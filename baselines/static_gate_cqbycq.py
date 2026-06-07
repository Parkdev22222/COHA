"""CQbyCQ + Static Gate baseline: context reset, fixed FQ rules, no DK accumulation."""
from coha.harness import COHAHarness, HarnessConfig


class StaticGateCQbyCQ:
    """
    CQbyCQ with a static Phase Gate: context resets per CQ, fixed pre-defined
    OWL quality rules, no dynamic FQ/DK rule accumulation.
    """
    def __init__(self, llm_client):
        config = HarnessConfig.coha_static_gate()
        self.harness = COHAHarness(llm_client, config)

    def run(self, cqs: list, user_story: str) -> dict:
        return self.harness.run(cqs, user_story)
