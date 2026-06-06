"""
Phase 3: Context Assembly.

Retrieves relevant documents for a given query using dense vector search
(sentence-transformers + FAISS). When ontology guidance is enabled,
boosts documents that contain ontology class and property names.
"""

import re
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


class ContextAssembler:
    """
    Assembles relevant context for an agent query using ontology-guided retrieval.

    Encodes documents with sentence-transformers, builds a FAISS index for
    efficient similarity search, and optionally boosts documents containing
    ontology-defined terms to improve ontological grounding of retrieved context.
    """

    def __init__(
        self,
        documents: list,
        ontology_ttl: str = "",
        use_ontology_guidance: bool = True,
    ):
        """
        Initialize the context assembler.

        Args:
            documents: List of document strings to index.
            ontology_ttl: OWL ontology in Turtle format (for term extraction).
            use_ontology_guidance: Whether to boost docs with ontology terms.
        """
        self.documents = documents
        self.ontology_ttl = ontology_ttl
        self.use_ontology_guidance = use_ontology_guidance
        self._model = None
        self._index = None
        self._embeddings = None
        self._ontology_terms = []
        self._build_failed = False

        if ontology_ttl and use_ontology_guidance:
            self._ontology_terms = self._extract_ontology_terms(ontology_ttl)

    def build_index(self):
        """
        Build the FAISS index over all documents.

        Encodes documents using 'all-MiniLM-L6-v2' sentence-transformers model
        and stores the resulting embeddings in a FAISS flat L2 index.
        """
        if self._build_failed:
            return

        if not self.documents:
            logger.warning("No documents provided for indexing.")
            return

        try:
            from sentence_transformers import SentenceTransformer
            import faiss

            if self._model is None:
                logger.info("Loading sentence-transformers model 'all-MiniLM-L6-v2'...")
                self._model = SentenceTransformer("all-MiniLM-L6-v2")

            logger.info(f"Encoding {len(self.documents)} documents...")
            embeddings = self._model.encode(
                self.documents,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            self._embeddings = embeddings.astype(np.float32)

            dim = self._embeddings.shape[1]
            self._index = faiss.IndexFlatIP(dim)  # Inner product = cosine sim for normalized vecs
            self._index.add(self._embeddings)
            logger.info(f"FAISS index built with {self._index.ntotal} vectors (dim={dim}).")

        except (ImportError, OSError, Exception) as e:
            logger.error(f"Failed to build FAISS index: {e}. Using fallback keyword retrieval.")
            self._build_failed = True
            self._index = None
            self._model = None

    def retrieve(self, query: str, k: int = 5) -> list:
        """
        Retrieve the top-k most relevant documents for the query.

        Performs dense retrieval with optional ontology-term boosting.

        Args:
            query: Query string.
            k: Number of documents to retrieve.

        Returns:
            List of top-k document strings.
        """
        if not self.documents:
            return []

        k = min(k, len(self.documents))

        # Lazy index build (skip if previous attempt failed)
        if self._index is None and self._model is None and not self._build_failed:
            self.build_index()

        if self._index is None:
            # Fallback: keyword-based retrieval
            return self._keyword_retrieve(query, k)

        try:
            from sentence_transformers import SentenceTransformer

            if self._model is None:
                self._model = SentenceTransformer("all-MiniLM-L6-v2")

            query_emb = self._model.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).astype(np.float32)

            # Search FAISS index
            distances, indices = self._index.search(query_emb, min(k * 3, len(self.documents)))

            # Build (doc_idx, score) pairs
            scored = []
            for idx, dist in zip(indices[0], distances[0]):
                if idx < 0:
                    continue
                score = float(dist)

                # Ontology term boosting
                if self.use_ontology_guidance and self._ontology_terms:
                    doc_lower = self.documents[idx].lower()
                    boost = sum(
                        1.0 for term in self._ontology_terms
                        if term.lower() in doc_lower
                    )
                    score += 0.05 * boost  # Small boost per matched ontology term

                scored.append((idx, score))

            # Sort by boosted score (descending) and take top-k
            scored.sort(key=lambda x: x[1], reverse=True)
            top_k_indices = [idx for idx, _ in scored[:k]]

            return [self.documents[i] for i in top_k_indices]

        except Exception as e:
            logger.warning(f"Dense retrieval failed: {e}. Falling back to keyword retrieval.")
            return self._keyword_retrieve(query, k)

    def _keyword_retrieve(self, query: str, k: int) -> list:
        """
        Fallback keyword-based retrieval when FAISS/sentence-transformers unavailable.

        Args:
            query: Query string.
            k: Number of documents to retrieve.

        Returns:
            Top-k documents by keyword overlap.
        """
        query_terms = set(re.findall(r"\w+", query.lower()))
        scored = []

        for i, doc in enumerate(self.documents):
            doc_terms = set(re.findall(r"\w+", doc.lower()))
            overlap = len(query_terms & doc_terms)

            # Boost if doc contains ontology terms
            boost = 0
            if self.use_ontology_guidance:
                doc_lower = doc.lower()
                boost = sum(1 for t in self._ontology_terms if t.lower() in doc_lower)

            scored.append((i, overlap + 0.5 * boost))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [self.documents[i] for i, _ in scored[:k]]

    def _extract_ontology_terms(self, ontology_ttl: str) -> list:
        """
        Extract class and property names from a Turtle-format ontology.

        Args:
            ontology_ttl: OWL ontology in Turtle format.

        Returns:
            List of term strings (class names and property names).
        """
        terms = set()

        # Extract prefix-based local names (e.g., :HVACZone, :hasSetpoint)
        local_name_pattern = re.compile(r":\s*([A-Z][a-zA-Z0-9_]+)", re.MULTILINE)
        for m in local_name_pattern.finditer(ontology_ttl):
            name = m.group(1)
            if len(name) > 2:
                # Split camelCase into words
                words = re.findall(r"[A-Z][a-z0-9]+|[A-Z]+(?=[A-Z]|$)|[a-z0-9]+", name)
                terms.add(name)
                terms.update(w.lower() for w in words if len(w) > 2)

        # Extract IRI fragment names
        iri_pattern = re.compile(r"[#/]([A-Z][a-zA-Z0-9_]+)>")
        for m in iri_pattern.finditer(ontology_ttl):
            name = m.group(1)
            if len(name) > 2:
                terms.add(name)

        return sorted(terms)


if __name__ == "__main__":
    docs = [
        "HVAC Zone B-103 has a temperature setpoint of 22°C. The current reading is 28.5°C.",
        "Energy meter EM-01 monitors the total power consumption of Floor 1.",
        "CO2 sensors in OccupancyZone A detect air quality for ventilation control.",
        "The building management system controls HVAC actuators based on sensor readings.",
        "Temperature anomalies trigger alerts when deviation from setpoint exceeds 2°C.",
    ]

    onto_ttl = """@prefix : <http://coha.org/smart_building#> .
:HVACZone a owl:Class .
:TemperatureSensor a owl:Class .
:EnergyMeter a owl:Class .
:hasSetpointTemperature a owl:ObjectProperty .
"""

    assembler = ContextAssembler(docs, onto_ttl, use_ontology_guidance=True)
    assembler.build_index()

    results = assembler.retrieve("What is the temperature of Zone B-103?", k=2)
    print("Retrieved docs:")
    for r in results:
        print(f"  - {r[:80]}")
