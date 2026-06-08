"""
Baseline B1: Whole-Ontology Prompting.

All CQs fed to LLM in a single prompt; single OWL output generated.
No iteration, no context management, no Phase Gate.
Simplest possible baseline.
"""
import time
import logging
from coha.owl_utils import merge_ontologies, check_consistency

logger = logging.getLogger(__name__)


class WholeOntologyPrompting:
    """
    B1: Single-prompt baseline.
    All 60 CQs provided at once; LLM generates full ontology in one call.
    """

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def run(self, cqs: list, user_story: str, domain_docs: str = "") -> dict:
        print(f"  [WholeOntology] Single-prompt generation for {len(cqs)} CQs...")
        t_start = time.time()

        cq_list = "\n".join(
            f"{i+1}. {cq['question'] if isinstance(cq, dict) else cq}"
            for i, cq in enumerate(cqs)
        )

        prompt = (
            "You are an OWL ontology engineer for the military tactical domain.\n\n"
            f"USER STORY:\n{user_story}\n\n"
            f"ALL COMPETENCY QUESTIONS ({len(cqs)} total):\n{cq_list}\n\n"
            "Generate a complete OWL 2 ontology in Turtle format that answers ALL of the "
            "above Competency Questions.\n\n"
            "Requirements:\n"
            "1. Use prefix: @prefix : <http://coha.org/military#>\n"
            "2. Declare owl:Class for each concept with rdfs:label\n"
            "3. Declare owl:ObjectProperty and owl:DatatypeProperty with rdfs:domain, rdfs:range\n"
            "4. Add rdfs:subClassOf where applicable\n"
            "5. Ensure every CQ is answerable from the ontology\n"
            "6. Return ONLY valid Turtle — no markdown, no explanation\n\n"
            "Generate the complete ontology:"
        )

        ontology_ttl = ""
        try:
            raw = self.llm_client.generate(system="", user=prompt, max_tokens=4096)
            ontology_ttl = self._clean_turtle(raw)
        except Exception as e:
            logger.error(f"WholeOntologyPrompting failed: {e}")

        total_ms = (time.time() - t_start) * 1000
        is_consistent = check_consistency(ontology_ttl) if ontology_ttl else False

        return {
            "ontology_ttl": ontology_ttl,
            "gate_times": [],
            "total_times": [total_ms],
            "n_retries_total": 0,
            "final_fq_rules": [],
            "final_dk_rules": [],
            "rar_data": [],
            "qic_data": [],
            "is_consistent": is_consistent,
        }

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
