"""
Phase 1: OntoGPT-inspired Structured Ontology Extractor.

Implements an OntoGPT-style structured extraction pipeline:
  1. Schema definition  — a LinkML-like YAML template with named slots
  2. Single-pass LLM extraction — the model fills the schema from raw text
  3. OWL synthesis      — convert structured extraction to valid Turtle

Reference: Caufield et al. (2024), "OntoGPT: A framework for ontology
           extraction using large language models with structured prompt
           templates"
           https://github.com/monarch-initiative/ontogpt
"""

import re
import logging

from llm_client import UnifiedLLMClient

logger = logging.getLogger(__name__)


class OntoGPTExtractor:
    """
    OntoGPT-inspired structured ontology extractor.

    Uses a predefined extraction schema (analogous to OntoGPT's LinkML
    templates) to guide single-pass LLM extraction of ontology elements.
    The schema defines named slots that the LLM fills in YAML format:
      classes            — domain entity types (OWL Classes)
      subclass_of        — is-a pairs [SubClass, SuperClass]
      object_properties  — triples [DomainClass, propertyName, RangeClass]
      datatype_properties — triples [DomainClass, propertyName, xsd:type]
      disjoint_classes   — mutually exclusive class pairs [A, B]
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

    def extract(self, domain_docs: str, user_stories: str = "") -> dict:
        """
        Run the full OntoGPT pipeline on domain documents.

        Args:
            domain_docs: Domain documentation text.
            user_stories: Optional user stories for additional context.

        Returns:
            dict with keys:
              - ontology_ttl: str
              - extraction: dict  (parsed schema slots)
        """
        print("[OntoGPT] Performing structured schema extraction...")
        extraction = self._structured_extract(domain_docs, user_stories)
        n_cls = len(extraction.get("classes", []))
        n_obj = len(extraction.get("object_properties", []))
        n_dat = len(extraction.get("datatype_properties", []))
        print(f"[OntoGPT] Extracted {n_cls} classes, "
              f"{n_obj} object props, {n_dat} datatype props.")

        print("[OntoGPT] Synthesising OWL from extraction...")
        ontology_ttl = self._extraction_to_owl(extraction)

        return {
            "ontology_ttl": ontology_ttl,
            "extraction": extraction,
        }

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def _structured_extract(self, domain_docs: str, user_stories: str) -> dict:
        """
        Prompt the LLM to fill a predefined YAML schema with ontology
        elements extracted from the domain documentation.
        """
        context_block = (
            f"\nUSER STORIES (for grounding):\n{user_stories[:1000]}"
            if user_stories.strip()
            else ""
        )

        prompt = (
            f"You are an ontology engineer using structured extraction to build an OWL "
            f"ontology for the {self.domain_name} domain.\n\n"
            f"DOMAIN DOCUMENTATION:\n{domain_docs[:4000]}"
            f"{context_block}\n\n"
            "EXTRACTION SCHEMA — fill in every slot based on the documentation above.\n"
            "Return ONLY the filled-in YAML block (including the ```yaml fences).\n\n"
            "```yaml\n"
            "classes:\n"
            "  # Domain entity types in PascalCase (15-25 classes)\n"
            "  - ClassName\n\n"
            "subclass_of:\n"
            "  # is-a hierarchy pairs: [SubClass, SuperClass]\n"
            "  - [SubClass, SuperClass]\n\n"
            "object_properties:\n"
            "  # Relationships: [DomainClass, camelCasePropertyName, RangeClass]\n"
            "  - [DomainClass, propertyName, RangeClass]\n\n"
            "datatype_properties:\n"
            "  # Attributes: [DomainClass, camelCasePropertyName, xsd:type]\n"
            "  # xsd types: xsd:string, xsd:float, xsd:integer, xsd:boolean, xsd:dateTime\n"
            "  - [DomainClass, propertyName, xsd:float]\n\n"
            "disjoint_classes:\n"
            "  # Mutually exclusive class pairs: [ClassA, ClassB]\n"
            "  - [ClassA, ClassB]\n"
            "```"
        )

        response = self.llm_client.generate(system="", user=prompt, max_tokens=2048)
        return self._parse_yaml_extraction(response)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_yaml_extraction(self, text: str) -> dict:
        yaml_text = self._extract_yaml_block(text)

        try:
            import yaml
            data = yaml.safe_load(yaml_text)
            if isinstance(data, dict):
                return self._normalise(data)
        except Exception:
            pass

        return self._fallback_parse(yaml_text)

    @staticmethod
    def _extract_yaml_block(text: str) -> str:
        if "```yaml" in text:
            start = text.find("```yaml") + len("```yaml")
            end = text.find("```", start)
            return text[start:end].strip() if end != -1 else text[start:].strip()
        if "```" in text:
            start = text.find("```") + 3
            newline = text.find("\n", start)
            if newline != -1:
                start = newline + 1
            end = text.find("```", start)
            return text[start:end].strip() if end != -1 else text[start:].strip()
        return text.strip()

    @staticmethod
    def _normalise(data: dict) -> dict:
        def to_list(v):
            return v if isinstance(v, list) else []

        return {
            "classes": to_list(data.get("classes")),
            "subclass_of": to_list(data.get("subclass_of")),
            "object_properties": to_list(data.get("object_properties")),
            "datatype_properties": to_list(data.get("datatype_properties")),
            "disjoint_classes": to_list(data.get("disjoint_classes")),
        }

    def _fallback_parse(self, text: str) -> dict:
        result = {
            "classes": [], "subclass_of": [],
            "object_properties": [], "datatype_properties": [],
            "disjoint_classes": [],
        }
        current = None
        for line in text.split("\n"):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s.startswith("classes:"):
                current = "classes"
            elif s.startswith("subclass_of:"):
                current = "subclass_of"
            elif s.startswith("object_properties:"):
                current = "object_properties"
            elif s.startswith("datatype_properties:"):
                current = "datatype_properties"
            elif s.startswith("disjoint_classes:"):
                current = "disjoint_classes"
            elif s.startswith("- ") and current:
                item = s[2:].strip()
                if current == "classes":
                    result["classes"].append(item.strip("'\""))
                elif item.startswith("[") and item.endswith("]"):
                    parts = [p.strip().strip("'\"") for p in item[1:-1].split(",")]
                    if len(parts) >= 2:
                        result[current].append(parts)
        return result

    # ------------------------------------------------------------------
    # OWL synthesis
    # ------------------------------------------------------------------

    def _extraction_to_owl(self, extraction: dict) -> str:
        parts = [
            self._base_prefix,
            self._fmt_block(
                f"<{self._base_uri}>",
                [
                    ("a", "owl:Ontology"),
                    ("rdfs:label", f'"{self.domain_name} Ontology"'),
                    ("rdfs:comment",
                     '"Ontology generated via OntoGPT-style extraction for COHA."'),
                ],
            ),
            "",
        ]

        defined_classes: set = set()

        for cls in extraction.get("classes", []):
            name = self._class_name(cls)
            if name and name not in defined_classes:
                parts.append(
                    self._fmt_block(
                        f":{name}",
                        [("a", "owl:Class"), ("rdfs:label", f'"{name}"')],
                    )
                )
                parts.append("")
                defined_classes.add(name)

        for entry in extraction.get("subclass_of", []):
            if isinstance(entry, list) and len(entry) >= 2:
                sub = self._class_name(entry[0])
                sup = self._class_name(entry[1])
                if sub and sup and sub in defined_classes and sup in defined_classes:
                    parts.append(f":{sub} rdfs:subClassOf :{sup} .")
        if extraction.get("subclass_of"):
            parts.append("")

        defined_props: set = set()

        for entry in extraction.get("object_properties", []):
            if not (isinstance(entry, list) and len(entry) >= 3):
                continue
            dom = self._class_name(entry[0])
            prop = self._prop_name(entry[1])
            rng = self._class_name(entry[2])
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

        for entry in extraction.get("datatype_properties", []):
            if not (isinstance(entry, list) and len(entry) >= 3):
                continue
            dom = self._class_name(entry[0])
            prop = self._prop_name(entry[1])
            dtype = str(entry[2])
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

        for entry in extraction.get("disjoint_classes", []):
            if isinstance(entry, list) and len(entry) >= 2:
                a = self._class_name(entry[0])
                b = self._class_name(entry[1])
                if a and b and a in defined_classes and b in defined_classes:
                    parts.append(f":{a} owl:disjointWith :{b} .")
        if extraction.get("disjoint_classes"):
            parts.append("")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Turtle formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt_block(subject: str, po_pairs: list) -> str:
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
    extractor = OntoGPTExtractor(client, "Smart Building Management")
    docs = (
        "A smart building contains HVAC zones, temperature sensors, CO2 sensors, "
        "energy meters, and occupancy zones. Actuators control HVAC systems."
    )
    result = extractor.extract(docs)
    print(f"Classes: {result['extraction']['classes']}")
    print(f"Object props: {result['extraction']['object_properties']}")
    print("\nOntology (first 600 chars):")
    print(result["ontology_ttl"][:600])
