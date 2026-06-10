"""
Baseline: OntoGPT (Caufield et al., 2023).

Schema-guided single-pass ontology extraction from domain documents.
Uses a LinkML-inspired template schema to structure LLM extraction.
No iteration, no context resets, no Phase Gate.

Reference: Caufield et al. "Structured prompt interrogation and recursive
extraction of semantics (SPIRES): A case study in populating rare disease
ontologies." Bioinformatics, 2024.
"""
import time
import logging
from coha.owl_utils import merge_ontologies, check_consistency

logger = logging.getLogger(__name__)

# LinkML-inspired schema for military tactical domain
MILITARY_SCHEMA = """
classes:
  MilitaryUnit:
    description: A military organizational element
    attributes: [designation, unitType, strength, assignedMission, parentUnit]
  Mission:
    description: An assigned military task
    attributes: [missionType, objective, assignedUnit, threatLevel, startTime]
  ThreatLevel:
    description: Assessment of enemy threat
    attributes: [level, enemyForce, location, confidence]
  TerrainType:
    description: Physical environment classification
    attributes: [terrainClass, mobility, visibility, coverAndConcealment]
  EngagementRule:
    description: Rules governing the use of force
    attributes: [ruleType, authority, conditions, restrictedActions]
  FireSupportAsset:
    description: Indirect fire or air support resource
    attributes: [assetType, munitionType, range, assignedUnit]
  CommandPost:
    description: A command and control facility
    attributes: [echelon, location, commanderRank, subordinateUnits]
  OrderType:
    description: Type of military command order
    attributes: [orderClass, format, issuingAuthority, timeOfIssue]
  IntelSummary:
    description: Intelligence assessment document
    attributes: [classification, period, threatAssessment, keyFindings]
  SensorPlatform:
    description: ISR collection asset
    attributes: [platformType, sensor, coverageArea, updateRate]
  TargetEntity:
    description: Enemy element under surveillance
    attributes: [targetType, location, activity, priority]
  ObservationEvent:
    description: A recorded ISR observation
    attributes: [observedBy, targetEntity, location, time, confidence]
"""


class OntoGPTAgent:
    """
    OntoGPT-style baseline: schema-guided single-pass extraction.
    Extracts ontology from domain documents using a predefined schema.
    """

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def run(self, cqs: list, user_story: str, domain_docs: str = "") -> dict:
        """
        Single-pass schema extraction from domain documents.

        Args:
            cqs: Competency questions (used only to scope extraction).
            user_story: Domain user story.
            domain_docs: Raw domain documentation text.

        Returns:
            harness-compatible result dict.
        """
        if hasattr(self.llm_client, "reset_stats"):
            self.llm_client.reset_stats()

        print(f"  [OntoGPT] Single-pass schema extraction from domain documents...")
        t_start = time.time()

        # Derive CQ scope for the prompt
        cq_texts = [cq["question"] if isinstance(cq, dict) else cq for cq in cqs[:10]]
        cq_sample = "\n".join(f"- {q}" for q in cq_texts)

        doc_snippet = domain_docs[:4000] if domain_docs else user_story[:2000]

        prompt = (
            "You are an ontology engineer using schema-guided extraction.\n\n"
            "TASK: Extract an OWL 2 ontology from the domain text below, "
            "conforming to the provided LinkML schema.\n\n"
            f"SCHEMA:\n{MILITARY_SCHEMA}\n\n"
            f"DOMAIN TEXT:\n{doc_snippet}\n\n"
            f"SAMPLE COMPETENCY QUESTIONS (for scoping):\n{cq_sample}\n\n"
            "OUTPUT REQUIREMENTS:\n"
            "1. Use prefix: @prefix : <http://coha.org/military#>\n"
            "2. Declare owl:Class for every schema class\n"
            "3. Declare owl:ObjectProperty / owl:DatatypeProperty for all attributes\n"
            "4. Add rdfs:subClassOf, rdfs:domain, rdfs:range where applicable\n"
            "5. Add rdfs:label for all declarations\n"
            "6. Return ONLY valid Turtle — no markdown, no explanation\n\n"
            "Generate the complete ontology:"
        )

        ontology_ttl = ""
        try:
            raw = self.llm_client.generate(system="", user=prompt, max_tokens=4096)
            ontology_ttl = self._clean_turtle(raw)
        except Exception as e:
            logger.error(f"OntoGPT extraction failed: {e}")

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
            "usage_stats": (
                self.llm_client.get_usage_stats()
                if hasattr(self.llm_client, "get_usage_stats") else {}
            ),
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
