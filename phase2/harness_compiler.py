"""
Phase 2: Harness Compiler.

Compiles OWL axioms extracted from the ontology into executable HarnessRules.
The compiler produces four types of rules:
  - INPUT_VALIDATION: entity type checks on incoming queries
  - OUTPUT_CONSTRAINT: ontology-consistency checks on LLM responses
  - PHASE_GATE: ordering constraints on sequential agent actions
  - TOOL_SCOPE: domain restrictions on tool usage per agent class

Rule compilation time is measured and stored for efficiency benchmarking (RCT metric).
"""

import time
import logging
from typing import Any

from phase2.axiom_extractor import AxiomExtractor
from phase2.rule_types import HarnessRule, HarnessRuleSet, RuleType

logger = logging.getLogger(__name__)


class HarnessCompiler:
    """
    Compiles an OWL ontology (Turtle format) into an executable HarnessRuleSet.

    The compiler translates declarative OWL axioms into imperative gate rules
    that can be evaluated at runtime in the Agent Runtime (Phase 3).
    """

    def __init__(self, domain: str):
        """
        Initialize the harness compiler.

        Args:
            domain: Domain identifier string (e.g., "smart_building").
        """
        self.domain = domain
        self.extractor = AxiomExtractor()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def compile(self, ontology_ttl: str) -> HarnessRuleSet:
        """
        Compile an OWL ontology into an executable HarnessRuleSet.

        Steps:
        1. Extract axioms from Turtle text via AxiomExtractor
        2. Generate INPUT_VALIDATION rules from ObjectProperty domains
        3. Generate OUTPUT_CONSTRAINT rules from class definitions
        4. Generate PHASE_GATE rules from property chains / ordering cues
        5. Generate TOOL_SCOPE rules from class hierarchy

        Args:
            ontology_ttl: OWL ontology in Turtle format.

        Returns:
            Populated HarnessRuleSet with compilation time set.
        """
        start_ms = time.time() * 1000

        axioms = self.extractor.extract_from_ttl(ontology_ttl)
        rules = []

        # 1. INPUT_VALIDATION rules from ObjectProperty domain/range
        for idx, prop in enumerate(axioms["object_properties"]):
            rule = self._make_input_rule(prop, idx)
            rules.append(rule)

        # 2. OUTPUT_CONSTRAINT rules for each defined class
        for idx, cls_name in enumerate(axioms["classes"]):
            rule = self._make_output_rule({"name": cls_name}, idx)
            rules.append(rule)

        # 3. PHASE_GATE rules from properties that imply ordering
        ordering_keywords = {
            "read", "write", "update", "create", "delete", "check",
            "issue", "execute", "monitor", "control", "detect",
        }
        for idx, prop in enumerate(axioms["object_properties"]):
            prop_lower = prop["name"].lower()
            if any(kw in prop_lower for kw in ordering_keywords):
                rule = self._make_phase_rule(prop, idx)
                rules.append(rule)

        # 4. TOOL_SCOPE rules from class hierarchy (subclass axioms)
        for idx, axiom in enumerate(axioms["subclass_axioms"]):
            cls_dict = {"name": axiom["subclass"], "superclass": axiom["superclass"]}
            rule = self._make_tool_rule(cls_dict, idx)
            rules.append(rule)

        # Also add tool scope rules for top-level agent-like classes
        agent_keywords = {"agent", "controller", "system", "manager", "unit", "command"}
        for idx, cls_name in enumerate(axioms["classes"]):
            if any(kw in cls_name.lower() for kw in agent_keywords):
                rule = self._make_tool_rule({"name": cls_name, "superclass": None}, idx + 1000)
                rules.append(rule)

        end_ms = time.time() * 1000
        compilation_time_ms = end_ms - start_ms

        rule_set = HarnessRuleSet(
            domain=self.domain,
            rules=rules,
            compilation_time_ms=compilation_time_ms,
        )

        logger.info(
            f"[HarnessCompiler] Compiled {len(rules)} rules in "
            f"{compilation_time_ms:.1f} ms for domain '{self.domain}'"
        )
        return rule_set

    # ------------------------------------------------------------------
    # Rule factory methods
    # ------------------------------------------------------------------

    def _make_input_rule(self, prop: dict, idx: int) -> HarnessRule:
        """
        Create an INPUT_VALIDATION rule from an ObjectProperty axiom.

        Validates that query inputs reference entities of the correct type.

        Args:
            prop: Dict with keys 'name', 'domain', 'range'.
            idx: Index for unique rule ID generation.

        Returns:
            HarnessRule of type INPUT_VALIDATION.
        """
        prop_name = prop.get("name", "unknown_property")
        domain_cls = prop.get("domain")
        range_cls = prop.get("range")

        trigger = (
            f"Query references property '{prop_name}'"
            + (f" with domain entity of type '{domain_cls}'" if domain_cls else "")
        )
        constraint = (
            f"Input entity for '{prop_name}' must be of class '{domain_cls or 'Any'}'"
        )
        if range_cls:
            constraint += f" and target must be of class '{range_cls}'"

        return HarnessRule(
            rule_id=f"IV_{self.domain}_{idx:04d}",
            rule_type=RuleType.INPUT_VALIDATION,
            trigger_condition=trigger,
            constraint_predicate=constraint,
            action_on_violation="reject",
            entity_class=domain_cls,
            property_name=prop_name,
            domain_class=domain_cls,
            range_class=range_cls,
            metadata={"source": "ObjectProperty", "property": prop_name},
        )

    def _make_output_rule(self, cls: dict, idx: int) -> HarnessRule:
        """
        Create an OUTPUT_CONSTRAINT rule from a class definition.

        Validates that LLM responses about entities of this class
        are consistent with the ontology.

        Args:
            cls: Dict with key 'name' (class name).
            idx: Index for unique rule ID generation.

        Returns:
            HarnessRule of type OUTPUT_CONSTRAINT.
        """
        cls_name = cls.get("name", "unknown_class")

        trigger = f"Response makes assertions about entities of class '{cls_name}'"
        constraint = (
            f"All assertions about '{cls_name}' instances must be consistent "
            f"with the ontology definition of '{cls_name}'"
        )

        return HarnessRule(
            rule_id=f"OC_{self.domain}_{idx:04d}",
            rule_type=RuleType.OUTPUT_CONSTRAINT,
            trigger_condition=trigger,
            constraint_predicate=constraint,
            action_on_violation="regenerate",
            entity_class=cls_name,
            metadata={"source": "Class", "class_name": cls_name},
        )

    def _make_phase_rule(self, prop: dict, idx: int) -> HarnessRule:
        """
        Create a PHASE_GATE rule from an ordering-sensitive property.

        Enforces that read/monitor actions precede write/control actions.

        Args:
            prop: Dict with keys 'name', 'domain', 'range'.
            idx: Index for unique rule ID generation.

        Returns:
            HarnessRule of type PHASE_GATE.
        """
        prop_name = prop.get("name", "unknown_property")
        domain_cls = prop.get("domain")

        read_keywords = {"read", "monitor", "check", "detect", "observe", "sense"}
        write_keywords = {"write", "update", "create", "issue", "execute", "control", "delete"}

        prop_lower = prop_name.lower()
        if any(kw in prop_lower for kw in read_keywords):
            # This is a read-type property; write must come after
            trigger = f"Agent attempts write/control action on '{domain_cls or 'entity'}'"
            constraint = (
                f"Property '{prop_name}' (read/monitor) must be executed before "
                f"any write/control action on the same entity"
            )
            precondition = f"read_completed_{prop_name}"
        elif any(kw in prop_lower for kw in write_keywords):
            # Write-type property; requires prior read
            trigger = f"Agent attempts action '{prop_name}'"
            constraint = (
                f"Action '{prop_name}' requires prior monitoring/read phase "
                f"to be completed for '{domain_cls or 'entity'}'"
            )
            precondition = f"monitoring_completed_{domain_cls or 'entity'}"
        else:
            trigger = f"Agent invokes property action '{prop_name}'"
            constraint = f"Property '{prop_name}' must be used in correct sequence"
            precondition = f"context_ready_{prop_name}"

        return HarnessRule(
            rule_id=f"PG_{self.domain}_{idx:04d}",
            rule_type=RuleType.PHASE_GATE,
            trigger_condition=trigger,
            constraint_predicate=constraint,
            action_on_violation="block",
            entity_class=domain_cls,
            property_name=prop_name,
            domain_class=domain_cls,
            metadata={
                "source": "ObjectProperty",
                "property": prop_name,
                "precondition": precondition,
            },
        )

    def _make_tool_rule(self, cls: dict, idx: int) -> HarnessRule:
        """
        Create a TOOL_SCOPE rule from a class hierarchy entry.

        Restricts the tools available to agents of a given class.

        Args:
            cls: Dict with keys 'name' and optionally 'superclass'.
            idx: Index for unique rule ID generation.

        Returns:
            HarnessRule of type TOOL_SCOPE.
        """
        cls_name = cls.get("name", "unknown_class")
        superclass = cls.get("superclass")

        # Infer allowed tool domains from class semantics
        cls_lower = cls_name.lower()
        if any(kw in cls_lower for kw in ["sensor", "monitor", "meter"]):
            allowed_tools = "read_sensor, query_state, report_anomaly"
        elif any(kw in cls_lower for kw in ["actuator", "controller", "hvac", "control"]):
            allowed_tools = "issue_command, set_setpoint, activate, deactivate"
        elif any(kw in cls_lower for kw in ["unit", "mission", "command"]):
            allowed_tools = "assess_situation, issue_order, query_roe"
        elif any(kw in cls_lower for kw in ["manager", "agent", "system"]):
            allowed_tools = "read_sensor, issue_command, report_anomaly, query_state, set_setpoint"
        else:
            allowed_tools = f"tools_allowed_for_{cls_name}"

        trigger = f"Agent acting as '{cls_name}' invokes a tool"
        constraint = (
            f"Tools available to '{cls_name}' are limited to: [{allowed_tools}]"
        )
        if superclass:
            constraint += f" (inherited from '{superclass}')"

        return HarnessRule(
            rule_id=f"TS_{self.domain}_{idx:04d}",
            rule_type=RuleType.TOOL_SCOPE,
            trigger_condition=trigger,
            constraint_predicate=constraint,
            action_on_violation="reject",
            entity_class=cls_name,
            metadata={
                "source": "SubClassAxiom" if superclass else "Class",
                "class_name": cls_name,
                "superclass": superclass,
                "allowed_tools": allowed_tools,
            },
        )


if __name__ == "__main__":
    sample_ttl = """@prefix : <http://coha.org/smart_building#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://coha.org/smart_building> a owl:Ontology .

:Sensor a owl:Class .
:TemperatureSensor a owl:Class ; rdfs:subClassOf :Sensor .
:HVACZone a owl:Class .
:SetpointValue a owl:Class .

:hasSetpointTemperature a owl:ObjectProperty ;
    rdfs:domain :HVACZone ;
    rdfs:range :SetpointValue .

:controls a owl:ObjectProperty ;
    rdfs:domain :HVACActuator ;
    rdfs:range :HVACZone .
"""

    compiler = HarnessCompiler("smart_building")
    rule_set = compiler.compile(sample_ttl)
    print(rule_set.to_dict())
    for r in rule_set.rules[:5]:
        print(f"  [{r.rule_type.value}] {r.rule_id}: {r.constraint_predicate[:60]}")
