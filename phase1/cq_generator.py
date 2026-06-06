"""
Phase 1: Competency Question (CQ) Generator.

Generates domain-specific CQs from domain documentation and user stories
using an LLM. CQs define the scope of knowledge the ontology must cover.
"""

import re
from typing import Optional

from llm_client import UnifiedLLMClient


class CQGenerator:
    """
    Generates Competency Questions (CQs) for ontology construction.

    CQs are natural language questions that define what the ontology
    must be able to answer. They guide the CQbyCQ loop to produce
    axioms covering the full scope of domain knowledge.
    """

    def __init__(self, llm_client: UnifiedLLMClient, domain_name: str):
        """
        Initialize the CQ generator.

        Args:
            llm_client: UnifiedLLMClient instance.
            domain_name: Name of the domain for which CQs are generated.
        """
        self.llm_client = llm_client
        self.domain_name = domain_name

    def generate(self, domain_docs: str, user_stories: str, n: int) -> list:
        """
        Generate n Competency Questions for the domain.

        Calls the LLM with domain documentation and user stories to generate
        CQs that cover the scope of domain knowledge required.

        Args:
            domain_docs: Textual description of the domain.
            user_stories: User stories describing agent tasks.
            n: Number of CQs to generate.

        Returns:
            List of CQ strings.
        """
        prompt = f"""You are an ontology engineering expert specializing in the domain of {self.domain_name}.

Given the following domain documentation and user stories, generate exactly {n} Competency Questions (CQs).

Competency Questions are natural language questions that define what the ontology must be able to answer.
They should:
1. Cover the key concepts and relationships in the domain
2. Be specific enough to guide ontology axiom generation
3. Be answerable from the domain knowledge described
4. Cover different aspects: entities, relationships, constraints, rules, and processes

DOMAIN DOCUMENTATION:
{domain_docs}

USER STORIES:
{user_stories}

Generate exactly {n} Competency Questions. Format your response as a numbered list:
1. [First CQ]
2. [Second CQ]
...{n}. [Nth CQ]

Focus on questions that would require OWL classes, object properties, data properties,
and axioms to answer properly. Include questions about:
- What types of entities exist in the domain?
- What relationships hold between entities?
- What constraints must be satisfied?
- What rules govern agent behavior?
- What events or states can occur?"""

        content = self.llm_client.generate(system="", user=prompt, max_tokens=2048)
        return self._parse_numbered_list(content, n)

    def _parse_numbered_list(self, text: str, expected_n: int) -> list:
        """
        Parse a numbered list from LLM response text.

        Args:
            text: LLM response containing numbered list.
            expected_n: Expected number of items.

        Returns:
            List of extracted strings.
        """
        lines = text.strip().split("\n")
        cqs = []

        for line in lines:
            line = line.strip()
            # Match patterns like "1.", "1)", "1:" or just numbered lines
            match = re.match(r"^\d+[\.\):\-]\s*(.+)$", line)
            if match:
                cq = match.group(1).strip()
                if cq:
                    cqs.append(cq)

        # If parsing failed, try splitting by newline and filtering
        if not cqs:
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and len(line) > 20:
                    cqs.append(line)

        # Trim or pad to expected count
        if len(cqs) > expected_n:
            cqs = cqs[:expected_n]

        return cqs


if __name__ == "__main__":
    from llm_client import get_client
    client = get_client()
    generator = CQGenerator(client, "Smart Building Management")

    sample_docs = "A smart building has HVAC zones, temperature sensors, and energy meters."
    sample_stories = "As a building manager, I want to detect thermal anomalies automatically."

    cqs = generator.generate(sample_docs, sample_stories, n=5)
    print(f"Generated {len(cqs)} CQs:")
    for i, cq in enumerate(cqs, 1):
        print(f"  {i}. {cq}")
