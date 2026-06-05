"""
Baseline: OG-RAG Agent (Ontology-Grounded RAG).

Extends standard RAG with ontology-guided retrieval and a basic input gate
for entity type validation. No output gate enforcement.
"""

import re
import time
import logging
import numpy as np
import anthropic

logger = logging.getLogger(__name__)


class OGRAGAgent:
    """
    OG-RAG (Ontology-Grounded Retrieval-Augmented Generation) Agent baseline.

    Augments standard RAG with:
    - Ontology-guided retrieval: boosts documents containing ontology-defined terms
    - Input gate: validates entity type references in queries against the ontology
    No output gate is applied (input constraint only).
    """

    def __init__(
        self,
        llm_client: anthropic.Anthropic,
        documents: list,
        ontology_ttl: str,
    ):
        """
        Initialize the OG-RAG agent.

        Args:
            llm_client: Anthropic API client instance.
            documents: List of document strings to index.
            ontology_ttl: OWL ontology in Turtle format for term extraction.
        """
        self.llm_client = llm_client
        self.documents = documents
        self.ontology_ttl = ontology_ttl
        self._model = None
        self._index = None
        self._embeddings = None
        self._index_built = False
        self._ontology_terms = self._extract_ontology_terms(ontology_ttl)
        self._entity_classes = self._extract_entity_classes(ontology_ttl)

    def _extract_ontology_terms(self, ttl: str) -> list:
        """Extract class/property names from the ontology for retrieval boosting."""
        terms = set()
        local_name_pattern = re.compile(r":\s*([A-Z][a-zA-Z0-9_]+)", re.MULTILINE)
        for m in local_name_pattern.finditer(ttl):
            name = m.group(1)
            if len(name) > 2:
                terms.add(name)
                words = re.findall(r"[A-Z][a-z0-9]+|[A-Z]+(?=[A-Z]|$)|[a-z0-9]+", name)
                terms.update(w.lower() for w in words if len(w) > 2)
        return sorted(terms)

    def _extract_entity_classes(self, ttl: str) -> list:
        """Extract class names (CamelCase) from the ontology for input validation."""
        classes = set()
        # Match owl:Class declarations
        pattern = re.compile(
            r"<([^>]+)>\s+(?:a|rdf:type)\s+[^.]*owl[#/]Class",
            re.IGNORECASE | re.DOTALL,
        )
        for m in pattern.finditer(ttl):
            local = m.group(1).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            if local:
                classes.add(local)

        # Also match simple prefix:ClassName patterns
        prefix_pattern = re.compile(r":([A-Z][a-zA-Z0-9]+)\s+a\s+owl:Class", re.MULTILINE)
        for m in prefix_pattern.finditer(ttl):
            classes.add(m.group(1))

        return sorted(classes)

    def _build_index(self):
        """Build FAISS index lazily on first call."""
        if self._index_built or not self.documents:
            return

        try:
            from sentence_transformers import SentenceTransformer
            import faiss

            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            embeddings = self._model.encode(
                self.documents,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            ).astype(np.float32)

            self._embeddings = embeddings
            dim = embeddings.shape[1]
            self._index = faiss.IndexFlatIP(dim)
            self._index.add(embeddings)
            self._index_built = True
            logger.info(f"OGRAGAgent: FAISS index built ({len(self.documents)} docs).")

        except ImportError as e:
            logger.warning(f"OGRAGAgent: Library missing ({e}). Using keyword retrieval.")
            self._index_built = True

    def _validate_input(self, query: str) -> tuple:
        """
        Validate query for entity type references.

        Checks if the query mentions entities that appear in the ontology.
        Returns (is_valid: bool, details: str).
        """
        query_lower = query.lower()

        # Check if any ontology entity is mentioned
        mentioned_entities = [
            cls for cls in self._entity_classes
            if cls.lower() in query_lower or
            any(word in query_lower for word in re.findall(r"[A-Z][a-z]+", cls))
        ]

        # Allow queries with explicit zone/unit/sensor identifiers (domain-agnostic)
        has_domain_entity = bool(re.search(
            r"\b(?:zone|sensor|unit|meter|zone|actuator|mission|command)\b",
            query_lower
        ))

        input_validated = len(mentioned_entities) > 0 or has_domain_entity
        return input_validated, mentioned_entities

    def _retrieve(self, query: str, k: int) -> list:
        """
        Retrieve top-k documents with ontology-guided boosting.

        Args:
            query: Query string.
            k: Number of documents to retrieve.

        Returns:
            List of retrieved document strings.
        """
        if not self.documents:
            return []

        k = min(k, len(self.documents))

        if self._index is not None and self._model is not None:
            try:
                query_emb = self._model.encode(
                    [query],
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                ).astype(np.float32)

                n_candidates = min(k * 3, len(self.documents))
                distances, indices = self._index.search(query_emb, n_candidates)

                # Ontology-guided boosting
                scored = []
                for idx, dist in zip(indices[0], distances[0]):
                    if idx < 0:
                        continue
                    score = float(dist)
                    doc_lower = self.documents[idx].lower()
                    boost = sum(
                        0.05 for term in self._ontology_terms
                        if term.lower() in doc_lower
                    )
                    scored.append((idx, score + boost))

                scored.sort(key=lambda x: x[1], reverse=True)
                return [self.documents[i] for i, _ in scored[:k]]

            except Exception as e:
                logger.warning(f"OGRAGAgent dense retrieval failed: {e}.")

        # Keyword + ontology fallback
        query_terms = set(re.findall(r"\w+", query.lower()))
        scored = []
        for i, doc in enumerate(self.documents):
            doc_lower = doc.lower()
            doc_terms = set(re.findall(r"\w+", doc_lower))
            kw_score = len(query_terms & doc_terms)
            onto_boost = sum(0.5 for t in self._ontology_terms if t.lower() in doc_lower)
            scored.append((i, kw_score + onto_boost))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [self.documents[i] for i, _ in scored[:k]]

    def run(self, query: str, k: int = 5) -> dict:
        """
        Generate a response with ontology-guided retrieval and input validation.

        Args:
            query: User query string.
            k: Number of documents to retrieve.

        Returns:
            dict with keys:
                - response: str — LLM-generated response
                - input_validated: bool — whether query passed input validation
                - latency_ms: float — total wall-clock time in milliseconds
        """
        t_start = time.time()

        # Lazy index build
        if not self._index_built:
            self._build_index()

        # Input validation
        input_validated, _ = self._validate_input(query)

        # Ontology-guided retrieval
        retrieved = self._retrieve(query, k)

        # Build system context with ontology terms
        key_classes = ", ".join(self._entity_classes[:10])
        context_text = "\n\n".join(
            f"[Doc {i+1}] {doc[:500]}" for i, doc in enumerate(retrieved)
        )

        prompt = (
            f"You are an ontology-grounded AI agent. Key domain entities: {key_classes}\n\n"
            f"RETRIEVED CONTEXT:\n{context_text}\n\n"
            f"QUERY:\n{query}\n\n"
            f"Answer based on the retrieved context and domain entity constraints. "
            f"Reference only entities defined in the domain ontology."
        )

        response = self._call_llm(prompt)
        latency_ms = (time.time() - t_start) * 1000

        return {
            "response": response,
            "input_validated": input_validated,
            "latency_ms": latency_ms,
        }

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.llm_client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.content[0].text.strip()
            except anthropic.APIError as e:
                if attempt < max_retries - 1:
                    import time as _time
                    _time.sleep(2 ** attempt)
                    continue
                logger.error(f"OGRAGAgent LLM call failed: {e}")
                return f"[Error: LLM call failed after {max_retries} attempts: {e}]"


if __name__ == "__main__":
    import os
    from domains.smart_building import DOMAIN_DOCS, MANUAL_ONTOLOGY_TTL

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    docs = [p.strip() for p in DOMAIN_DOCS.split("\n\n") if p.strip()]

    agent = OGRAGAgent(client, docs, MANUAL_ONTOLOGY_TTL)
    result = agent.run("What should happen when Zone B-103 reads 28.5°C with setpoint 22°C?")
    print(f"Input validated: {result['input_validated']}")
    print(f"Response: {result['response'][:300]}")
    print(f"Latency: {result['latency_ms']:.0f} ms")
