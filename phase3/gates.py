"""
Phase 3: Gate Implementations.

Three gate classes enforce the Harness rules at runtime:
  - InputGate: validates incoming queries against INPUT_VALIDATION / TOOL_SCOPE rules
  - OutputGate: validates LLM responses against OUTPUT_CONSTRAINT rules (with LLM judge)
  - PhaseGate: enforces action ordering via PHASE_GATE rules

Each gate returns (passed: bool, violations: list[str]).
Gate overhead is measured externally by AgentRuntime for the GO metric.
"""

import re
import time
import logging
import anthropic
from typing import Tuple

from phase2.rule_types import HarnessRule, HarnessRuleSet, RuleType

logger = logging.getLogger(__name__)


class InputGate:
    """
    Input Gate — validates queries before LLM inference.

    Checks incoming queries against INPUT_VALIDATION and TOOL_SCOPE rules
    using keyword matching on entity types mentioned in the query.
    """

    def __init__(self, rule_set: HarnessRuleSet):
        """
        Initialize the input gate.

        Args:
            rule_set: Compiled harness rule set for the domain.
        """
        self.rule_set = rule_set
        self._input_rules = rule_set.get_rules_by_type(RuleType.INPUT_VALIDATION)
        self._tool_rules = rule_set.get_rules_by_type(RuleType.TOOL_SCOPE)

    def validate(self, query: str, context: dict = None) -> Tuple[bool, list]:
        """
        Validate an incoming query against input and tool-scope rules.

        Uses keyword matching to detect entity type references in the query
        and checks them against rule entity_class fields.

        Args:
            query: The user query string.
            context: Optional additional context dict.

        Returns:
            Tuple (passed: bool, violations: list[str]).
        """
        if context is None:
            context = {}

        violations = []
        query_lower = query.lower()

        # Check INPUT_VALIDATION rules
        for rule in self._input_rules:
            if rule.entity_class and rule.property_name:
                prop_lower = rule.property_name.lower()
                entity_lower = rule.entity_class.lower() if rule.entity_class else ""

                # If the property is mentioned in the query, check entity type
                if prop_lower in query_lower:
                    # Look for entity type keywords
                    entity_keywords = self._extract_entity_keywords(entity_lower)
                    if entity_keywords and not any(kw in query_lower for kw in entity_keywords):
                        violations.append(
                            f"Rule {rule.rule_id}: Query references property "
                            f"'{rule.property_name}' but missing expected entity type "
                            f"'{rule.entity_class}'"
                        )

        # Check TOOL_SCOPE rules for tool-like keywords in query
        tool_keywords_in_query = self._detect_tool_keywords(query_lower)
        if tool_keywords_in_query:
            for rule in self._tool_rules:
                allowed = rule.metadata.get("allowed_tools", "")
                for tool_kw in tool_keywords_in_query:
                    # Check if the requested tool type is in allowed list
                    if allowed and not self._tool_allowed(tool_kw, allowed):
                        # Only flag if the entity class is actually mentioned
                        entity_class = rule.entity_class or ""
                        if entity_class.lower() in query_lower:
                            violations.append(
                                f"Rule {rule.rule_id}: Tool action '{tool_kw}' may not be "
                                f"permitted for agent class '{rule.entity_class}'"
                            )
                            break

        passed = len(violations) == 0
        return passed, violations

    def _extract_entity_keywords(self, entity_name: str) -> list:
        """Extract searchable keywords from an entity class name."""
        # Split camelCase and underscore-joined names
        words = re.findall(r"[a-z]+", entity_name.lower())
        return [w for w in words if len(w) > 2]

    def _detect_tool_keywords(self, query_lower: str) -> list:
        """Detect references to tool-like actions in query."""
        tool_patterns = [
            "delete", "remove", "override", "force", "bypass",
            "escalate", "launch", "fire", "attack",
        ]
        return [kw for kw in tool_patterns if kw in query_lower]

    def _tool_allowed(self, tool_kw: str, allowed_tools: str) -> bool:
        """Check if a tool keyword appears in the allowed tools string."""
        return tool_kw.lower() in allowed_tools.lower()


class OutputGate:
    """
    Output Gate — validates LLM responses against ontology constraints.

    Uses an LLM judge to check whether response assertions violate
    any OUTPUT_CONSTRAINT rules. Can be disabled for ablation studies.
    """

    def __init__(
        self,
        rule_set: HarnessRuleSet,
        llm_client: anthropic.Anthropic,
        enabled: bool = True,
    ):
        """
        Initialize the output gate.

        Args:
            rule_set: Compiled harness rule set.
            llm_client: Anthropic API client for LLM judge calls.
            enabled: If False, gate always passes (for ablation study).
        """
        self.rule_set = rule_set
        self.llm_client = llm_client
        self.enabled = enabled
        self._output_rules = rule_set.get_rules_by_type(RuleType.OUTPUT_CONSTRAINT)

    def validate(self, response: str, query: str) -> Tuple[bool, list]:
        """
        Validate an LLM response against output constraint rules.

        Extracts key assertions from the response and uses an LLM judge
        to check them against relevant ontology constraints.

        Args:
            response: LLM-generated response string.
            query: Original user query (for context).

        Returns:
            Tuple (passed: bool, violations: list[str]).
        """
        if not self.enabled:
            return True, []

        if not self._output_rules:
            return True, []

        # Extract key assertions from the response
        assertions = self._extract_assertions(response)
        if not assertions:
            return True, []

        violations = []

        # Find rules relevant to this response (by entity class mention)
        response_lower = response.lower()
        relevant_rules = [
            r for r in self._output_rules
            if r.entity_class and r.entity_class.lower() in response_lower
        ]

        if not relevant_rules:
            # Use the top-N rules as a sample
            relevant_rules = self._output_rules[:5]

        if not relevant_rules:
            return True, []

        # Summarize constraints for the LLM judge
        constraints_text = "\n".join(
            f"- [{r.rule_id}] {r.constraint_predicate}"
            for r in relevant_rules[:10]
        )
        assertions_text = "\n".join(f"- {a}" for a in assertions[:10])

        prompt = (
            f"You are an ontology-grounded constraint checker for an AI agent.\n\n"
            f"DOMAIN: {self.rule_set.domain}\n\n"
            f"ONTOLOGY CONSTRAINTS:\n{constraints_text}\n\n"
            f"ORIGINAL QUERY:\n{query}\n\n"
            f"RESPONSE ASSERTIONS TO CHECK:\n{assertions_text}\n\n"
            f"Do any of these response assertions violate the listed ontology constraints?\n"
            f"Answer YES or NO on the first line.\n"
            f"If YES, list each violated constraint rule ID and brief reason (one per line).\n"
            f"If NO, write 'All assertions are ontology-consistent.'"
        )

        try:
            resp = self.llm_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            judge_text = resp.content[0].text.strip()
            first_line = judge_text.split("\n")[0].strip().upper()

            if first_line.startswith("YES"):
                # Parse violation lines
                lines = judge_text.split("\n")[1:]
                for line in lines:
                    line = line.strip()
                    if line and not line.lower().startswith("all assertions"):
                        violations.append(f"OutputGate: {line}")

                if not violations:
                    violations.append("OutputGate: LLM judge detected constraint violation.")

        except anthropic.APIError as e:
            logger.warning(f"OutputGate LLM judge call failed: {e}. Skipping output validation.")
            return True, []

        passed = len(violations) == 0
        return passed, violations

    def _extract_assertions(self, response: str) -> list:
        """
        Extract key assertions from a response string.

        Looks for sentences containing "is a", "has", numeric values with units,
        and action statements.

        Args:
            response: LLM response text.

        Returns:
            List of assertion strings.
        """
        assertions = []
        sentences = re.split(r"(?<=[.!?])\s+", response)

        for sentence in sentences:
            s = sentence.strip()
            if not s:
                continue

            # Prioritize sentences with factual assertion patterns
            has_assertion = (
                " is a " in s.lower()
                or " has " in s.lower()
                or " must " in s.lower()
                or " should " in s.lower()
                or bool(re.search(r"\d+\.?\d*\s*(?:°C|kWh|kW|%|m|km|units?|degrees?)", s))
                or bool(re.search(r"\b(?:is|are|was|were)\s+\w+", s, re.IGNORECASE))
                or bool(re.search(r"\b(?:increase|decrease|set|activate|deactivate|command)\b", s, re.IGNORECASE))
            )

            if has_assertion and len(s) > 15:
                assertions.append(s[:200])

        return assertions[:15]


class PhaseGate:
    """
    Phase Gate — enforces action ordering constraints.

    Checks PHASE_GATE rules to ensure the agent's actions follow
    the correct sequence (e.g., read before write).
    """

    def __init__(self, rule_set: HarnessRuleSet, enabled: bool = True):
        """
        Initialize the phase gate.

        Args:
            rule_set: Compiled harness rule set.
            enabled: If False, gate always passes (for ablation study).
        """
        self.rule_set = rule_set
        self.enabled = enabled
        self._phase_rules = rule_set.get_rules_by_type(RuleType.PHASE_GATE)

    def check_preconditions(
        self,
        current_phase: str,
        action: str,
        state: dict,
    ) -> Tuple[bool, list]:
        """
        Check whether the proposed action is permitted in the current phase.

        Args:
            current_phase: Name of the current execution phase.
            action: The action the agent wants to perform.
            state: Current agent state dict.

        Returns:
            Tuple (allowed: bool, violations: list[str]).
        """
        if not self.enabled:
            return True, []

        violations = []
        action_lower = action.lower()

        for rule in self._phase_rules:
            prop_name = rule.property_name or ""
            precondition = rule.metadata.get("precondition", "")
            trigger = rule.trigger_condition.lower()

            # Check if this rule applies to the current action
            if prop_name.lower() in action_lower or any(
                kw in action_lower for kw in ["write", "update", "execute", "control", "issue"]
            ):
                # Check if the precondition is satisfied in the state
                if precondition and not state.get(precondition, False):
                    # Check if trigger condition matches
                    if any(kw in trigger for kw in ["write", "control", "execute", "update", "issue"]):
                        violations.append(
                            f"Rule {rule.rule_id}: Precondition '{precondition}' "
                            f"not satisfied for action '{action}'. "
                            f"{rule.constraint_predicate}"
                        )

        allowed = len(violations) == 0
        return allowed, violations

    def update_state(self, action: str, result: dict, state: dict) -> dict:
        """
        Update agent state after a completed action.

        Records completed actions in the state dict so future phase gate
        checks can verify preconditions.

        Args:
            action: The action that was completed.
            result: Result dict from the action.
            state: Current state dict.

        Returns:
            Updated state dict.
        """
        new_state = dict(state)
        action_lower = action.lower()

        # Mark read/monitor actions as completed
        read_keywords = ["read", "monitor", "check", "detect", "observe", "sense", "query"]
        if any(kw in action_lower for kw in read_keywords):
            new_state[f"read_completed_{action}"] = True
            new_state["monitoring_completed"] = True
            new_state["monitoring_completed_entity"] = action

        # Mark write/control actions
        write_keywords = ["write", "update", "execute", "control", "issue", "set", "activate"]
        if any(kw in action_lower for kw in write_keywords):
            new_state[f"write_completed_{action}"] = True

        # Record the action in history
        if "action_history" not in new_state:
            new_state["action_history"] = []
        new_state["action_history"] = new_state["action_history"] + [
            {"action": action, "success": result.get("success", True)}
        ]

        return new_state


if __name__ == "__main__":
    import os
    import anthropic as _anthropic
    from phase2.rule_types import HarnessRuleSet, HarnessRule, RuleType

    # Create a minimal rule set for testing
    rules = [
        HarnessRule(
            rule_id="IV_test_0001",
            rule_type=RuleType.INPUT_VALIDATION,
            trigger_condition="Query references temperature property",
            constraint_predicate="Temperature sensor entity must be specified",
            action_on_violation="reject",
            entity_class="TemperatureSensor",
            property_name="hasCurrentTemperature",
        ),
        HarnessRule(
            rule_id="PG_test_0001",
            rule_type=RuleType.PHASE_GATE,
            trigger_condition="Agent attempts control action",
            constraint_predicate="Monitoring must precede control",
            action_on_violation="block",
            property_name="controls",
            metadata={"precondition": "monitoring_completed"},
        ),
    ]
    rs = HarnessRuleSet(domain="test", rules=rules)

    ig = InputGate(rs)
    passed, viols = ig.validate("What is the temperature of Zone A?")
    print(f"InputGate: passed={passed}, violations={viols}")

    pg = PhaseGate(rs)
    state = {}
    ok, viols = pg.check_preconditions("inference", "execute_control_command", state)
    print(f"PhaseGate (no precondition): passed={ok}, violations={viols}")

    state = pg.update_state("monitor_sensors", {}, state)
    state["monitoring_completed"] = True
    ok2, viols2 = pg.check_preconditions("inference", "execute_control_command", state)
    print(f"PhaseGate (after monitoring): passed={ok2}, violations={viols2}")
