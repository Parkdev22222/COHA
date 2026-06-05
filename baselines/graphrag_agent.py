"""
Baseline: GraphRAG Agent.

A simplified Microsoft GraphRAG-style agent that clusters documents into
communities, generates community summaries, and answers queries using the
most relevant community-level global context.
"""

import time
import re
import logging
import numpy as np
import anthropic

logger = logging.getLogger(__name__)


class GraphRAGAgent:
    """
    GraphRAG Agent baseline — simplified Microsoft GraphRAG style.

    Groups documents into semantic communities via clustering, generates
    a summary for each community, then selects the most relevant community
    summary to answer each query. Provides global context rather than
    local document-level retrieval.
    """

    def __init__(self, llm_client: anthropic.Anthropic, documents: list):
        """
        Initialize the GraphRAG agent.

        Args:
            llm_client: Anthropic API client instance.
            documents: List of document strings to organize into communities.
        """
        self.llm_client = llm_client
        self.documents = documents
        self._community_summaries = []
        self._community_docs = []
        self._community_embeddings = None
        self._model = None
        self._built = False

    def build_community_summaries(self):
        """
        Group documents into communities and generate a summary for each.

        Uses sentence-transformers + K-Means clustering to form communities.
        Falls back to sequential grouping if clustering is unavailable.
        Each community is summarized with an LLM call.
        """
        if self._built or not self.documents:
            return

        logger.info(f"GraphRAGAgent: Building communities from {len(self.documents)} documents.")

        # Group documents into communities
        communities = self._cluster_documents()
        self._community_docs = communities

        # Generate a summary for each community
        self._community_summaries = []
        for i, community in enumerate(communities):
            logger.info(f"GraphRAGAgent: Summarizing community {i+1}/{len(communities)}...")
            summary = self._summarize_community(i, community)
            self._community_summaries.append(summary)

        # Embed community summaries for retrieval
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._community_embeddings = self._model.encode(
                self._community_summaries,
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).astype(np.float32)
        except ImportError:
            self._community_embeddings = None

        self._built = True
        logger.info(f"GraphRAGAgent: Built {len(self._community_summaries)} community summaries.")

    def _cluster_documents(self) -> list:
        """
        Cluster documents into semantic communities.

        Uses K-Means on sentence-transformer embeddings.
        Falls back to equal-size sequential groups if unavailable.

        Returns:
            List of document groups (each group is a list of doc strings).
        """
        n_docs = len(self.documents)
        n_communities = max(2, min(5, n_docs // 3))

        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.cluster import KMeans

            model = SentenceTransformer("all-MiniLM-L6-v2")
            embeddings = model.encode(
                self.documents,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )

            n_communities = min(n_communities, n_docs)
            kmeans = KMeans(n_clusters=n_communities, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)

            communities = [[] for _ in range(n_communities)]
            for doc, label in zip(self.documents, labels):
                communities[label].append(doc)

            # Remove empty communities
            communities = [c for c in communities if c]
            return communities

        except Exception as e:
            logger.warning(f"GraphRAGAgent: Clustering failed ({e}). Using sequential grouping.")
            # Sequential fallback
            group_size = max(1, n_docs // n_communities)
            return [
                self.documents[i:i + group_size]
                for i in range(0, n_docs, group_size)
            ]

    def _summarize_community(self, community_idx: int, docs: list) -> str:
        """
        Generate a summary for a document community.

        Args:
            community_idx: Community index for labeling.
            docs: List of document strings in this community.

        Returns:
            Community summary string.
        """
        docs_text = "\n\n".join(f"- {doc[:300]}" for doc in docs)
        prompt = (
            f"Summarize the key facts, entities, relationships, and rules in the "
            f"following group of domain documents. Focus on information that would "
            f"be useful for answering operational queries.\n\n"
            f"DOCUMENTS (Community {community_idx + 1}):\n{docs_text}\n\n"
            f"Provide a concise, factual summary (3–5 sentences) covering the main "
            f"concepts and their relationships."
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.llm_client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=256,
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.content[0].text.strip()
            except anthropic.APIError as e:
                if attempt < max_retries - 1:
                    import time as _time
                    _time.sleep(2 ** attempt)
                    continue
                logger.warning(f"Community summarization failed: {e}")
                return f"Community {community_idx + 1}: " + " | ".join(doc[:80] for doc in docs[:3])

    def run(self, query: str) -> dict:
        """
        Generate a response using the most relevant community summary.

        Args:
            query: User query string.

        Returns:
            dict with keys:
                - response: str — LLM-generated response
                - latency_ms: float — total wall-clock time in milliseconds
        """
        t_start = time.time()

        # Lazy build
        if not self._built:
            self.build_community_summaries()

        if not self._community_summaries:
            response = self._call_llm(query, context="No community summaries available.")
            return {"response": response, "latency_ms": (time.time() - t_start) * 1000}

        # Select most relevant community summary
        best_summary = self._select_community(query)

        # Generate response with global context
        prompt = (
            f"You are an AI agent with access to the following global domain summary.\n\n"
            f"GLOBAL DOMAIN CONTEXT:\n{best_summary}\n\n"
            f"QUERY:\n{query}\n\n"
            f"Answer the query based on the global context provided. "
            f"Be specific and reference relevant facts from the context."
        )

        response = self._call_llm(query, context=best_summary)
        latency_ms = (time.time() - t_start) * 1000

        return {
            "response": response,
            "latency_ms": latency_ms,
        }

    def _select_community(self, query: str) -> str:
        """
        Select the most relevant community summary for the query.

        Args:
            query: Query string.

        Returns:
            Best-matching community summary string.
        """
        if len(self._community_summaries) == 1:
            return self._community_summaries[0]

        # Dense retrieval if embeddings available
        if self._community_embeddings is not None and self._model is not None:
            try:
                query_emb = self._model.encode(
                    [query],
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                ).astype(np.float32)

                scores = (self._community_embeddings @ query_emb.T).flatten()
                best_idx = int(np.argmax(scores))
                return self._community_summaries[best_idx]
            except Exception as e:
                logger.warning(f"GraphRAGAgent community selection failed: {e}")

        # Keyword fallback
        query_terms = set(re.findall(r"\w+", query.lower()))
        best_score = -1
        best_summary = self._community_summaries[0]

        for summary in self._community_summaries:
            summary_terms = set(re.findall(r"\w+", summary.lower()))
            score = len(query_terms & summary_terms)
            if score > best_score:
                best_score = score
                best_summary = summary

        return best_summary

    def _call_llm(self, query: str, context: str) -> str:
        """Call the LLM with the query and global context."""
        prompt = (
            f"You are an AI agent with access to the following global domain knowledge.\n\n"
            f"GLOBAL CONTEXT:\n{context}\n\n"
            f"QUERY:\n{query}\n\n"
            f"Provide a specific, accurate answer based on the global context."
        )

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
                logger.error(f"GraphRAGAgent LLM call failed: {e}")
                return f"[Error: LLM call failed after {max_retries} attempts: {e}]"


if __name__ == "__main__":
    import os
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    docs = [
        "HVAC Zone B-103 temperature setpoint is 22°C. Current reading: 28.5°C.",
        "Energy meter EM-01: today 450 kWh, baseline 280 kWh. Anomaly threshold: 150% of baseline.",
        "CO2 sensor CS-301: 1250 ppm. Threshold: 1000 ppm → increase ventilation 20%.",
        "HVAC rule: temperature deviation > 2°C triggers actuator command.",
        "Occupancy sensor OS-1: Zone-North has 0 occupants for 2 hours. Apply setpoint relaxation.",
    ]

    agent = GraphRAGAgent(client, docs)
    result = agent.run("What action should be taken for Zone B-103?")
    print(f"Response: {result['response'][:300]}")
    print(f"Latency: {result['latency_ms']:.0f} ms")
