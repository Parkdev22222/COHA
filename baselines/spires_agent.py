"""
Baseline: SPIRES (Structured Prompt Interrogation and Recursive Extraction of Semantics).

Recursive multi-pass extraction: first identifies top-level classes, then
recursively extracts properties and axioms for each class.

Unlike COHA, SPIRES is document-driven (not CQ-driven) and has no
self-improving gate — each extraction pass is independent.

Reference: Caufield et al. "Structured prompt interrogation and recursive
extraction of semantics (SPIRES)." Bioinformatics, 2024.
"""
import time
import logging
from coha.owl_utils import merge_ontologies, check_consistency, extract_class_names

logger = logging.getLogger(__name__)

BASE_PREFIXES = """@prefix : <http://coha.org/military#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

<http://coha.org/military> a owl:Ontology ;
    rdfs:label "Military Tactical Ontology (SPIRES)" .

"""


class SPIRESAgent:
    """
    SPIRES-style baseline: recursive structured extraction.

    Phase 1 — Class Discovery: extract all top-level domain classes.
    Phase 2 — Recursive Expansion: for each class, extract properties,
               sub-classes, and axioms.
    Phase 3 — Merge: combine all extracted axioms into one ontology.
    """

    def __init__(self, llm_client, max_classes_to_expand: int = 15):
        self.llm_client = llm_client
        self.max_classes_to_expand = max_classes_to_expand

    def run(self, cqs: list, user_story: str, domain_docs: str = "") -> dict:
        """
        Recursive SPIRES extraction.

        Args:
            cqs: Competency questions (used to scope class discovery).
            user_story: Domain user story.
            domain_docs: Raw domain documentation text.

        Returns:
            harness-compatible result dict.
        """
        total_times = []
        gate_times = []

        doc_snippet = domain_docs[:3000] if domain_docs else user_story[:2000]
        cq_texts = [cq["question"] if isinstance(cq, dict) else cq for cq in cqs[:10]]
        cq_sample = "\n".join(f"- {q}" for q in cq_texts)

        # ── Phase 1: Class Discovery ─────────────────────────────────────
        print("  [SPIRES] Phase 1: Discovering top-level classes...")
        t0 = time.time()
        classes = self._discover_classes(doc_snippet, cq_sample, user_story)
        total_times.append((time.time() - t0) * 1000)
        print(f"  [SPIRES] Discovered {len(classes)} classes: {classes[:8]}")

        # ── Phase 2: Recursive Expansion ─────────────────────────────────
        accumulated_ttl = BASE_PREFIXES
        classes_to_expand = classes[:self.max_classes_to_expand]

        for idx, cls in enumerate(classes_to_expand):
            print(f"  [SPIRES] Phase 2 [{idx+1}/{len(classes_to_expand)}]: Expanding {cls}...")
            t0 = time.time()
            delta = self._expand_class(cls, classes, doc_snippet, user_story)
            total_times.append((time.time() - t0) * 1000)
            if delta:
                accumulated_ttl = merge_ontologies(accumulated_ttl, delta)

        # ── Phase 3: Cross-class Axioms ───────────────────────────────────
        print("  [SPIRES] Phase 3: Extracting cross-class axioms...")
        t0 = time.time()
        cross_axioms = self._extract_cross_axioms(
            extract_class_names(accumulated_ttl), doc_snippet, user_story
        )
        total_times.append((time.time() - t0) * 1000)
        if cross_axioms:
            accumulated_ttl = merge_ontologies(accumulated_ttl, cross_axioms)

        is_consistent = check_consistency(accumulated_ttl)

        return {
            "ontology_ttl": accumulated_ttl,
            "gate_times": gate_times,
            "total_times": total_times,
            "n_retries_total": 0,
            "final_fq_rules": [],
            "final_dk_rules": [],
            "rar_data": [],
            "qic_data": [],
            "is_consistent": is_consistent,
        }

    def _discover_classes(self, doc_snippet: str, cq_sample: str, user_story: str) -> list:
        """Phase 1: identify top-level ontology classes."""
        prompt = (
            "You are an ontology engineer performing structured concept extraction.\n\n"
            f"USER STORY:\n{user_story}\n\n"
            f"DOMAIN TEXT:\n{doc_snippet}\n\n"
            f"SAMPLE COMPETENCY QUESTIONS:\n{cq_sample}\n\n"
            "List ALL top-level ontology classes needed for this military domain.\n"
            "Rules:\n"
            "- One CamelCase class name per line\n"
            "- 10-20 classes total\n"
            "- No explanations, no prefixes\n\n"
            "Classes:"
        )
        try:
            resp = self.llm_client.generate(system="", user=prompt, max_tokens=512)
            classes = []
            for line in resp.strip().split("\n"):
                name = line.strip().strip("-• ").strip()
                if name and name[0].isupper() and " " not in name and len(name) > 2:
                    classes.append(name)
            return list(dict.fromkeys(classes))[:20]
        except Exception as e:
            logger.warning(f"SPIRES class discovery failed: {e}")
            return []

    def _expand_class(self, cls: str, all_classes: list, doc_snippet: str, user_story: str) -> str:
        """Phase 2: recursively expand a single class into OWL axioms."""
        related = [c for c in all_classes if c != cls][:10]
        related_str = ", ".join(related)
        prompt = (
            f"You are extracting OWL axioms for the class :{cls} in a military ontology.\n\n"
            f"Other known classes: {related_str}\n\n"
            f"DOMAIN TEXT:\n{doc_snippet[:1500]}\n\n"
            f"USER STORY:\n{user_story[:500]}\n\n"
            f"Generate OWL 2 Turtle axioms for :{cls}:\n"
            "1. Declare :{cls} as owl:Class with rdfs:label\n"
            "2. Add rdfs:subClassOf if appropriate\n"
            "3. Add owl:ObjectProperty/owl:DatatypeProperty for its attributes\n"
            "   with rdfs:domain, rdfs:range, rdfs:label\n"
            "4. Do NOT re-declare other classes — reference them by name only\n"
            "5. Use prefix :  for <http://coha.org/military#>\n"
            "Return ONLY valid Turtle, no markdown:\n"
        )
        try:
            raw = self.llm_client.generate(system="", user=prompt, max_tokens=1024)
            return self._clean_turtle(raw)
        except Exception as e:
            logger.warning(f"SPIRES expand {cls} failed: {e}")
            return ""

    def _extract_cross_axioms(self, classes: list, doc_snippet: str, user_story: str) -> str:
        """Phase 3: extract cross-class relationships (ObjectProperties between classes)."""
        if len(classes) < 2:
            return ""
        cls_list = ", ".join(f":{c}" for c in classes[:15])
        prompt = (
            "Given these ontology classes in a military domain:\n"
            f"{cls_list}\n\n"
            f"DOMAIN TEXT:\n{doc_snippet[:1500]}\n\n"
            "Generate OWL 2 Turtle axioms for CROSS-CLASS relationships only:\n"
            "- owl:ObjectProperty declarations linking the above classes\n"
            "- rdfs:domain and rdfs:range referencing the declared classes\n"
            "- rdfs:subClassOf axioms between classes where applicable\n"
            "- owl:disjointWith where classes are mutually exclusive\n"
            "Do NOT re-declare the classes themselves.\n"
            "Use prefix :  for <http://coha.org/military#>\n"
            "Return ONLY valid Turtle:\n"
        )
        try:
            raw = self.llm_client.generate(system="", user=prompt, max_tokens=1024)
            return self._clean_turtle(raw)
        except Exception as e:
            logger.warning(f"SPIRES cross-axiom extraction failed: {e}")
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
