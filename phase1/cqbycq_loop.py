"""
Phase 1: CQbyCQ Loop for iterative ontology construction.

Implements the CQbyCQ methodology: for each Competency Question,
generate OWL axioms that extend the current ontology to answer that CQ.
Each iteration builds upon the previous, producing a coherent ontology.
"""

import time
import anthropic
from typing import Optional


class CQbyCQLoop:
    """
    Implements the CQbyCQ (Competency Question by Competency Question) loop
    for automated OWL ontology construction.

    Each CQ is processed sequentially. The current accumulated ontology
    is passed to the LLM so new axioms are consistent with existing ones.
    """

    def __init__(self, llm_client: anthropic.Anthropic, domain_name: str):
        """
        Initialize the CQbyCQ loop.

        Args:
            llm_client: Anthropic API client instance.
            domain_name: Name of the domain being modeled.
        """
        self.llm_client = llm_client
        self.domain_name = domain_name

    def generate_axioms(self, user_story: str, cq: str, current_ontology_ttl: str) -> str:
        """
        Generate OWL axioms to answer a specific Competency Question.

        Given the user story context, the CQ to answer, and the current
        accumulated ontology, generate new OWL axioms in Turtle format.

        Args:
            user_story: The user story providing agent task context.
            cq: The Competency Question to answer.
            current_ontology_ttl: Current accumulated ontology in Turtle format.

        Returns:
            New OWL axioms as a Turtle/Manchester syntax string.
        """
        current_onto_section = ""
        if current_ontology_ttl.strip():
            current_onto_section = f"""
CURRENT ACCUMULATED ONTOLOGY (Turtle format):
```turtle
{current_ontology_ttl}
```

Ensure your new axioms are consistent with the existing ontology.
Reuse existing classes and properties where appropriate.
Do NOT redefine classes or properties already defined above.
"""
        else:
            current_onto_section = """
This is the first iteration — no existing ontology yet.
Start with the @prefix declarations and core classes.
"""

        prompt = f"""You are an expert ontology engineer working on the {self.domain_name} domain.

USER STORY:
{user_story}

COMPETENCY QUESTION TO ANSWER:
{cq}
{current_onto_section}
Your task: Generate ONLY the NEW OWL axioms in Turtle format needed to answer the above CQ.

Requirements:
1. Use standard OWL 2 vocabulary: owl:Class, owl:ObjectProperty, owl:DatatypeProperty,
   rdfs:subClassOf, rdfs:domain, rdfs:range, owl:Restriction, owl:minCardinality,
   owl:maxCardinality, owl:equivalentClass, owl:disjointWith
2. Include appropriate @prefix declarations if using new prefixes
3. Use the base prefix: @prefix : <http://coha.org/{self.domain_name.lower().replace(' ', '_')}#> .
4. Standard prefixes:
   @prefix owl: <http://www.w3.org/2002/07/owl#> .
   @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
   @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
   @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
5. Return ONLY valid Turtle syntax — no explanations, no markdown code blocks
6. Add rdfs:label annotations for human readability

Generate ONLY the new axioms that address the CQ, without duplicating existing definitions.
Return ONLY the Turtle syntax, starting directly with prefix declarations or axioms:"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.llm_client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                )
                content = response.content[0].text.strip()
                return self._clean_turtle_response(content)
            except anthropic.APIError as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"LLM call failed after {max_retries} attempts: {e}") from e

    def run(self, user_story: str, cqs: list, initial_ontology_ttl: str = "") -> str:
        """
        Run the CQbyCQ loop over all Competency Questions.

        Iterates over all CQs sequentially, accumulating OWL axioms into
        a single ontology Turtle string.

        Args:
            user_story: The user story providing task context.
            cqs: List of Competency Questions to process.
            initial_ontology_ttl: Optional starting ontology in Turtle format.

        Returns:
            Final accumulated ontology as a Turtle string.
        """
        # Start with base prefixes and OWL ontology declaration
        base_prefix = f"""@prefix : <http://coha.org/{self.domain_name.lower().replace(' ', '_')}#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

<http://coha.org/{self.domain_name.lower().replace(' ', '_')}> a owl:Ontology ;
    rdfs:label "{self.domain_name} Ontology" ;
    rdfs:comment "Automatically generated ontology via CQbyCQ loop for COHA framework." .

"""

        if initial_ontology_ttl.strip():
            accumulated_ontology = initial_ontology_ttl
        else:
            accumulated_ontology = base_prefix

        for i, cq in enumerate(cqs):
            print(f"  [CQbyCQ] Processing CQ {i+1}/{len(cqs)}: {cq[:80]}...")
            try:
                new_axioms = self.generate_axioms(user_story, cq, accumulated_ontology)
                if new_axioms.strip():
                    accumulated_ontology = self._merge_ontology(accumulated_ontology, new_axioms)
            except RuntimeError as e:
                print(f"  [CQbyCQ] Warning: Failed to generate axioms for CQ {i+1}: {e}")
                continue

        return accumulated_ontology

    def _clean_turtle_response(self, text: str) -> str:
        """
        Clean LLM response to extract pure Turtle syntax.

        Args:
            text: Raw LLM response text.

        Returns:
            Cleaned Turtle syntax string.
        """
        # Remove markdown code blocks if present
        if "```turtle" in text:
            start = text.find("```turtle") + len("```turtle")
            end = text.find("```", start)
            if end != -1:
                text = text[start:end]
        elif "```" in text:
            start = text.find("```") + 3
            # Skip language identifier line if present
            newline_pos = text.find("\n", start)
            if newline_pos != -1 and text[start:newline_pos].strip().lower() in ("turtle", "ttl", ""):
                start = newline_pos + 1
            end = text.find("```", start)
            if end != -1:
                text = text[start:end]

        return text.strip()

    def _merge_ontology(self, base_ttl: str, new_axioms: str) -> str:
        """
        Merge new axioms into the existing ontology, avoiding duplicate prefixes.

        Args:
            base_ttl: Current accumulated ontology in Turtle format.
            new_axioms: New axioms to add.

        Returns:
            Merged ontology string.
        """
        # Extract prefix declarations from new_axioms
        base_lines = base_ttl.strip().split("\n")
        new_lines = new_axioms.strip().split("\n")

        # Collect existing prefixes
        existing_prefixes = set()
        for line in base_lines:
            if line.startswith("@prefix"):
                existing_prefixes.add(line.strip())

        # Filter new axioms to avoid duplicate prefix declarations
        filtered_new_lines = []
        for line in new_lines:
            if line.startswith("@prefix"):
                if line.strip() not in existing_prefixes:
                    filtered_new_lines.append(line)
                    existing_prefixes.add(line.strip())
            else:
                filtered_new_lines.append(line)

        new_content = "\n".join(filtered_new_lines).strip()

        if new_content:
            return base_ttl.rstrip() + "\n\n# --- Axioms for next CQ ---\n" + new_content + "\n"
        return base_ttl


if __name__ == "__main__":
    import os
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    loop = CQbyCQLoop(client, "Smart Building Management")

    user_story = "As a building manager, I want to monitor HVAC zones and detect anomalies."
    cqs = [
        "What are the different types of sensors in a smart building?",
        "What is the relationship between an HVAC zone and its temperature setpoint?",
    ]

    result = loop.run(user_story, cqs)
    print("Generated ontology (first 500 chars):")
    print(result[:500])
