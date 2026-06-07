"""
Axiom Generator: generates delta-Oi (OWL axioms for a single CQ).

Supports two context modes:
  - Context Reset (COHA): fresh context per CQ, inject only Handoff Artifact
  - Full Accumulation (Vanilla): pass growing full ontology TTL
"""
import re
import logging
from coha.handoff_artifact import HandoffArtifact

logger = logging.getLogger(__name__)

BASE_PREFIXES = """@prefix : <http://coha.org/military#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> ."""


class AxiomGenerator:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def generate_with_reset(self, cq: str, user_story: str, handoff: HandoffArtifact) -> str:
        """Generate delta-Oi using context reset: inject only the handoff artifact."""
        system_prompt = (
            "You are an expert ontology engineer for the military tactical domain.\n"
            "Apply the following accumulated rules strictly when generating OWL axioms.\n\n"
            + handoff.to_prompt_text()
        )
        user_prompt = (
            f"User Story: {user_story}\n\n"
            f"Current Ontology Summary:\n{handoff.accumulated_ontology.to_summary()}\n\n"
            f"Competency Question: {cq}\n\n"
            "Generate ONLY the NEW OWL axioms in Turtle format (delta-Oi) needed to answer this CQ.\n"
            "Requirements:\n"
            "1. Use base prefix: @prefix : <http://coha.org/military#>\n"
            "2. Include standard OWL 2 vocabulary (owl:Class, owl:ObjectProperty, rdfs:subClassOf, etc.)\n"
            "3. Add rdfs:label for every class and property\n"
            "4. Do NOT redefine classes/properties already in the current ontology\n"
            "5. Return ONLY valid Turtle syntax -- no markdown, no explanations\n\n"
            "Generate delta-Oi:"
        )
        response = self.llm_client.generate(system=system_prompt, user=user_prompt, max_tokens=2048)
        return self._clean_turtle(response)

    def generate_full_context(self, cq: str, user_story: str, accumulated_ttl: str) -> str:
        """Generate delta-Oi with full accumulated ontology in context (Vanilla CQbyCQ)."""
        onto_section = (
            f"\nACCUMULATED ONTOLOGY:\n```turtle\n{accumulated_ttl}\n```\n\n"
            "Ensure new axioms are consistent with the existing ontology. "
            "Do NOT redefine existing classes or properties.\n"
            if accumulated_ttl.strip()
            else "\nThis is the first CQ -- no existing ontology yet.\n"
        )
        user_prompt = (
            f"You are an ontology engineer for the military tactical domain.\n\n"
            f"User Story: {user_story}"
            f"{onto_section}"
            f"Competency Question: {cq}\n\n"
            "Generate ONLY the new OWL axioms in Turtle format to answer this CQ.\n"
            "Return ONLY valid Turtle syntax.\n\n"
            "Generate:"
        )
        response = self.llm_client.generate(system="", user=user_prompt, max_tokens=2048)
        return self._clean_turtle(response)

    @staticmethod
    def _clean_turtle(text: str) -> str:
        """Extract clean Turtle from LLM response."""
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
