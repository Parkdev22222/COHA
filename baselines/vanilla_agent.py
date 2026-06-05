"""
Baseline: Vanilla Agent.

A minimal LLM agent that answers queries directly without any ontology,
retrieval, or gate enforcement. Serves as the lower-bound baseline.
"""

import time
import logging
import anthropic

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

    def __init__(self, llm_client: anthropic.Anthropic):
        """
        Initialize the vanilla agent.

        Args:
            llm_client: Anthropic API client instance.
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
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.llm_client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": query}],
                )
                return response.content[0].text.strip()
            except anthropic.APIError as e:
                if attempt < max_retries - 1:
                    import time as _time
                    _time.sleep(2 ** attempt)
                    continue
                logger.error(f"VanillaAgent LLM call failed: {e}")
                return f"[Error: LLM call failed after {max_retries} attempts: {e}]"


if __name__ == "__main__":
    import os
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    agent = VanillaAgent(client)
    result = agent.run("What is the capital of France?")
    print(f"Response: {result['response'][:200]}")
    print(f"Latency: {result['latency_ms']:.0f} ms")
