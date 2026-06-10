"""
Baseline B3: Memoryless CQbyCQ (Lippolis et al., 2025).

Each CQ processed completely independently — no accumulated context,
no handoff, no Phase Gate. Each call receives only the current CQ
and user story; previous CQs have no influence.

Contrasts with:
- Vanilla CQbyCQ: single accumulating context (context grows each CQ)
- COHA: context reset + handoff artifact injection
"""
import time
import logging
from coha.owl_utils import merge_ontologies, check_consistency

logger = logging.getLogger(__name__)


class MemorylessCQbyCQ:
    """
    B3: Memoryless CQbyCQ.
    Each CQ processed in isolation; deltas merged only at the end.
    No context transfer between CQs whatsoever.
    """

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def run(self, cqs: list, user_story: str, max_retries: int = 3) -> dict:
        if hasattr(self.llm_client, "reset_stats"):
            self.llm_client.reset_stats()

        total_times = []
        all_deltas = []

        for i, cq in enumerate(cqs):
            cq_text = cq["question"] if isinstance(cq, dict) else cq
            print(f"  [Memoryless-CQbyCQ] CQ {i+1}/{len(cqs)}: {cq_text[:60]}...")
            t_start = time.time()

            delta_oi = None
            for attempt in range(max_retries):
                try:
                    delta_oi = self._generate_isolated(cq_text, user_story)
                    if delta_oi:
                        break
                except Exception as e:
                    logger.warning(f"CQ {i+1} attempt {attempt+1} failed: {e}")

            total_times.append((time.time() - t_start) * 1000)
            if delta_oi:
                all_deltas.append(delta_oi)

        # Merge all independently-generated deltas at the end
        accumulated_ttl = ""
        for delta in all_deltas:
            accumulated_ttl = merge_ontologies(accumulated_ttl, delta)

        return {
            "ontology_ttl": accumulated_ttl,
            "gate_times": [],
            "total_times": total_times,
            "n_retries_total": 0,
            "final_fq_rules": [],
            "final_dk_rules": [],
            "rar_data": [],
            "qic_data": [],
            "is_consistent": check_consistency(accumulated_ttl),
            "usage_stats": (
                self.llm_client.get_usage_stats()
                if hasattr(self.llm_client, "get_usage_stats") else {}
            ),
        }

    def _generate_isolated(self, cq: str, user_story: str) -> str:
        """Generate delta-Oi with NO knowledge of previous CQs."""
        prompt = (
            "You are an ontology engineer for the military tactical domain.\n\n"
            f"USER STORY:\n{user_story}\n\n"
            f"COMPETENCY QUESTION:\n{cq}\n\n"
            "Generate ONLY the OWL 2 axioms in Turtle format needed to answer this CQ.\n"
            "No context from other CQs is available — generate standalone axioms.\n"
            "Requirements:\n"
            "1. Use prefix: @prefix : <http://coha.org/military#>\n"
            "2. Declare every class and property used with rdfs:label\n"
            "3. Return ONLY valid Turtle — no markdown, no explanation\n\n"
            "Generate:"
        )
        raw = self.llm_client.generate(system="", user=prompt, max_tokens=1024)
        return self._clean_turtle(raw)

    @staticmethod
    def _clean_turtle(text: str) -> str:
        for marker in ["```turtle", "```ttl"]:
            if marker in text:
                start = text.find(marker) + len(marker)
                end = text.find("```", start)
                return text[start:end].strip() if end != -1 else text[start:].strip()
        if "```" in text:
            start = text.find("```") + 3
            nl = text.find("\n", start)
            if nl != -1:
                start = nl + 1
            end = text.find("```", start)
            return text[start:end].strip() if end != -1 else text[start:].strip()
        return text.strip()
