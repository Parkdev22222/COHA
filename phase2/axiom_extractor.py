"""
Phase 2: OWL Axiom Extractor.

Parses OWL ontologies in Turtle format using regex-based extraction
(no external parser required). Extracts classes, object properties,
data properties, subclass axioms, and cardinality constraints.
"""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


class AxiomExtractor:
    """
    Extracts structured axioms from OWL ontologies in Turtle format.

    Uses regex-based parsing to handle a wide variety of Turtle serializations
    without requiring external RDF parsing libraries.
    """

    def __init__(self):
        """Initialize the axiom extractor."""
        pass

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def extract_from_ttl(self, ontology_ttl: str) -> dict:
        """
        Extract all axioms from a Turtle-format OWL ontology.

        Args:
            ontology_ttl: OWL ontology in Turtle format.

        Returns:
            dict with keys:
                - classes: list of class name strings
                - object_properties: list of dicts {name, domain, range}
                - data_properties: list of dicts {name, domain, range_type}
                - subclass_axioms: list of dicts {subclass, superclass}
                - cardinality_constraints: list of dicts {class, property, min_card, max_card}
        """
        prefixes = self._extract_prefixes(ontology_ttl)
        expanded = self._apply_prefixes(ontology_ttl, prefixes)

        # Use expanded IRI form for class/property extraction
        classes = self._extract_classes(expanded)
        obj_props = self._extract_object_properties(expanded)
        data_props = self._extract_data_properties(expanded)
        cardinality_constraints = self._extract_cardinality_constraints(expanded)

        # Subclass axioms: run on BOTH expanded and original (prefixed) forms
        subclass_axioms = self._extract_subclass_axioms(expanded, ontology_ttl)

        return {
            "classes": classes,
            "object_properties": obj_props,
            "data_properties": data_props,
            "subclass_axioms": subclass_axioms,
            "cardinality_constraints": cardinality_constraints,
        }

    def extract_from_llm_response(self, response: str) -> dict:
        """
        Extract axioms from free-form LLM-generated ontology text.

        Handles responses that may contain mixed Turtle code blocks and
        natural language explanations.

        Args:
            response: LLM-generated text potentially containing Turtle.

        Returns:
            Same dict structure as extract_from_ttl.
        """
        # Try to extract Turtle code blocks first
        turtle_blocks = re.findall(
            r"```(?:turtle|ttl)?\s*\n(.*?)```",
            response,
            re.DOTALL | re.IGNORECASE,
        )

        if turtle_blocks:
            combined_ttl = "\n".join(turtle_blocks)
        else:
            # Treat entire response as potential Turtle
            combined_ttl = response

        return self.extract_from_ttl(combined_ttl)

    # ------------------------------------------------------------------
    # Private helpers: prefix handling
    # ------------------------------------------------------------------

    def _extract_prefixes(self, ttl: str) -> dict:
        """Extract prefix -> IRI namespace mappings from Turtle text."""
        prefixes = {}
        pattern = re.compile(
            r"@prefix\s+(\w*):\s*<([^>]+)>",
            re.MULTILINE,
        )
        for match in pattern.finditer(ttl):
            prefix, iri = match.group(1), match.group(2)
            prefixes[prefix] = iri
        return prefixes

    def _apply_prefixes(self, ttl: str, prefixes: dict) -> str:
        """
        Expand prefixed names to full IRIs for easier regex matching.

        Handles both the default (empty) prefix and named prefixes.
        Only expands known prefixes; unknown ones are left as-is.
        """
        result = ttl
        # Sort: process non-empty prefixes first, then the empty/default prefix
        sorted_prefixes = sorted(prefixes.items(), key=lambda kv: (kv[0] == "", kv[0]))

        for prefix, iri in sorted_prefixes:
            sep = "#" if not iri.endswith("#") and not iri.endswith("/") else ""

            if prefix == "":
                # Default prefix: match standalone :LocalName (not preceded by another colon/word)
                pattern = re.compile(r"(?<![:/\w]):([A-Za-z_]\w*)")
            else:
                # Named prefix: match prefix:LocalName at word boundary
                pattern = re.compile(rf"(?<![:/\w]){re.escape(prefix)}:([A-Za-z_]\w*)")

            result = pattern.sub(
                lambda m, _iri=iri, _sep=sep: f"<{_iri}{_sep}{m.group(1)}>",
                result,
            )
        return result

    def _local_name(self, iri_or_prefixed: str) -> str:
        """Extract the local name from an IRI, prefixed name, or raw string."""
        # Strip angle brackets
        s = iri_or_prefixed.strip("<>")
        # Take fragment or last path segment (full IRI)
        if "#" in s:
            return s.rsplit("#", 1)[-1]
        if "/" in s:
            return s.rsplit("/", 1)[-1]
        # Handle prefixed name: prefix:LocalName or :LocalName
        if ":" in s:
            return s.rsplit(":", 1)[-1]
        return s

    # ------------------------------------------------------------------
    # Private helpers: extraction routines
    # ------------------------------------------------------------------

    def _extract_classes(self, ttl: str) -> list:
        """Extract OWL class names from the ontology."""
        classes = set()

        # Pattern: <IRI> a owl:Class  or  <IRI> rdf:type owl:Class
        pattern = re.compile(
            r"<([^>]+)>\s+(?:a|rdf:type)\s+[<\"]?(?:http://www\.w3\.org/2002/07/owl#)?[<\"]?Class[>\"]?",
            re.IGNORECASE,
        )
        for m in pattern.finditer(ttl):
            classes.add(self._local_name(f"<{m.group(1)}>"))

        # Pattern: owl:Class declarations (block style)
        pattern2 = re.compile(
            r"<([^>]+)>\s+(?:a|rdf:type)[^.;]*owl#Class",
            re.IGNORECASE | re.DOTALL,
        )
        for m in pattern2.finditer(ttl):
            classes.add(self._local_name(f"<{m.group(1)}>"))

        return sorted(classes)

    def _extract_object_properties(self, ttl: str) -> list:
        """Extract OWL ObjectProperty declarations with domain/range."""
        props = {}

        # After prefix expansion, properties look like:
        # <iri#propName> a <...owl#ObjectProperty> ; <...rdfs#domain> <iri#Domain> ; ...
        # Match the subject IRI followed by owl#ObjectProperty anywhere in the statement

        # Broad pass: find all ObjectProperty subject IRIs
        # Pattern: subject IRI followed by 'a' or rdf:type, then owl#ObjectProperty
        op_pattern = re.compile(
            r"(<[^>]+>)\s+(?:a|<[^>]*rdf-syntax[^>]*type[^>]*>)\s+<[^>]*owl#ObjectProperty[^>]*>",
            re.IGNORECASE,
        )
        for m in op_pattern.finditer(ttl):
            name = self._local_name(m.group(1))
            props[name] = {"name": name, "domain": None, "range": None}

        # Domain assertions: <propIRI> ... rdfs#domain ... <DomainIRI>
        domain_pattern = re.compile(
            r"(<[^>]+>)\s+<[^>]*rdfs[^>]*domain[^>]*>\s+(<[^>]+>)",
            re.IGNORECASE,
        )
        for m in domain_pattern.finditer(ttl):
            prop_name = self._local_name(m.group(1))
            domain = self._local_name(m.group(2))
            if prop_name in props:
                props[prop_name]["domain"] = domain
            else:
                props[prop_name] = {"name": prop_name, "domain": domain, "range": None}

        # Range assertions (exclude xsd: types — those belong to data properties)
        range_pattern = re.compile(
            r"(<[^>]+>)\s+<[^>]*rdfs[^>]*range[^>]*>\s+(<[^>]+>)",
            re.IGNORECASE,
        )
        for m in range_pattern.finditer(ttl):
            prop_name = self._local_name(m.group(1))
            range_val_iri = m.group(2)
            # Skip xsd types — they belong to data properties
            if "XMLSchema" in range_val_iri or "xsd#" in range_val_iri.lower():
                continue
            range_val = self._local_name(range_val_iri)
            if prop_name in props:
                props[prop_name]["range"] = range_val

        return list(props.values())

    def _extract_data_properties(self, ttl: str) -> list:
        """Extract OWL DatatypeProperty declarations with domain/range type."""
        props = {}

        # Find DatatypeProperty declarations (expanded IRI form)
        dp_pattern = re.compile(
            r"(<[^>]+>)\s+(?:a|<[^>]*rdf-syntax[^>]*type[^>]*>)\s+<[^>]*owl#DatatypeProperty[^>]*>",
            re.IGNORECASE,
        )
        for m in dp_pattern.finditer(ttl):
            name = self._local_name(m.group(1))
            props[name] = {"name": name, "domain": None, "range_type": None}

        # Domain assertions
        domain_pattern = re.compile(
            r"(<[^>]+>)\s+<[^>]*rdfs[^>]*domain[^>]*>\s+(<[^>]+>)",
            re.IGNORECASE,
        )
        for m in domain_pattern.finditer(ttl):
            prop_name = self._local_name(m.group(1))
            if prop_name in props:
                props[prop_name]["domain"] = self._local_name(m.group(2))

        # XSD range types
        xsd_range_pattern = re.compile(
            r"(<[^>]+>)\s+<[^>]*rdfs[^>]*range[^>]*>\s+(<[^>]*XMLSchema[^>]*>)",
            re.IGNORECASE,
        )
        for m in xsd_range_pattern.finditer(ttl):
            prop_name = self._local_name(m.group(1))
            if prop_name in props:
                props[prop_name]["range_type"] = self._local_name(m.group(2))

        return list(props.values())

    def _extract_subclass_axioms(self, expanded_ttl: str, original_ttl: str = "") -> list:
        """Extract rdfs:subClassOf axioms from both expanded and original Turtle."""
        axioms = []
        seen = set()

        def _add(sub, sup):
            if sub and sup and "Restriction" not in sup and "XMLSchema" not in sup:
                key = (sub, sup)
                if key not in seen:
                    seen.add(key)
                    axioms.append({"subclass": sub, "superclass": sup})

        # --- Pattern on expanded IRI form ---
        # <SubIRI> ... <rdfs#subClassOf> <SupIRI>
        pattern_expanded = re.compile(
            r"(<[^>]+>)[^.]*?<[^>]*rdfs[^>]*subClassOf[^>]*>\s+(<[^>]+>)",
            re.DOTALL | re.IGNORECASE,
        )
        for m in pattern_expanded.finditer(expanded_ttl):
            _add(self._local_name(m.group(1)), self._local_name(m.group(2)))

        # --- Statement-based pattern on original (prefixed) Turtle ---
        source = original_ttl if original_ttl else expanded_ttl
        statements = re.split(r"\s*\.\s*\n", source)
        for stmt in statements:
            # Must contain owl:Class (prefixed form)
            if "owl:Class" not in stmt and "owl#Class" not in stmt:
                continue

            # Extract subject (first IRI or prefixed name on the line)
            subj_match = re.match(r"\s*(<[^>]+>|:[A-Za-z_][a-zA-Z0-9_]*)", stmt)
            if not subj_match:
                continue
            subj_raw = subj_match.group(1)
            sub_name = self._local_name(subj_raw.strip("<>"))

            # Find all subClassOf objects in this statement
            for m in re.finditer(
                r"rdfs:subClassOf\s+(<[^>]+>|:[A-Za-z_][a-zA-Z0-9_]*)",
                stmt,
                re.IGNORECASE,
            ):
                sup_raw = m.group(1)
                sup_name = self._local_name(sup_raw.strip("<>"))
                _add(sub_name, sup_name)

        return axioms

    def _extract_cardinality_constraints(self, ttl: str) -> list:
        """Extract OWL cardinality restrictions from the ontology."""
        constraints = []

        # Match owl:minCardinality and owl:maxCardinality in restriction blocks
        min_pattern = re.compile(
            r"owl#minCardinality[^\d]*(\d+)",
            re.IGNORECASE,
        )
        max_pattern = re.compile(
            r"owl#maxCardinality[^\d]*(\d+)",
            re.IGNORECASE,
        )
        on_prop_pattern = re.compile(
            r"owl#onProperty\s+<([^>]+)>",
            re.IGNORECASE,
        )

        # Find restriction blocks (simplified)
        restriction_pattern = re.compile(
            r"owl#Restriction[^.]*?\.",
            re.DOTALL | re.IGNORECASE,
        )
        for block_match in restriction_pattern.finditer(ttl):
            block = block_match.group(0)
            min_m = min_pattern.search(block)
            max_m = max_pattern.search(block)
            prop_m = on_prop_pattern.search(block)

            if prop_m:
                prop_name = self._local_name(f"<{prop_m.group(1)}>")
                constraints.append({
                    "class": None,  # owning class not easily extractable here
                    "property": prop_name,
                    "min_card": int(min_m.group(1)) if min_m else None,
                    "max_card": int(max_m.group(1)) if max_m else None,
                })

        return constraints


if __name__ == "__main__":
    sample_ttl = """@prefix : <http://coha.org/smart_building#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://coha.org/smart_building> a owl:Ontology .

:Sensor a owl:Class ; rdfs:label "Sensor" .
:TemperatureSensor a owl:Class ; rdfs:subClassOf :Sensor .
:HVACZone a owl:Class ; rdfs:label "HVAC Zone" .

:hasCurrentTemperature a owl:ObjectProperty ;
    rdfs:domain :Sensor ;
    rdfs:range :TemperatureValue .

:temperatureValue a owl:DatatypeProperty ;
    rdfs:domain :TemperatureValue ;
    rdfs:range xsd:float .
"""

    extractor = AxiomExtractor()
    result = extractor.extract_from_ttl(sample_ttl)
    print("Classes:", result["classes"])
    print("Object Properties:", result["object_properties"])
    print("Data Properties:", result["data_properties"])
    print("Subclass Axioms:", result["subclass_axioms"])
