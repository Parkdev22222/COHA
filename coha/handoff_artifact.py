"""
Handoff Artifact: structured knowledge transfer across context resets.

Schema from COHA paper (§3.3):
  iteration              : int
  completed_cqs          : list[str]
  accumulated_ontology   : AccumulatedOntology (classes, properties, axioms, consistency, ttl)
  formal_quality_rules   : list[str]
  domain_knowledge_rules : list[str]
  next_cq                : str
  coverage_gaps          : list[str]
  fq_learned_patterns    : list[str]   — guidance strings learned from past FQ gate failures
  dk_success_patterns    : list[dict]  — doctrine-grounded OWL patterns from past CQ successes
  dk_failure_patterns    : list[dict]  — doctrine-REJECTED candidates (mistakes to avoid)
"""
import json
from dataclasses import dataclass, field
from typing import List


@dataclass
class AccumulatedOntology:
    classes: List[str] = field(default_factory=list)
    properties: List[str] = field(default_factory=list)
    axioms: List[str] = field(default_factory=list)
    consistency: str = "UNKNOWN"  # "VALID" | "INVALID" | "UNKNOWN"
    ttl: str = ""  # full Turtle text

    def to_summary(self, max_classes=20, max_props=20) -> str:
        """Compact text summary for injection into LLM prompt."""
        lines = []
        if self.classes:
            lines.append(f"Classes ({len(self.classes)}): {', '.join(self.classes[:max_classes])}")
        if self.properties:
            lines.append(f"Properties ({len(self.properties)}): {', '.join(self.properties[:max_props])}")
        lines.append(f"Consistency: {self.consistency}")
        return "\n".join(lines)


@dataclass
class HandoffArtifact:
    iteration: int = 0
    completed_cqs: List[str] = field(default_factory=list)
    accumulated_ontology: AccumulatedOntology = field(default_factory=AccumulatedOntology)
    formal_quality_rules: List[str] = field(default_factory=list)
    domain_knowledge_rules: List[str] = field(default_factory=list)
    next_cq: str = ""
    coverage_gaps: List[str] = field(default_factory=list)
    fq_learned_patterns: List[str] = field(default_factory=list)
    dk_success_patterns: List[dict] = field(default_factory=list)
    dk_failure_patterns: List[dict] = field(default_factory=list)

    @classmethod
    def initial(cls) -> "HandoffArtifact":
        return cls()

    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "completed_cqs": self.completed_cqs,
            "accumulated_ontology": {
                "classes": self.accumulated_ontology.classes,
                "properties": self.accumulated_ontology.properties,
                "axioms": self.accumulated_ontology.axioms,
                "consistency": self.accumulated_ontology.consistency,
            },
            "formal_quality_rules": self.formal_quality_rules,
            "domain_knowledge_rules": self.domain_knowledge_rules,
            "next_cq": self.next_cq,
            "coverage_gaps": self.coverage_gaps,
            "fq_learned_patterns": self.fq_learned_patterns,
            "dk_success_patterns": self.dk_success_patterns,
            "dk_failure_patterns": self.dk_failure_patterns,
        }

    def to_prompt_text(self) -> str:
        """Compact representation for injection into LLM system prompt."""
        parts = []
        parts.append(f"=== Handoff Artifact (iteration {self.iteration}) ===")
        if self.accumulated_ontology.classes or self.accumulated_ontology.properties:
            parts.append("Current Ontology Summary:")
            parts.append(self.accumulated_ontology.to_summary())
        if self.formal_quality_rules:
            parts.append(f"\n=== Formal Quality Rules ({len(self.formal_quality_rules)}) ===")
            for r in self.formal_quality_rules:
                parts.append(f"- {r}")
        if self.domain_knowledge_rules:
            structural = [r for r in self.domain_knowledge_rules if r.startswith("[STRUCT]")]
            completeness = [r for r in self.domain_knowledge_rules if r.startswith("[COMPL]")]
            legacy = [r for r in self.domain_knowledge_rules
                      if not r.startswith("[STRUCT]") and not r.startswith("[COMPL]")]
            if structural:
                parts.append(f"\n=== DK Structural Rules ({len(structural)}) — enforce in each delta ===")
                for r in structural:
                    parts.append(f"- {r}")
            if completeness:
                parts.append(f"\n=== DK Completeness Goals ({len(completeness)}) — eventual targets, not per-CQ ===")
                for r in completeness:
                    parts.append(f"- {r}")
            if legacy:
                parts.append(f"\n=== Domain Knowledge Rules ({len(legacy)}) ===")
                for r in legacy:
                    parts.append(f"- {r}")
        if self.coverage_gaps:
            parts.append(f"\nCoverage Gaps: {', '.join(self.coverage_gaps[:5])}")
        if self.fq_learned_patterns:
            parts.append(f"\n=== OWL Generation Guidelines ({len(self.fq_learned_patterns)}) — learned from past FQ failures ===")
            for p in self.fq_learned_patterns:
                parts.append(f"- {p}")
        if self.dk_success_patterns:
            parts.append(f"\n=== Doctrine-Grounded Reference Patterns ({len(self.dk_success_patterns)}) — FOLLOW these ===")
            for p in self.dk_success_patterns:
                src = p.get("citation", "?")
                pat = p.get("owl_pattern", "?")
                cq_s = p.get("cq_summary", "")[:60]
                parts.append(f"- [{src}] {pat}  ← ref: {cq_s}")
        if self.dk_failure_patterns:
            parts.append(f"\n=== Doctrine-Rejected Patterns ({len(self.dk_failure_patterns)}) — AVOID repeating these ===")
            for p in self.dk_failure_patterns:
                rule = p.get("rule", "?")
                cq_s = p.get("cq_summary", "")[:60]
                parts.append(f"- REJECTED: {rule}  (CQ: {cq_s}) — do not assert domain claims without doctrine basis")
        return "\n".join(parts)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
