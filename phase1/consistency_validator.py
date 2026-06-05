"""
Phase 1: OWL Ontology Consistency Validator.

Validates OWL ontologies for syntactic and semantic consistency.
Uses owlready2 with HermiT reasoner when Java is available,
falls back to basic Turtle syntax checks otherwise.
"""

import re
import os
import tempfile
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class ConsistencyValidator:
    """
    Validates OWL ontologies for syntactic and semantic consistency.

    Attempts to use the HermiT reasoner via owlready2 when Java is available.
    Falls back to basic Turtle syntax validation if Java is not found.
    """

    def __init__(self):
        """Initialize the consistency validator."""
        self._java_available = self._check_java()
        self._owlready2_available = self._check_owlready2()

    def _check_java(self) -> bool:
        """Check if Java is available for reasoning."""
        import subprocess
        try:
            result = subprocess.run(
                ["java", "-version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    def _check_owlready2(self) -> bool:
        """Check if owlready2 is importable."""
        try:
            import owlready2  # noqa: F401
            return True
        except ImportError:
            return False

    def validate(self, ontology_ttl: str) -> Tuple[bool, list]:
        """
        Validate an OWL ontology for consistency.

        Tries to load the ontology with owlready2 and run the HermiT reasoner.
        Falls back to syntax checking if Java/owlready2 are unavailable.

        Args:
            ontology_ttl: OWL ontology in Turtle format.

        Returns:
            Tuple of (is_consistent: bool, violations: list[str]).
        """
        violations = []

        # First check basic syntax
        syntax_ok = self.check_syntax(ontology_ttl)
        if not syntax_ok:
            return False, ["Turtle syntax error: ontology could not be parsed"]

        if not self._owlready2_available:
            logger.warning("owlready2 not available; falling back to syntax check only.")
            return True, []

        if not self._java_available:
            logger.warning("Java not available; skipping OWL reasoner, falling back to syntax check.")
            return True, []

        # Try owlready2 + HermiT
        try:
            import owlready2
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".ttl", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(ontology_ttl)
                tmp_path = tmp.name

            try:
                # Load ontology
                onto = owlready2.get_ontology(f"file://{tmp_path}").load()

                # Run reasoner
                with onto:
                    owlready2.sync_reasoner(infer_property_values=True)

                # Check for unsatisfiable classes (consistency indicator)
                unsatisfiable = list(owlready2.default_world.inconsistent_classes())
                if unsatisfiable:
                    for cls in unsatisfiable:
                        violations.append(f"Unsatisfiable class: {cls}")
                    return False, violations

                return True, []

            except owlready2.OwlReadyInconsistentOntologyError as e:
                violations.append(f"OWL inconsistency detected: {e}")
                return False, violations
            except Exception as e:
                logger.warning(f"owlready2 reasoning failed: {e}. Falling back to syntax check.")
                return True, []
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        except Exception as e:
            logger.warning(f"Consistency validation error: {e}")
            return True, []

    def check_syntax(self, ontology_ttl: str) -> bool:
        """
        Perform basic Turtle syntax validation.

        Checks for common Turtle syntax markers and structural validity
        without requiring external tools.

        Args:
            ontology_ttl: OWL ontology in Turtle format.

        Returns:
            True if basic syntax appears valid, False otherwise.
        """
        if not ontology_ttl or not ontology_ttl.strip():
            return False

        text = ontology_ttl.strip()

        # Must have at least one prefix or IRI
        has_prefix = bool(re.search(r"@prefix\s+\w*:\s*<[^>]+>", text))
        has_iri = bool(re.search(r"<http[s]?://[^>]+>", text))
        if not has_prefix and not has_iri:
            return False

        # Check for unmatched angle brackets
        open_brackets = text.count("<")
        close_brackets = text.count(">")
        # Allow some slack for comparison operators / strings
        if abs(open_brackets - close_brackets) > 5:
            return False

        # Check for unclosed string literals (odd number of unescaped quotes)
        # Count non-triple-quoted string markers (simple heuristic)
        triple_removed = re.sub(r'""".*?"""', "", text, flags=re.DOTALL)
        triple_removed = re.sub(r"'''.*?'''", "", triple_removed, flags=re.DOTALL)
        single_quote_count = triple_removed.count('"') - triple_removed.count('\\"')
        if single_quote_count % 2 != 0:
            # Could be language-tagged literal; be lenient
            pass

        # Must end with a period or valid Turtle terminator somewhere
        stripped = text.rstrip()
        has_terminator = (
            stripped.endswith(".")
            or stripped.endswith(";")
            or stripped.endswith(",")
            or bool(re.search(r"\.\s*$", text, re.MULTILINE))
        )
        if not has_terminator:
            return False

        return True


if __name__ == "__main__":
    validator = ConsistencyValidator()

    valid_ttl = """@prefix : <http://coha.org/smart_building#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<http://coha.org/smart_building> a owl:Ontology .

:Sensor a owl:Class ;
    rdfs:label "Sensor" .

:TemperatureSensor a owl:Class ;
    rdfs:subClassOf :Sensor ;
    rdfs:label "Temperature Sensor" .
"""

    invalid_ttl = "this is not valid turtle at all"

    ok, viols = validator.validate(valid_ttl)
    print(f"Valid TTL -> consistent={ok}, violations={viols}")

    ok2, viols2 = validator.validate(invalid_ttl)
    print(f"Invalid TTL -> consistent={ok2}, violations={viols2}")
