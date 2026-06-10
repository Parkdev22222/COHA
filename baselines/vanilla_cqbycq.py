"""Vanilla CQbyCQ baseline: single context accumulation, no Phase Gate."""
import time
import logging
from coha.axiom_generator import AxiomGenerator, BASE_PREFIXES
from coha.owl_utils import merge_ontologies, check_consistency

logger = logging.getLogger(__name__)


class VanillaCQbyCQ:
    """
    Original CQbyCQ (Saeedizade & Blomqvist, 2024).
    All CQ processing in a single accumulating context.
    No context resets, no Phase Gate, no rule accumulation.
    """
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.generator = AxiomGenerator(llm_client)

    def run(self, cqs: list, user_story: str, max_retries: int = 3) -> dict:
        if hasattr(self.llm_client, "reset_stats"):
            self.llm_client.reset_stats()

        accumulated_ttl = ""
        gate_times = []
        total_times = []

        for i, cq in enumerate(cqs):
            cq_text = cq["question"] if isinstance(cq, dict) else cq
            print(f"  [Vanilla-CQbyCQ] CQ {i+1}/{len(cqs)}: {cq_text[:60]}...")
            t_start = time.time()
            delta_oi = None
            for attempt in range(max_retries):
                try:
                    delta_oi = self.generator.generate_full_context(
                        cq_text, user_story, accumulated_ttl
                    )
                    break
                except Exception as e:
                    logger.warning(f"CQ {i+1} attempt {attempt+1} failed: {e}")
            total_ms = (time.time() - t_start) * 1000
            total_times.append(total_ms)
            if delta_oi:
                accumulated_ttl = merge_ontologies(accumulated_ttl, delta_oi)

        return {
            "ontology_ttl": accumulated_ttl,
            "gate_times": gate_times,
            "total_times": total_times,
            "n_retries_total": 0,
            "final_fq_rules": [],
            "final_dk_rules": [],
            "is_consistent": check_consistency(accumulated_ttl),
            "usage_stats": (
                self.llm_client.get_usage_stats()
                if hasattr(self.llm_client, "get_usage_stats") else {}
            ),
        }
