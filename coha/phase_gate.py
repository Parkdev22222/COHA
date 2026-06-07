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
        return cls(
            fq_accumulate=False,
            dk_accumulate=False,
            initial_fq_rules=[
                "owl:ObjectProperty must have explicit rdfs:domain and rdfs:range",
                "owl:Class declarations must include rdfs:label annotation",
                "No duplicate class or property URIs within delta-Oi",
                "rdfs:subClassOf must reference an already-declared class",
                "owl:DatatypeProperty range must be an xsd: datatype",
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

    @property
    def violations(self):
        return self.fq_violations + self.dk_violations


class SelfImprovingPhaseGate:
    """
    Self-Improving Phase Gate: validates delta-Oi and inductively updates FQ and DK rule sets.
    """

    def __init__(self, llm_client, config: GateConfig):
        self.llm_client = llm_client
        self.config = config

    def process(self, delta_oi: str, handoff, cq: str) -> GateResult:
        """Run all 4 gate steps for a single CQ's generated delta-Oi."""
        t_start = time.time()

        # Determine active FQ rules
        if self.config.fq_accumulate:
            active_fq_rules = handoff.formal_quality_rules
        elif self.config.initial_fq_rules:
            active_fq_rules = self.config.initial_fq_rules
        else:
            active_fq_rules = []

        # Step 1: Formal Validation
        fq_violations = (
            self._validate_formal(delta_oi, active_fq_rules) if active_fq_rules else []
        )
        new_fq_rules = []
        if self.config.fq_accumulate:
            new_fq_rules = self._extract_fq_rules(delta_oi, bool(fq_violations))

        # Step 2: Domain Validation
        active_dk_rules = handoff.domain_knowledge_rules if self.config.dk_accumulate else []
        dk_violations = (
            self._validate_domain(delta_oi, active_dk_rules) if active_dk_rules else []
        )
        new_dk_rules = []
        if self.config.dk_accumulate:
            new_dk_rules = self._extract_dk_rules(delta_oi, active_dk_rules)

        passed = (len(fq_violations) == 0) and (len(dk_violations) == 0)
        latency_ms = (time.time() - t_start) * 1000

        return GateResult(
            passed=passed,
            fq_violations=fq_violations,
            dk_violations=dk_violations,
            new_fq_rules=new_fq_rules,
            new_dk_rules=new_dk_rules,
            latency_ms=latency_ms,
        )

    def _validate_formal(self, delta_oi: str, fq_rules: List[str]) -> List[str]:
        rules_text = "\n".join(f"- {r}" for r in fq_rules)
        prompt = (
            "You are an OWL ontology quality validator.\n\n"
            f"FORMAL QUALITY RULES:\n{rules_text}\n\n"
            f"OWL AXIOMS TO VALIDATE:\n```turtle\n{delta_oi[:2000]}\n```\n\n"
            "Do these OWL axioms violate any formal quality rule?\n"
            "Answer YES or NO on the first line.\n"
            "If YES, list each violated rule on a separate line."
        )
        try:
            resp = self.llm_client.generate(system="", user=prompt, max_tokens=512)
            lines = [l.strip() for l in resp.strip().split("\n") if l.strip()]
            if lines and lines[0].upper().startswith("YES"):
                return lines[1:] if len(lines) > 1 else ["Formal quality violation detected."]
        except Exception as e:
            logger.warning(f"FQ validation error: {e}")
        return []

    def _extract_fq_rules(self, delta_oi: str, had_violations: bool) -> List[str]:
        outcome = "FAILED (violations detected)" if had_violations else "SUCCEEDED"
        prompt = (
            "You are learning formal quality rules for OWL ontology generation.\n\n"
            f"GENERATION OUTCOME: {outcome}\n\n"
            f"OWL AXIOMS:\n```turtle\n{delta_oi[:2000]}\n```\n\n"
            "Based on this generation, what NEW formal quality rule (if any) should be added "
            "to prevent future issues or enforce good OWL structural practices?\n"
            "Rules must be GENERAL (structural/logical, not domain-specific).\n"
            "Return 0-2 rules, one per line. If none warranted, reply NONE."
        )
        try:
            resp = self.llm_client.generate(system="", user=prompt, max_tokens=256)
            if "NONE" in resp.upper()[:20]:
                return []
            rules = [
                l.strip("- ").strip()
                for l in resp.strip().split("\n")
                if l.strip() and len(l.strip()) > 10
            ]
            return rules[:2]
        except Exception as e:
            logger.warning(f"FQ rule extraction error: {e}")
        return []

    def _validate_domain(self, delta_oi: str, dk_rules: List[str]) -> List[str]:
        rules_text = "\n".join(f"- {r}" for r in dk_rules[-15:])
        prompt = (
            "You are a military domain ontology validator.\n\n"
            f"DOMAIN KNOWLEDGE RULES:\n{rules_text}\n\n"
            f"OWL AXIOMS TO VALIDATE:\n```turtle\n{delta_oi[:2000]}\n```\n\n"
            "Do these OWL axioms violate any domain knowledge rule or introduce incorrect "
            "military-domain relationships?\n"
            "Answer YES or NO on the first line.\n"
            "If YES, list each violation on a separate line."
        )
        try:
            resp = self.llm_client.generate(system="", user=prompt, max_tokens=512)
            lines = [l.strip() for l in resp.strip().split("\n") if l.strip()]
            if lines and lines[0].upper().startswith("YES"):
                return lines[1:] if len(lines) > 1 else ["Domain knowledge violation detected."]
        except Exception as e:
            logger.warning(f"DK validation error: {e}")
        return []

    def _extract_dk_rules(self, delta_oi: str, existing_dk_rules: List[str]) -> List[str]:
        existing_text = (
            "\n".join(f"- {r}" for r in existing_dk_rules[-10:])
            if existing_dk_rules
            else "None yet."
        )
        prompt = (
            "You are inductively learning domain knowledge rules for military ontology generation.\n\n"
            f"EXISTING DOMAIN RULES:\n{existing_text}\n\n"
            f"NEW OWL AXIOMS:\n```turtle\n{delta_oi[:2000]}\n```\n\n"
            "What NEW domain knowledge rules can be induced from these axioms "
            "(not already in existing rules)?\n"
            "Focus on military-domain constraints, required properties, and concept relationships.\n"
            "Example: 'Military Mission requires: assignedUnit, objective, threatLevel'\n"
            "Return 0-2 new rules, one per line. If none, reply NONE."
        )
        try:
            resp = self.llm_client.generate(system="", user=prompt, max_tokens=256)
            if "NONE" in resp.upper()[:20]:
                return []
            rules = [
                l.strip("- ").strip()
                for l in resp.strip().split("\n")
                if l.strip() and len(l.strip()) > 10
            ]
            return rules[:2]
        except Exception as e:
            logger.warning(f"DK rule extraction error: {e}")
        return []
