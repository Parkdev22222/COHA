"""
Baseline B4: Ontogenia (Lippolis et al., 2025).

CQbyCQ extension with:
  (1) Metacognitive prompting: LLM reflects on its own generation and
      identifies potential errors before committing axioms
  (2) Ontology Design Patterns (ODP): common structural patterns
      injected into each generation prompt

No dynamic rule accumulation, no Phase Gate, no context reset.
Single accumulating context like Vanilla CQbyCQ, but with
metacognitive self-reflection and ODP guidance per CQ.

Reference: Lippolis et al. (2025). Ontology Generation using Large
Language Models: Memoryless CQbyCQ and Ontogenia. ESWC 2025.
arXiv:2503.05388.
"""
import time
import logging
from coha.owl_utils import merge_ontologies, check_consistency

logger = logging.getLogger(__name__)

# Ontology Design Patterns for military domain
MILITARY_ODPS = """
=== Ontology Design Patterns (ODPs) ===

ODP-1 AgentRole: An Agent plays a Role in a Context.
  :Unit rdfs:subClassOf :Agent
  :Mission rdfs:subClassOf :Context
  :assignedRole a owl:ObjectProperty ; rdfs:domain :Unit ; rdfs:range :Role .

ODP-2 EventParticipation: An Event has Participants with Roles.
  :ObservationEvent rdfs:subClassOf :Event
  :hasParticipant a owl:ObjectProperty ; rdfs:domain :Event ; rdfs:range :Agent .
  :atLocation a owl:ObjectProperty ; rdfs:domain :Event ; rdfs:range :Location .

ODP-3 PartOf (mereology): A Component is part of a Composite.
  :isPartOf a owl:ObjectProperty ; rdfs:domain :MilitaryUnit ; rdfs:range :MilitaryUnit .
  :hasPart owl:inverseOf :isPartOf .

ODP-4 Classification: An Entity is classified by a Type.
  :hasClassification a owl:ObjectProperty .
  :ThreatLevel rdfs:subClassOf :Classification .

ODP-5 Sequence: Ordered sequence of Steps.
  :hasNextStep a owl:ObjectProperty ; rdfs:domain :OrderType ; rdfs:range :OrderType .
  :precedes owl:inverseOf :hasNextStep .
"""


class OntoGeniaAgent:
    """
    B4: Ontogenia — metacognitive prompting + ODP injection.
    Single accumulating context; no Phase Gate.
    """

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def run(self, cqs: list, user_story: str, max_retries: int = 3) -> dict:
        accumulated_ttl = ""
        total_times = []

        for i, cq in enumerate(cqs):
            cq_text = cq["question"] if isinstance(cq, dict) else cq
            print(f"  [Ontogenia] CQ {i+1}/{len(cqs)}: {cq_text[:60]}...")
            t_start = time.time()

            delta_oi = None
            for attempt in range(max_retries):
                try:
                    delta_oi = self._generate_with_metacognition(
                        cq_text, user_story, accumulated_ttl
                    )
                    if delta_oi:
                        break
                except Exception as e:
                    logger.warning(f"CQ {i+1} attempt {attempt+1} failed: {e}")

            total_times.append((time.time() - t_start) * 1000)
            if delta_oi:
                accumulated_ttl = merge_ontologies(accumulated_ttl, delta_oi)

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
        }

    def _generate_with_metacognition(
        self, cq: str, user_story: str, accumulated_ttl: str
    ) -> str:
        """Two-phase metacognitive generation with ODP injection."""

        onto_section = (
            f"\nACCUMULATED ONTOLOGY:\n```turtle\n{accumulated_ttl[:3000]}\n```\n"
            if accumulated_ttl.strip()
            else "\nThis is the first CQ.\n"
        )

        # Phase A: Metacognitive reflection — identify what's needed and potential pitfalls
        reflect_prompt = (
            "You are an expert ontology engineer using metacognitive reflection.\n\n"
            f"USER STORY:\n{user_story}\n"
            f"{onto_section}\n"
            f"{MILITARY_ODPS}\n"
            f"COMPETENCY QUESTION:\n{cq}\n\n"
            "Before generating OWL axioms, reflect:\n"
            "1. What classes and properties are needed to answer this CQ?\n"
            "2. Which Ontology Design Pattern (above) best applies?\n"
            "3. What errors or inconsistencies should I avoid?\n"
            "4. What existing concepts can I reuse vs. what needs to be new?\n\n"
            "Provide a brief reflection (3-5 sentences), then on a new line write "
            "GENERATE: followed by the OWL Turtle axioms.\n"
            "Use prefix: @prefix : <http://coha.org/military#>"
        )

        try:
            resp = self.llm_client.generate(system="", user=reflect_prompt, max_tokens=2048)

            # Extract the Turtle part after "GENERATE:"
            if "GENERATE:" in resp:
                turtle_part = resp.split("GENERATE:", 1)[1].strip()
            else:
                turtle_part = resp

            return self._clean_turtle(turtle_part)
        except Exception as e:
            logger.warning(f"Ontogenia metacognitive generation failed: {e}")
            return ""

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
