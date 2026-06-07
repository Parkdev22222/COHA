"""
Phase 1: Text2Onto-inspired Ontology Learner.

Implements a Text2Onto-style ontology learning pipeline:
  1. Concept extraction  — identify domain entity types from raw text
  2. Taxonomy construction — build is-a (rdfs:subClassOf) hierarchy
  3. Relation extraction  — identify object properties and datatype properties
  4. OWL synthesis        — assemble extracted elements into valid Turtle

Reference: Cimiano & Völker (2005), "text2onto — A framework for ontology
           learning and data-driven change discovery"
"""

import re
import logging

from llm_client import UnifiedLLMClient

logger = logging.getLogger(__name__)


class Text2OntoLearner:
    """
    Text2Onto-inspired ontology learner.

    Unlike CQbyCQ (which builds the ontology incrementally per CQ),
    Text2Onto extracts ontological elements from the raw text corpus
    in a structured multi-pass NLP pipeline and then synthesises OWL.
    """

    def __init__(self, llm_client: UnifiedLLMClient, domain_name: str):
        self.llm_client = llm_client
        self.domain_name = domain_name
        slug = domain_name.lower().replace(" ", "_")
        self._base_uri = f"http://coha.org/{slug}"
        self._base_prefix = (
            f"@prefix : <{self._base_uri}#> .\n"
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def learn(self, domain_docs: str) -> dict:
        """
        Run the full Text2Onto pipeline on domain documents.

        Args:
            domain_docs: Domain documentation text.

        Returns:
            dict with keys:
              - ontology_ttl: str  — final OWL ontology in Turtle format
              - concepts: list[str]
              - hierarchy: list[dict]
              - relations: list[dict]
        """
        print("[Text2Onto] Step 1: Extracting concepts...")
        concepts = self._extract_concepts(domain_docs)
        print(f"[Text2Onto] Extracted {len(concepts)} concepts.")

        print("[Text2Onto] Step 2: Building is-a taxonomy...")
        hierarchy = self._build_taxonomy(concepts, domain_docs)

        print("[Text2Onto] Step 3: Extracting object/datatype properties...")
        relations = self._extract_relations(concepts, domain_docs)

        print("[Text2Onto] Step 4: Synthesising OWL ontology...")
        ontology_ttl = self._synthesize_owl(concepts, hierarchy, relations)

        return {
            "ontology_ttl": ontology_ttl,
            "concepts": concepts,
            "hierarchy": hierarchy,
            "relations": relations,
        }

    # ------------------------------------------------------------------
    # Extraction steps
    # ------------------------------------------------------------------

    def _extract_concepts(self, text: str) -> list:
        """Pass 1 — extract domain entity types (OWL classes) from text."""
        prompt = (
            f"You are an ontology engineer performing concept extraction "
            f"for the {self.domain_name} domain.\n\n"
            "TASK: Extract all significant domain concepts (entity types / classes) "
            "from the text below.\n"
            "Focus on nouns that represent *types* of entities, not individuals or values.\n\n"
            f"TEXT:\n{text[:4000]}\n\n"
            "OUTPUT FORMAT:\n"
            "Return a plain numbered list, one concept per line, in PascalCase.\n"
            "Example: TemperatureSensor, HVACZone, EnergyMeter.\n"
            "Exclude generic terms like Thing, Object, Data.\n"
            "Return 10-30 concepts.\n\n"
            "CONCEPTS:"
        )
        response = self.llm_client.generate(system="", user=prompt, max_tokens=1024)
        return self._parse_concept_list(response)

    def _build_taxonomy(self, concepts: list, text: str) -> list:
        """Pass 2 — build rdfs:subClassOf hierarchy from extracted concepts."""
        concepts_str = "\n".join(f"- {c}" for c in concepts[:30])
        prompt = (
            f"You are an ontology engineer building an is-a taxonomy "
            f"for the {self.domain_name} domain.\n\n"
            f"CONCEPTS:\n{concepts_str}\n\n"
            f"DOMAIN TEXT (for context):\n{text[:2000]}\n\n"
            "TASK: Identify rdfs:subClassOf (is-a) relationships between the concepts.\n"
            "Only include genuine 'X is a type of Y' pairs — "
            "not 'has', 'uses', 'part-of', or 'located-in' relationships.\n\n"
            "OUTPUT FORMAT — one pair per line:\n"
            "SubClass -> SuperClass\n\n"
            "SUBCLASS RELATIONSHIPS:"
        )
        response = self.llm_client.generate(system="", user=prompt, max_tokens=512)
        return self._parse_hierarchy(response)

    def _extract_relations(self, concepts: list, text: str) -> list:
        """Pass 3 — extract object properties and datatype properties."""
        concepts_str = ", ".join(concepts[:20])
        prompt = (
            f"You are an ontology engineer extracting OWL properties "
            f"for the {self.domain_name} domain.\n\n"
            f"KNOWN CONCEPTS: {concepts_str}\n\n"
            f"DOMAIN TEXT:\n{text[:3000]}\n\n"
            "TASK: Identify:\n"
            "1. Object properties (between classes):\n"
            "   Format → DomainClass --propertyName--> RangeClass\n"
            "2. Datatype properties (attributes with literal values):\n"
            "   Format → Class .attributeName: xsd:datatype\n"
            "   Valid xsd types: xsd:string, xsd:float, xsd:integer, "
            "xsd:boolean, xsd:dateTime\n\n"
            "Return each property on its own line using exactly those formats.\n\n"
            "PROPERTIES:"
        )
        response = self.llm_client.generate(system="", user=prompt, max_tokens=1024)
        return self._parse_relations(response)

    # ------------------------------------------------------------------
    # OWL synthesis
    # ------------------------------------------------------------------

    def _synthesize_owl(self, concepts: list, hierarchy: list, relations: list) -> str:
        """Assemble all extracted elements into valid OWL Turtle."""
        parts = [
            self._base_prefix,
            self._fmt_block(
                f"<{self._base_uri}>",
                [
                    ("a", "owl:Ontology"),
                    ("rdfs:label", f'"{self.domain_name} Ontology"'),
                    ("rdfs:comment",
                     '"Ontology generated via Text2Onto-style extraction for COHA."'),
                ],
            ),
            "",
        ]

        defined_classes: set = set()

        for c in concepts:
            name = self._class_name(c)
            if name and name not in defined_classes:
                parts.append(
                    self._fmt_block(
                        f":{name}",
                        [("a", "owl:Class"), ("rdfs:label", f'"{name}"')],
                    )
                )
                parts.append("")
                defined_classes.add(name)

        for h in hierarchy:
            sub = self._class_name(h.get("subclass", ""))
            sup = self._class_name(h.get("superclass", ""))
            if sub and sup and sub in defined_classes and sup in defined_classes:
                parts.append(f":{sub} rdfs:subClassOf :{sup} .")
        if hierarchy:
            parts.append("")

        defined_props: set = set()

        for r in relations:
            if r.get("type") != "object":
                continue
            prop = self._prop_name(r.get("name", ""))
            dom = self._class_name(r.get("domain", ""))
            rng = self._class_name(r.get("range", ""))
            if not prop or prop in defined_props:
                continue
            po = [("a", "owl:ObjectProperty"), ("rdfs:label", f'"{prop}"')]
            if dom and dom in defined_classes:
                po.append(("rdfs:domain", f":{dom}"))
            if rng and rng in defined_classes:
                po.append(("rdfs:range", f":{rng}"))
            parts.append(self._fmt_block(f":{prop}", po))
            parts.append("")
            defined_props.add(prop)

        for r in relations:
            if r.get("type") != "datatype":
                continue
            prop = self._prop_name(r.get("name", ""))
            dom = self._class_name(r.get("domain", ""))
            dtype = r.get("range", "xsd:string")
            if not dtype.startswith("xsd:"):
                dtype = "xsd:string"
            if not prop or prop in defined_props:
                continue
            po = [("a", "owl:DatatypeProperty"), ("rdfs:label", f'"{prop}"')]
            if dom and dom in defined_classes:
                po.append(("rdfs:domain", f":{dom}"))
            po.append(("rdfs:range", dtype))
            parts.append(self._fmt_block(f":{prop}", po))
            parts.append("")
            defined_props.add(prop)

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    def _parse_concept_list(self, text: str) -> list:
        concepts = []
        for line in text.strip().split("\n"):
            line = re.sub(r"^[\d]+[.)]\s*", "", line.strip())
            line = re.sub(r"^[-*•]\s*", "", line)
            line = re.split(r"\s*[-–:]\s+", line)[0].strip()
            name = self._class_name(line)
            if name and len(name) > 1:
                concepts.append(name)
        return list(dict.fromkeys(concepts))

    def _parse_hierarchy(self, text: str) -> list:
        pairs = []
        for line in text.strip().split("\n"):
            if "->" in line:
                parts = line.split("->")
                if len(parts) == 2:
                    sub = parts[0].strip().lstrip("-").strip()
                    sup = parts[1].strip()
                    if sub and sup:
                        pairs.append({"subclass": sub, "superclass": sup})
        return pairs

    def _parse_relations(self, text: str) -> list:
        relations = []
        for line in text.strip().split("\n"):
            line = line.strip()
            m = re.match(r"(\w[\w\s]*)--(\w+)-->\s*(\w[\w\s]*)", line)
            if m:
                relations.append({
                    "type": "object",
                    "domain": m.group(1).strip(),
                    "name": m.group(2).strip(),
                    "range": m.group(3).strip(),
                })
                continue
            m = re.match(r"(\w+)\s*\.(\w+)\s*:\s*(xsd:\w+|\w+)", line)
            if m:
                dtype = m.group(3)
                if not dtype.startswith("xsd:"):
                    dtype = f"xsd:{dtype}"
                relations.append({
                    "type": "datatype",
                    "domain": m.group(1),
                    "name": m.group(2),
                    "range": dtype,
                })
        return relations

    # ------------------------------------------------------------------
    # Turtle formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt_block(subject: str, po_pairs: list) -> str:
        """Format a Turtle subject block: subject p1 o1 ; p2 o2 ."""
        lines = [f"{subject} {po_pairs[0][0]} {po_pairs[0][1]}"]
        for pred, obj in po_pairs[1:]:
            lines.append(f"    {pred} {obj}")
        return " ;\n".join(lines) + " ."

    @staticmethod
    def _class_name(text: str) -> str:
        text = re.sub(r"[^\w\s]", "", str(text)).strip()
        return "".join(w.capitalize() for w in re.split(r"[\s_]+", text) if w)

    @staticmethod
    def _prop_name(text: str) -> str:
        text = re.sub(r"[^\w\s]", "", str(text)).strip()
        words = [w for w in re.split(r"[\s_]+", text) if w]
        if not words:
            return ""
        return words[0].lower() + "".join(w.capitalize() for w in words[1:])


if __name__ == "__main__":
    from llm_client import get_client

    client = get_client()
    learner = Text2OntoLearner(client, "Smart Building Management")
    docs = (
        "A smart building contains HVAC zones, temperature sensors, CO2 sensors, "
        "energy meters, and occupancy zones. Actuators control HVAC systems."
    )
    result = learner.learn(docs)
    print(f"Concepts ({len(result['concepts'])}): {result['concepts']}")
    print(f"Hierarchy: {result['hierarchy']}")
    print(f"Relations: {len(result['relations'])} extracted")
    print("\nOntology (first 500 chars):")
    print(result["ontology_ttl"][:500])
