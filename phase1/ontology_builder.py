"""
Phase 1: Ontology Builder.

Orchestrates the full Phase 1 pipeline:
1. CQ generation via CQGenerator
2. Iterative axiom construction via CQbyCQLoop
3. Consistency validation after each CQ iteration
4. CQ coverage rate computation

Returns a complete OWL ontology in Turtle format along with quality metrics.
"""

import time
import logging
import anthropic
from typing import Optional

from phase1.cq_generator import CQGenerator
from phase1.cqbycq_loop import CQbyCQLoop
from phase1.consistency_validator import ConsistencyValidator

logger = logging.getLogger(__name__)


class OntologyBuilder:
    """
    Builds an OWL ontology automatically from domain documentation and user stories.

    Implements the full Phase 1 pipeline of the COHA framework:
    - Competency Question generation
    - CQbyCQ iterative axiom construction
    - Consistency validation with repair
    - CQ coverage rate computation
    """

    def __init__(
        self,
        llm_client: anthropic.Anthropic,
        domain_name: str,
        consistency_validator: ConsistencyValidator,
    ):
        """
        Initialize the ontology builder.

        Args:
            llm_client: Anthropic API client instance.
            domain_name: Name of the domain being modeled.
            consistency_validator: Validator instance for OWL consistency.
        """
        self.llm_client = llm_client
        self.domain_name = domain_name
        self.validator = consistency_validator
        self.cq_generator = CQGenerator(llm_client, domain_name)
        self.cqbycq_loop = CQbyCQLoop(llm_client, domain_name)

    def build(
        self,
        domain_docs: str,
        user_stories: str,
        n_cqs: int = 10,
    ) -> dict:
        """
        Build an OWL ontology from domain documentation and user stories.

        Runs the full Phase 1 pipeline:
        1. Generates n_cqs Competency Questions
        2. Runs the CQbyCQ loop to construct the ontology
        3. Validates consistency, regenerating inconsistent sections up to MAX_RETRY times
        4. Computes CQ coverage rate

        Args:
            domain_docs: Textual description of the domain.
            user_stories: User stories describing agent tasks.
            n_cqs: Number of CQs to generate.

        Returns:
            dict with keys:
                - ontology_ttl: str - Final ontology in Turtle format
                - cqs: list[str] - Generated competency questions
                - cq_coverage_rate: float - Fraction of CQs answerable from ontology
                - is_consistent: bool - Whether ontology passed consistency check
                - n_iterations: int - Total CQ iterations performed
        """
        from config import MAX_RETRY

        print(f"[OntologyBuilder] Phase 1: Generating {n_cqs} Competency Questions...")
        cqs = self.cq_generator.generate(domain_docs, user_stories, n_cqs)
        print(f"[OntologyBuilder] Generated {len(cqs)} CQs.")

        # Use first user story as representative context
        representative_story = user_stories.strip().split("\n")[0] if user_stories.strip() else user_stories

        ontology_ttl = ""
        n_iterations = 0
        is_consistent = False

        # CQbyCQ loop with consistency validation per CQ
        base_prefix = self._make_base_prefix()
        accumulated = base_prefix

        for i, cq in enumerate(cqs):
            print(f"[OntologyBuilder] CQ {i+1}/{len(cqs)}: {cq[:70]}...")
            success = False

            for attempt in range(MAX_RETRY):
                try:
                    new_axioms = self.cqbycq_loop.generate_axioms(
                        representative_story, cq, accumulated
                    )
                    candidate = self.cqbycq_loop._merge_ontology(accumulated, new_axioms)
                    is_ok, viols = self.validator.validate(candidate)

                    if is_ok:
                        accumulated = candidate
                        n_iterations += 1
                        success = True
                        break
                    else:
                        print(
                            f"[OntologyBuilder] Inconsistency on CQ {i+1} attempt {attempt+1}: "
                            f"{viols[:2]}. Regenerating..."
                        )
                except Exception as e:
                    print(f"[OntologyBuilder] Error on CQ {i+1} attempt {attempt+1}: {e}")

            if not success:
                # Accept the last candidate with a warning rather than skipping entirely
                print(f"[OntologyBuilder] Skipping CQ {i+1} after {MAX_RETRY} failed attempts.")

        ontology_ttl = accumulated

        # Final consistency check
        is_consistent, final_viols = self.validator.validate(ontology_ttl)
        if not is_consistent:
            print(f"[OntologyBuilder] Warning: Final ontology has consistency issues: {final_viols[:3]}")

        # Compute CQ coverage rate
        print("[OntologyBuilder] Computing CQ coverage rate...")
        cq_coverage_rate = self.compute_cq_coverage_rate(cqs, ontology_ttl, self.llm_client)
        print(f"[OntologyBuilder] CQ Coverage Rate: {cq_coverage_rate:.2%}")

        return {
            "ontology_ttl": ontology_ttl,
            "cqs": cqs,
            "cq_coverage_rate": cq_coverage_rate,
            "is_consistent": is_consistent,
            "n_iterations": n_iterations,
        }

    def compute_cq_coverage_rate(
        self,
        cqs: list,
        ontology_ttl: str,
        llm_client: anthropic.Anthropic,
    ) -> float:
        """
        Compute the fraction of CQs answerable from the ontology.

        For each CQ, asks the LLM to judge whether the ontology contains
        sufficient axioms to answer the question.

        Args:
            cqs: List of Competency Questions.
            ontology_ttl: Current ontology in Turtle format.
            llm_client: Anthropic API client.

        Returns:
            Float in [0, 1] representing the fraction of covered CQs.
        """
        if not cqs:
            return 0.0

        covered = 0
        for i, cq in enumerate(cqs):
            prompt = f"""You are an ontology expert evaluating whether a given OWL ontology contains
sufficient axioms to answer a Competency Question (CQ).

ONTOLOGY (Turtle format):
```turtle
{ontology_ttl[:3000]}
```

COMPETENCY QUESTION:
{cq}

Does the ontology contain sufficient classes, properties, and axioms to answer this CQ?
Consider: Are the relevant entity types defined? Are the key relationships modeled?

Answer with exactly one word: YES or NO.
Then on the next line, briefly explain why (one sentence).
"""
            try:
                import time as _time
                for attempt in range(3):
                    try:
                        response = llm_client.messages.create(
                            model="claude-sonnet-4-6",
                            max_tokens=128,
                            messages=[{"role": "user", "content": prompt}],
                        )
                        answer = response.content[0].text.strip().upper()
                        if answer.startswith("YES"):
                            covered += 1
                        break
                    except anthropic.APIError:
                        if attempt < 2:
                            _time.sleep(2 ** attempt)
            except Exception as e:
                logger.warning(f"Coverage check for CQ {i+1} failed: {e}")

        return covered / len(cqs)

    def _make_base_prefix(self) -> str:
        """Generate the base Turtle prefix block for the ontology."""
        slug = self.domain_name.lower().replace(" ", "_")
        return f"""@prefix : <http://coha.org/{slug}#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

<http://coha.org/{slug}> a owl:Ontology ;
    rdfs:label "{self.domain_name} Ontology" ;
    rdfs:comment "Automatically generated ontology via CQbyCQ loop for COHA framework." .

"""


if __name__ == "__main__":
    import os
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    validator = ConsistencyValidator()
    builder = OntologyBuilder(client, "Smart Building Management", validator)

    docs = (
        "A smart building contains HVAC zones, temperature sensors, CO2 sensors, "
        "energy meters, and occupancy zones. Actuators control HVAC systems."
    )
    stories = "As a building manager, I want the agent to detect thermal anomalies and issue control commands."

    result = builder.build(docs, stories, n_cqs=3)
    print(f"Built ontology: consistent={result['is_consistent']}, "
          f"coverage={result['cq_coverage_rate']:.0%}, "
          f"iterations={result['n_iterations']}")
    print(result["ontology_ttl"][:400])
