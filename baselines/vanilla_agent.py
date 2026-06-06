"""
Baseline: Vanilla Agent.

A minimal LLM agent that answers queries directly without any ontology,
retrieval, or gate enforcement. Serves as the lower-bound baseline.
"""

import time
import logging

from llm_client import UnifiedLLMClient

logger = logging.getLogger(__name__)


class VanillaAgent:
    """
    Vanilla Agent baseline — direct LLM calls with no augmentation.

    Accepts a query and calls the LLM directly without:
    - Retrieval augmentation
    - Ontology grounding
    - Input/output gate validation

    Used as the baseline to measure the contribution of COHA components.
    """

    def __init__(self, llm_client: UnifiedLLMClient):
        """
        Initialize the vanilla agent.

        Args:
            llm_client: UnifiedLLMClient instance.
        """
        self.llm_client = llm_client

    def run(self, query: str) -> dict:
        """
        Generate a response to a query using the LLM directly.

        Args:
            query: User query string.

        Returns:
            dict with keys:
                - response: str — LLM-generated response
                - latency_ms: float — wall-clock time in milliseconds
        """
        t_start = time.time()

        response_text = self._call_llm(query)

        latency_ms = (time.time() - t_start) * 1000

        return {
            "response": response_text,
            "latency_ms": latency_ms,
        }

    def _call_llm(self, query: str) -> str:
        """
        Call the LLM with the query directly.

        Args:
            query: User query string.

        Returns:
            Generated response string.
        """
        try:
            return self.llm_client.generate(system="", user=query, max_tokens=1024)
        except RuntimeError as e:
            logger.error(f"VanillaAgent LLM call failed: {e}")
            return f"[Error: LLM call failed: {e}]"


if __name__ == "__main__":
    from llm_client import get_client
    client = get_client()
    agent = VanillaAgent(client)
    result = agent.run("What is the capital of France?")
    print(f"Response: {result['response'][:200]}")
    print(f"Latency: {result['latency_ms']:.0f} ms")
