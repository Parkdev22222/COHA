"""
Self-Improving Phase Gate.

Operates at the boundary between each CQ processing step.
Maintains two inductively updated rule sets:
  - Formal Quality Rules (FQ): OWL structural/logical patterns
  - Domain Knowledge Rules (DK): domain-specific concepts and constraints

4-step operation per CQ:
  Step 1: Formal Validation (FQ Rules) -> request regen if violated
  Step 2: Domain Validation (DK Rules) -> discover new domain concepts
  Step 3: Rule Update (FQ_{k+1} = FQ_k union new_fq; DK_{k+1} = DK_k union new_dk)
  Step 4: Handoff is updated by the caller (harness.py)
"""
import time
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

# Deterministic mapping from FQ check ID → actionable OWL generation guideline.
# Used to build the accumulated FQ guide injected into future CQ prompts.
FQ_VIOLATION_GUIDANCE: dict = {
    "FQ-OBJPROP-DOMRANGE": (
        "Always declare both rdfs:domain and rdfs:range for every owl:ObjectProperty"
    ),
    "FQ-DATPROP-XSD-RANGE": (
        "Use only xsd: datatypes (xsd:string, xsd:integer, xsd:boolean, xsd:float) "
        "for owl:DatatypeProperty range"
    ),
    "FQ-CLASS-LABEL": (
        "Every owl:Class declaration must include rdfs:label with a human-readable name"
    ),
    "FQ-PROP-LABEL": (
        "Every owl:ObjectProperty and owl:DatatypeProperty must include rdfs:label"
    ),
    "FQ-SUBCLASS-RESOURCE": (
        "rdfs:subClassOf target must be a class URI — never a string literal"
    ),
    "FQ-NO-PROP-TYPE-CONFLICT": (
        "Declare each property as owl:ObjectProperty OR owl:DatatypeProperty — never both"
    ),
    "FQ-NO-CLASS-PROP-CONFLICT": (
        "An entity must not be declared as both owl:Class and a property type"
    ),
    "FQ-PARSE": (
        "Output must be valid Turtle syntax — no markdown fences, no prose, only RDF triples"
    ),
}


@dataclass
class GateConfig:
    fq_accumulate: bool = True      # dynamically accumulate FQ rules
    dk_accumulate: bool = True      # dynamically accumulate DK rules
    initial_fq_rules: List[str] = field(default_factory=list)  # for static gate
    max_retries: int = 3

    @classmethod
    def coha_full(cls):
        return cls(fq_accumulate=True, dk_accumulate=True)

    @classmethod
    def coha_no_dk(cls):
        return cls(fq_accumulate=True, dk_accumulate=False)

    @classmethod
    def coha_no_fq(cls):
        return cls(fq_accumulate=False, dk_accumulate=True)

    @classmethod
    def static_gate(cls):
        # Fixed FQ catalog active from the start (no inductive growth).
        # Rule strings are "<check_id>: <desc>" so they map to deterministic checks.
        return cls(
            fq_accumulate=False,
            dk_accumulate=False,
            initial_fq_rules=[
                "FQ-OBJPROP-DOMRANGE: owl:ObjectProperty must have explicit rdfs:domain and rdfs:range",
                "FQ-CLASS-LABEL: owl:Class declarations must include rdfs:label",
                "FQ-PROP-LABEL: Object/Datatype properties must include rdfs:label",
                "FQ-DATPROP-XSD-RANGE: owl:DatatypeProperty range must be an xsd: datatype",
                "FQ-SUBCLASS-RESOURCE: rdfs:subClassOf target must be a class resource, not a literal",
                "FQ-NO-PROP-TYPE-CONFLICT: A property must not be both ObjectProperty and DatatypeProperty",
                "FQ-NO-CLASS-PROP-CONFLICT: An entity must not be declared both a Class and a property",
            ],
        )

    @classmethod
    def no_gate(cls):
        return cls(fq_accumulate=False, dk_accumulate=False)


@dataclass
class GateResult:
    passed: bool
    fq_violations: List[str]
    dk_violations: List[str]
    new_fq_rules: List[str]
    new_dk_rules: List[str]
    latency_ms: float
    new_fq_guidance: List[str] = field(default_factory=list)
    new_dk_patterns: List[dict] = field(default_factory=list)

    @property
    def violations(self):
        return self.fq_violations + self.dk_violations


class SelfImprovingPhaseGate:
    """
    Self-Improving Phase Gate: validates delta-Oi and inductively updates FQ and DK rule sets.
    """

    def __init__(self, llm_client, config: GateConfig, domain_docs: str = None):
        self.llm_client = llm_client
        self.config = config
        # Build a doctrine retriever for grounding DK rules (if docs provided)
        self.retriever = None
        if domain_docs:
            try:
                from domain.doc_retriever import DomainDocRetriever
                self.retriever = DomainDocRetriever(domain_docs)
            except Exception as e:
                logger.warning(f"Could not build doc retriever; DK grounding disabled: {e}")

    def process(self, delta_oi: str, handoff, cq: str, cq_index: int = 0) -> GateResult:
        """Run all 4 gate steps for a single CQ's generated delta-Oi."""
        t_start = time.time()

        # Determine active FQ rules
        if self.config.fq_accumulate:
            active_fq_rules = handoff.formal_quality_rules
        elif self.config.initial_fq_rules:
            active_fq_rules = self.config.initial_fq_rules
        else:
            active_fq_rules = []

        # Step 1: Formal Validation (deterministic rdflib checks)
        fq_violations, new_fq_rules, fired_ids = self._validate_formal_deterministic(
            delta_oi, active_fq_rules
        )
        # Build actionable guidance strings from fired check IDs (deduped)
        new_fq_guidance = list(dict.fromkeys(
            FQ_VIOLATION_GUIDANCE[cid] for cid in fired_ids if cid in FQ_VIOLATION_GUIDANCE
        ))

        # Step 2: Domain Validation
        active_dk_rules = handoff.domain_knowledge_rules if self.config.dk_accumulate else []
        dk_violations = (
            self._validate_domain(delta_oi, active_dk_rules) if active_dk_rules else []
        )
        new_dk_rules, new_dk_patterns = [], []
        if self.config.dk_accumulate:
            new_dk_rules, new_dk_patterns = self._extract_dk_rules(
                delta_oi, active_dk_rules, cq=cq, cq_index=cq_index
            )

        # FQ violations are hard failures (structural correctness).
        # DK violations are advisory only — logged but do not block acceptance.
        passed = (len(fq_violations) == 0)
        latency_ms = (time.time() - t_start) * 1000

        return GateResult(
            passed=passed,
            fq_violations=fq_violations,
            dk_violations=dk_violations,
            new_fq_rules=new_fq_rules,
            new_dk_rules=new_dk_rules,
            latency_ms=latency_ms,
            new_fq_guidance=new_fq_guidance,
            new_dk_patterns=new_dk_patterns,
        )

    @staticmethod
    def _fq_rule_to_check_id(rule: str) -> str:
        """Map a stored FQ rule string back to its check id (id is the prefix)."""
        return rule.split(":", 1)[0].strip() if ":" in rule else rule.strip()

    def _validate_formal_deterministic(self, delta_oi: str, active_fq_rules: List[str]):
        """Deterministic FQ validation via rdflib (paper §3.2.2 Step 1).

        Returns (fq_violations, new_fq_rules, fired_check_ids).

        Semantics:
          - static / no-accumulate mode (initial_fq_rules set, fq_accumulate=False):
                run the fixed catalog; ALL violations are hard failures.
          - accumulate mode (fq_accumulate=True):
                ALL 7 checks run from CQ 1 — every violation is a hard failure.
                Concrete violation messages (e.g. "ObjectProperty :X is missing rdfs:domain")
                are returned in fq_violations and fed back to the LLM on retry via
                _violation_hint(). First-time violations are ALSO added to new_fq_rules
                (for RAR curve tracking), but they do not get a "free pass" — the gate
                rejects immediately so the LLM can self-correct with precise feedback.
          - disabled (no active rules, no accumulate): no FQ checks run.
        """
        from coha.fq_checker import run_checks, ALL_CHECK_IDS, FQ_CHECKS, describe

        # Static mode: fixed catalog, every violation blocks.
        if not self.config.fq_accumulate:
            if not active_fq_rules:
                return [], [], []
            active_ids = [self._fq_rule_to_check_id(r) for r in active_fq_rules]
            active_ids = [c for c in active_ids if c in FQ_CHECKS] or ALL_CHECK_IDS
            fired = run_checks(delta_oi, active_ids)
            violations = [m for msgs in fired.values() for m in msgs]
            return violations, [], list(fired.keys())

        # Accumulate mode: run the full catalog. ALL violations block immediately.
        # Track first-time check firings for RAR curve (added to new_fq_rules).
        active_ids = set(self._fq_rule_to_check_id(r) for r in active_fq_rules)
        fired = run_checks(delta_oi, ALL_CHECK_IDS)

        hard_violations = []
        newly_learned = []
        for cid, msgs in fired.items():
            hard_violations.extend(msgs)  # every violation blocks immediately
            if cid not in active_ids:
                newly_learned.append(describe(cid))  # first observation → RAR curve
        return hard_violations, newly_learned, list(fired.keys())

    def _validate_domain(self, delta_oi: str, dk_rules: List[str]) -> List[str]:
        # Only enforce [STRUCT] rules per CQ.
        # [COMPL] rules are eventual completeness goals — not required in a single delta-Oi.
        structural_rules = [r for r in dk_rules if r.startswith("[STRUCT]")]
        if not structural_rules:
            return []
        rules_text = "\n".join(f"- {r}" for r in structural_rules[-15:])
        prompt = (
            "You are a military domain ontology validator.\n\n"
            "STRUCTURAL DOMAIN RULES (must hold within this delta):\n"
            f"{rules_text}\n\n"
            f"OWL AXIOMS TO VALIDATE:\n```turtle\n{delta_oi[:2000]}\n```\n\n"
            "Do these OWL axioms DIRECTLY violate any structural rule above?\n"
            "Only flag violations that are clearly present in this delta — do NOT flag\n"
            "missing properties that could be added in later competency questions.\n"
            "Answer YES or NO on the first line.\n"
            "If YES, list each violated rule on a separate line."
        )
        try:
            resp = self.llm_client.generate(system="", user=prompt, max_tokens=512)
            lines = [l.strip() for l in resp.strip().split("\n") if l.strip()]
            if lines and lines[0].upper().startswith("YES"):
                return lines[1:] if len(lines) > 1 else ["Structural DK violation detected."]
        except Exception as e:
            logger.warning(f"DK validation error: {e}")
        return []

    def _extract_dk_rules(
        self, delta_oi: str, existing_dk_rules: List[str],
        cq: str = "", cq_index: int = 0,
    ):
        """Inductively extract DK rules, each GROUNDED in published doctrine.

        Returns (new_rules: List[str], new_patterns: List[dict]).

        Pipeline (paper §3.2.2):
          1. LLM induces 0-2 candidate rules from delta-Oi, classified [STRUCT]/[COMPL]
          2. Each candidate is grounded against the doctrine corpus via retrieval +
             LLM verification. Only rules supported by a doctrine passage are kept,
             with a source citation appended as "(src: <section>)".
          3. Grounded rules produce a compressed OWL pattern entry stored in
             dk_success_patterns for the self-improving guide.
        """
        existing_text = (
            "\n".join(f"- {r}" for r in existing_dk_rules[-10:])
            if existing_dk_rules
            else "None yet."
        )
        prompt = (
            "You are inductively learning domain knowledge rules for military ontology generation.\n\n"
            f"EXISTING DOMAIN RULES:\n{existing_text}\n\n"
            f"NEW OWL AXIOMS:\n```turtle\n{delta_oi[:2000]}\n```\n\n"
            "Induce 0-2 NEW domain knowledge rules from these axioms (not already listed above).\n\n"
            "Classify EACH rule with a prefix:\n"
            "  [STRUCT] — a structural constraint that must hold within any single delta-Oi\n"
            "             (e.g. wrong relationship direction, prohibited pattern)\n"
            "             Example: [STRUCT] :isPartOf must go from smaller to larger unit, not vice versa\n"
            "  [COMPL]  — an eventual completeness goal for the full ontology\n"
            "             (e.g. a class should eventually have certain properties)\n"
            "             Example: [COMPL] :Mission should eventually have: :assignedUnit, :objective, :threatLevel\n\n"
            "Return each rule on its own line starting with [STRUCT] or [COMPL].\n"
            "If no new rules are warranted, reply NONE."
        )
        try:
            resp = self.llm_client.generate(system="", user=prompt, max_tokens=256)
            if "NONE" in resp.upper()[:20]:
                return [], []
            candidates = []
            for line in resp.strip().split("\n"):
                line = line.strip().strip("- ")
                if len(line) > 10 and (line.startswith("[STRUCT]") or line.startswith("[COMPL]")):
                    candidates.append(line)
            candidates = candidates[:2]
        except Exception as e:
            logger.warning(f"DK rule extraction error: {e}")
            return [], []

        # Ground each candidate in doctrine. If no retriever, fall back to ungrounded
        # acceptance (so ablations without docs still run), with no patterns.
        if not self.retriever:
            return candidates, []

        grounded_rules = []
        grounded_patterns = []
        owl_pattern = self._compress_owl_pattern(delta_oi)
        for rule in candidates:
            citation, similarity = self._ground_rule(rule)
            if citation:
                grounded_rules.append(f"{rule} (src: {citation})")
                if owl_pattern:
                    grounded_patterns.append({
                        "cq_summary": cq[:80],
                        "cq_index": cq_index,
                        "owl_pattern": owl_pattern,
                        "citation": citation,
                        "similarity": similarity,
                        "rule": rule,
                    })
            else:
                logger.info(f"DK rule rejected (no doctrine support): {rule}")
        return grounded_rules, grounded_patterns

    def _ground_rule(self, rule: str):
        """Return (citation, similarity) if doctrine supports the rule, else ('', 0.0).

        Two-step: (1) retrieve the most relevant doctrine passage,
                  (2) LLM verifies the passage actually supports the rule.
        """
        evidence = self.retriever.retrieve_evidence(rule, top_k=2)
        if not evidence:
            return "", 0.0
        best_similarity = evidence[0][1]
        passages = "\n\n".join(
            f"[{self.retriever.section_title(c)}]\n{c[:700]}" for c, _ in evidence
        )
        prompt = (
            "You are verifying whether a proposed military ontology rule is supported by "
            "published US Army doctrine.\n\n"
            f"PROPOSED RULE:\n{rule}\n\n"
            f"DOCTRINE PASSAGES:\n{passages}\n\n"
            "Is the proposed rule consistent with and supported by these doctrine passages?\n"
            "Answer SUPPORTED or UNSUPPORTED on the first line.\n"
            "If SUPPORTED, on the second line give the single most relevant section title."
        )
        try:
            resp = self.llm_client.generate(system="", user=prompt, max_tokens=128)
            lines = [l.strip() for l in resp.strip().split("\n") if l.strip()]
            if lines and lines[0].upper().startswith("SUPPORTED"):
                citation = (
                    lines[1].strip().strip("[]").strip()[:60]
                    if len(lines) > 1
                    else self.retriever.section_title(evidence[0][0])
                )
                return citation, best_similarity
        except Exception as e:
            logger.warning(f"DK grounding verification error: {e}")
        return "", 0.0

    @staticmethod
    def _compress_owl_pattern(delta_oi: str, max_items: int = 4) -> str:
        """Extract key OWL triples as a compact string (no LLM needed).

        Returns e.g. ":hasCommander(ObjectProperty, :Unit→:Commander); :Mission(Class)"
        """
        try:
            from coha.fq_checker import _parse, OWL, RDFS
            import rdflib

            g = _parse(delta_oi)

            def local(uri):
                s = str(uri)
                for sep in ("#", "/"):
                    if sep in s:
                        return s.rsplit(sep, 1)[-1]
                return s

            TYPE = rdflib.RDF.type
            OBJ = rdflib.URIRef(OWL + "ObjectProperty")
            DTP = rdflib.URIRef(OWL + "DatatypeProperty")
            CLS = rdflib.URIRef(OWL + "Class")
            DOM = rdflib.URIRef(RDFS + "domain")
            RAN = rdflib.URIRef(RDFS + "range")

            items = []
            for p in sorted(set(g.subjects(TYPE, OBJ)), key=str):
                d = next((local(o) for o in g.objects(p, DOM)), "?")
                r = next((local(o) for o in g.objects(p, RAN)), "?")
                items.append(f":{local(p)}(ObjectProperty,:{d}→:{r})")
                if len(items) >= max_items:
                    break
            for p in sorted(set(g.subjects(TYPE, DTP)), key=str):
                r = next((local(o) for o in g.objects(p, RAN)), "xsd:?")
                items.append(f":{local(p)}(DatatypeProperty,→{r})")
                if len(items) >= max_items:
                    break
            if len(items) < max_items:
                for c in sorted(set(g.subjects(TYPE, CLS)), key=str):
                    if not isinstance(c, rdflib.BNode):
                        items.append(f":{local(c)}(Class)")
                        if len(items) >= max_items:
                            break
            return "; ".join(items)
        except Exception:
            return ""

    def check_completeness(self, final_ontology_ttl: str, dk_rules: List[str]) -> dict:
        """Check [COMPL] rules against the final merged ontology (called once at experiment end).

        Returns:
            satisfied: list of rules that pass
            violated: list of rules that fail
            score: fraction satisfied
        """
        compl_rules = [r for r in dk_rules if r.startswith("[COMPL]")]
        if not compl_rules:
            return {"satisfied": [], "violated": [], "score": 1.0}

        rules_text = "\n".join(f"- {r}" for r in compl_rules)
        prompt = (
            "You are evaluating whether a completed military ontology satisfies its design goals.\n\n"
            f"COMPLETENESS GOALS:\n{rules_text}\n\n"
            f"FINAL ONTOLOGY (excerpt):\n```turtle\n{final_ontology_ttl[:4000]}\n```\n\n"
            "For each completeness goal, answer SATISFIED or VIOLATED.\n"
            "Format: one line per rule → '<rule text> → SATISFIED' or '<rule text> → VIOLATED'"
        )
        try:
            resp = self.llm_client.generate(system="", user=prompt, max_tokens=512)
            satisfied, violated = [], []
            for line in resp.strip().split("\n"):
                if "SATISFIED" in line.upper():
                    satisfied.append(line.split("→")[0].strip())
                elif "VIOLATED" in line.upper():
                    violated.append(line.split("→")[0].strip())
            total = len(satisfied) + len(violated)
            score = round(len(satisfied) / total, 4) if total else 1.0
            return {"satisfied": satisfied, "violated": violated, "score": score}
        except Exception as e:
            logger.warning(f"Completeness check failed: {e}")
            return {"satisfied": [], "violated": [], "score": 0.0}

    def resolve_dk_conflicts(
        self, existing_rules: List[str], new_rules: List[str]
    ) -> List[str]:
        """
        Priority resolution for conflicting DK Rules (paper §3.2.2 Step 2).

        When new rules contradict existing ones (e.g., different cardinality
        constraints for the same concept), the LLM adjudicates which rule
        takes precedence. Non-conflicting rules are always accepted.

        Returns the merged rule set with conflicts resolved.
        """
        if not existing_rules or not new_rules:
            return list(dict.fromkeys(existing_rules + new_rules))

        # Quick check: if no obvious keyword overlap, no conflict possible
        new_keywords = set(
            w.lower() for r in new_rules for w in r.split()
            if len(w) > 4
        )
        existing_keywords = set(
            w.lower() for r in existing_rules for w in r.split()
            if len(w) > 4
        )
        if not (new_keywords & existing_keywords):
            return list(dict.fromkeys(existing_rules + new_rules))

        existing_text = "\n".join(f"- {r}" for r in existing_rules[-15:])
        new_text = "\n".join(f"- {r}" for r in new_rules)
        prompt = (
            "You are resolving conflicts between domain knowledge rules for military ontology.\n\n"
            f"EXISTING RULES:\n{existing_text}\n\n"
            f"NEW RULES (to integrate):\n{new_text}\n\n"
            "For each new rule:\n"
            "- If it CONTRADICTS an existing rule, keep only the more specific/correct one\n"
            "- If it DUPLICATES an existing rule, discard it\n"
            "- If it is COMPATIBLE, accept it\n\n"
            "Return the final merged rule list, one rule per line. "
            "Include all accepted existing rules + accepted new rules."
        )
        try:
            resp = self.llm_client.generate(system="", user=prompt, max_tokens=512)
            merged = [
                l.strip("- ").strip()
                for l in resp.strip().split("\n")
                if l.strip() and len(l.strip()) > 10
            ]
            return list(dict.fromkeys(merged)) if merged else list(dict.fromkeys(existing_rules + new_rules))
        except Exception as e:
            logger.warning(f"DK conflict resolution failed: {e}; falling back to union.")
            return list(dict.fromkeys(existing_rules + new_rules))
