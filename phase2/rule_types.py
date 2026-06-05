"""
Phase 2: Harness Rule Types.

Defines the data structures for harness rules compiled from OWL axioms.
Rules are typed (INPUT_VALIDATION, OUTPUT_CONSTRAINT, PHASE_GATE, TOOL_SCOPE)
and carry structured information for gate enforcement at runtime.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class RuleType(Enum):
    """Enumeration of harness rule categories."""
    INPUT_VALIDATION = "input_validation"
    OUTPUT_CONSTRAINT = "output_constraint"
    PHASE_GATE = "phase_gate"
    TOOL_SCOPE = "tool_scope"


@dataclass
class HarnessRule:
    """
    A single executable harness rule compiled from an OWL axiom.

    Each rule specifies when it fires (trigger_condition), what must hold
    (constraint_predicate), and what happens on violation (action_on_violation).
    """

    rule_id: str
    rule_type: RuleType
    trigger_condition: str       # Description of when this rule fires
    constraint_predicate: str    # What constraint must hold
    action_on_violation: str     # "reject" | "regenerate" | "block"
    entity_class: Optional[str] = None
    property_name: Optional[str] = None
    domain_class: Optional[str] = None
    range_class: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class HarnessRuleSet:
    """
    A compiled set of harness rules for a specific domain.

    Groups rules by type and tracks compilation time for efficiency metrics.
    """

    domain: str
    rules: list = field(default_factory=list)
    compilation_time_ms: float = 0.0

    def get_rules_by_type(self, rule_type: RuleType) -> list:
        """Return all rules of the specified type."""
        return [r for r in self.rules if r.rule_type == rule_type]

    def to_dict(self) -> dict:
        """Serialize the rule set summary to a dict."""
        return {
            "domain": self.domain,
            "n_rules": len(self.rules),
            "rules_by_type": {
                rt.value: len(self.get_rules_by_type(rt)) for rt in RuleType
            },
            "compilation_time_ms": self.compilation_time_ms,
        }
