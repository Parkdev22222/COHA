"""
Baseline: RAG Agent.

A standard retrieval-augmented generation agent using sentence-transformers
for dense retrieval and FAISS for approximate nearest-neighbor search.
No ontology grounding or gate enforcement.
"""

import time
import logging
import numpy as np
import anthropic

logger = logging.getLogger(__name__)


class RAGAgent:
    """
    RAG (Retrieval-Augmented Generation) Agent baseline.

    Encodes documents with sentence-transformers, retrieves top-k documents
    by cosine similarity for each query, and generates a response using the
    retrieved context. FAISS index is built lazily on the first call.
    """

    def __init__(self, llm_client: anthropic.Anthropic, documents: list):
        """
        Initialize the RAG agent.

        Args:
            llm_client: Anthropic API client instance.
            documents: List of document strings to index for retrieval.
        """
        self.llm_client = llm_client
        self.documents = documents
        self._model = None
        self._index = None
        self._embeddings = None
        self._index_built = False

    def _build_index(self):
        """
        Build the FAISS index over documents (called lazily on first run).

        Uses 'all-MiniLM-L6-v2' sentence-transformers model and
        FAISS IndexFlatIP (inner product for cosine similarity on normalized vectors).
        """
        if self._index_built or not self.documents:
            return

        try:
            from sentence_transformers import SentenceTransformer
            import faiss

            logger.info("RAGAgent: Loading sentence-transformers model...")
            self._model = SentenceTransformer("all-MiniLM-L6-v2")

            logger.info(f"RAGAgent: Encoding {len(self.documents)} documents...")
            embeddings = self._model.encode(
                self.documents,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            self._embeddings = embeddings.astype(np.float32)

            dim = self._embeddings.shape[1]
            self._index = faiss.IndexFlatIP(dim)
            self._index.add(self._embeddings)
            self._index_built = True
            logger.info(f"RAGAgent: FAISS index built ({self._index.ntotal} vectors, dim={dim}).")

        except ImportError as e:
            logger.warning(f"RAGAgent: Required library missing ({e}). Falling back to keyword search.")
            self._index_built = True  # Prevent repeated attempts

    def run(self, query: str, k: int = 5) -> dict:
        """
        Generate a response with retrieval-augmented context.

        Args:
            query: User query string.
            k: Number of documents to retrieve.

        Returns:
            dict with keys:
                - response: str — LLM-generated response
                - retrieved_docs: list[str] — retrieved context documents
                - latency_ms: float — total wall-clock time in milliseconds
        """
        t_start = time.time()

        # Lazy index build
        if not self._index_built:
            self._build_index()

        # Retrieve relevant documents
        retrieved = self._retrieve(query, k)

        # Build RAG prompt
        context_text = "\n\n".join(
            f"[Document {i+1}]\n{doc[:500]}" for i, doc in enumerate(retrieved)
        )
        prompt = (
            f"Use the following retrieved documents to answer the question accurately.\n\n"
            f"RETRIEVED CONTEXT:\n{context_text}\n\n"
            f"QUESTION:\n{query}\n\n"
            f"Answer based on the provided context. If the context doesn't contain "
            f"sufficient information, state that clearly rather than guessing."
        )

        response_text = self._call_llm(prompt)
        latency_ms = (time.time() - t_start) * 1000

        return {
            "response": response_text,
            "retrieved_docs": retrieved,
            "latency_ms": latency_ms,
        }

    def _retrieve(self, query: str, k: int) -> list:
        """
        Retrieve the top-k most relevant documents.

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

                distances, indices = self._index.search(query_emb, k)
                return [self.documents[i] for i in indices[0] if i >= 0]

            except Exception as e:
                logger.warning(f"RAGAgent dense retrieval failed: {e}. Using keyword fallback.")

        # Keyword fallback
        import re
        query_terms = set(re.findall(r"\w+", query.lower()))
        scored = []
        for i, doc in enumerate(self.documents):
            doc_terms = set(re.findall(r"\w+", doc.lower()))
            scored.append((i, len(query_terms & doc_terms)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [self.documents[i] for i, _ in scored[:k]]

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.llm_client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text.strip()
            except anthropic.APIError as e:
                if attempt < max_retries - 1:
                    import time as _time
                    _time.sleep(2 ** attempt)
                    continue
                logger.error(f"RAGAgent LLM call failed: {e}")
                return f"[Error: LLM call failed after {max_retries} attempts: {e}]"


if __name__ == "__main__":
    import os
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    docs = [
        "HVAC Zone B-103 has a temperature setpoint of 22°C and currently reads 28.5°C.",
        "Energy meter EM-01 baseline is 280 kWh. Today's reading is 450 kWh.",
        "CO2 sensor CS-301 reads 1250 ppm; threshold is 1000 ppm for ventilation increase.",
    ]

    agent = RAGAgent(client, docs)
    result = agent.run("What is the temperature deviation in Zone B-103?")
    print(f"Response: {result['response'][:300]}")
    print(f"Retrieved docs: {len(result['retrieved_docs'])}")
    print(f"Latency: {result['latency_ms']:.0f} ms")
