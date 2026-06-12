"""
Lightweight domain document retriever for DK rule grounding.

No external dependencies (no sklearn / no network). Chunks the doctrine
corpus by section headers and scores chunks by token-overlap against a
query (a candidate DK rule). Used by the Phase Gate to ground inductively
extracted Domain Knowledge rules in published US Army doctrine
(ADP 3-0, ADP 3-90, FM 3-0, ROE training materials).

Grounding pipeline (paper §3.2.2):
  1. LLM induces a candidate DK rule from delta-Oi
  2. retrieve_evidence() finds the most relevant doctrine passage(s)
  3. LLM verifies whether the passage actually supports the rule
  4. Rule is accepted ONLY if grounded, with a source citation attached
"""
import re
import math
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "is", "are",
    "be", "with", "on", "at", "by", "as", "that", "this", "must", "should",
    "have", "has", "their", "its", "from", "not", "any", "all", "can", "may",
}


def _tokenize(text: str) -> List[str]:
    """Lowercase alphanumeric tokens, stopwords removed, length > 2."""
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 2]


class DomainDocRetriever:
    """TF-IDF-style retriever over doctrine sections (dependency-free)."""

    def __init__(self, domain_docs: str, min_chunk_chars: int = 80):
        self.chunks: List[str] = self._chunk_by_section(domain_docs, min_chunk_chars)
        self._chunk_tokens: List[List[str]] = [_tokenize(c) for c in self.chunks]
        self._idf = self._compute_idf(self._chunk_tokens)

    @staticmethod
    def _chunk_by_section(docs: str, min_chunk_chars: int) -> List[str]:
        """Split on markdown headers (##, ###) into titled passages."""
        if not docs or not docs.strip():
            return []
        # Split keeping headers attached to their following content
        parts = re.split(r"\n(?=#{1,4}\s)", docs.strip())
        chunks = []
        for p in parts:
            p = p.strip()
            if len(p) >= min_chunk_chars:
                chunks.append(p)
            elif chunks:
                # too-small fragment: append to previous chunk
                chunks[-1] = chunks[-1] + "\n" + p
        return chunks

    @staticmethod
    def _compute_idf(chunk_tokens: List[List[str]]) -> dict:
        n_docs = len(chunk_tokens) or 1
        df = {}
        for tokens in chunk_tokens:
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1
        return {t: math.log((n_docs + 1) / (c + 1)) + 1.0 for t, c in df.items()}

    def _score(self, query_tokens: List[str], chunk_tokens: List[str]) -> float:
        if not query_tokens or not chunk_tokens:
            return 0.0
        chunk_set = set(chunk_tokens)
        score = sum(self._idf.get(t, 1.0) for t in set(query_tokens) if t in chunk_set)
        # length-normalize so long chunks don't dominate
        return score / math.sqrt(len(chunk_set))

    def retrieve_evidence(self, query: str, top_k: int = 2) -> List[Tuple[str, float]]:
        """Return up to top_k (chunk_text, score) pairs ranked by relevance."""
        if not self.chunks:
            return []
        q_tokens = _tokenize(query)
        scored = [
            (self.chunks[i], self._score(q_tokens, self._chunk_tokens[i]))
            for i in range(len(self.chunks))
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [(c, s) for c, s in scored[:top_k] if s > 0.0]

    @staticmethod
    def section_title(chunk: str) -> str:
        """Extract the first markdown header line as a citation label."""
        for line in chunk.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                return line.lstrip("# ").strip()
        return chunk[:50].strip()
