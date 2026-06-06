"""
Phase 3: Agent Runtime.

Implements the closed-loop COHA agent pipeline:
  Input Gate → Context Assembly → LLM Inference → Output Gate → Phase Gate

Each gate step is timed for the GO (Gate Overhead) efficiency metric.
Supports configurable enable/disable of each gate for ablation studies.
"""

import time
import logging
from typing import Optional

from llm_client import UnifiedLLMClient
from phase2.rule_types import HarnessRuleSet
from phase3.gates import InputGate, OutputGate, PhaseGate
from phase3.context_assembly import ContextAssembler

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    COHA Agent Runtime — closed-loop ontology-grounded agent.

    Runs a full query through the COHA pipeline:
    1. Input Gate: validates the query
    2. Context Assembly: retrieves relevant documents
    3. LLM Inference: generates a response
    4. Output Gate: validates the response (with regeneration)
    5. Phase Gate: checks next-action preconditions

    Gate overhead is measured for the GO metric. Number of regenerations
    is tracked for efficiency analysis.
    """

    def __init__(
        self,
        llm_client: UnifiedLLMClient,
        rule_set: HarnessRuleSet,
        context_assembler: ContextAssembler,
        config: dict,
    ):
        """
        Initialize the agent runtime.

        Args:
            llm_client: UnifiedLLMClient instance.
            rule_set: Compiled harness rule set for the domain.
            context_assembler: Pre-built context assembler with document index.
            config: Configuration dict with keys:
                - enable_input_gate: bool
                - enable_output_gate: bool
                - enable_phase_gate: bool
                - max_regeneration_attempts: int
        """
        self.llm_client = llm_client
        self.rule_set = rule_set
        self.context_assembler = context_assembler
        self.config = config

        enable_out = config.get("enable_output_gate", True)
        enable_phase = config.get("enable_phase_gate", True)
        enable_in = config.get("enable_input_gate", True)

        self.input_gate = InputGate(rule_set) if enable_in else None
        self.output_gate = OutputGate(rule_set, llm_client, enabled=enable_out)
        self.phase_gate = PhaseGate(rule_set, enabled=enable_phase)
        self.max_regen = config.get("max_regeneration_attempts", 3)

    def run(self, query: str, session_state: dict = None) -> dict:
        """
        Execute the full COHA pipeline for a single query.

        Args:
            query: User query string.
            session_state: Optional agent state dict (carries across turns).

        Returns:
            dict with keys:
                - response: str — final agent response
                - violations: list[str] — all gate violations encountered
                - gate_overhead_ms: float — total ms spent in gate checks
                - n_regenerations: int — number of LLM regeneration attempts
                - passed_gates: dict — which gates the query passed/failed
        """
        if session_state is None:
            session_state = {}

        all_violations = []
        gate_overhead_ms = 0.0
        n_regenerations = 0
        passed_gates = {
            "input_gate": None,
            "output_gate": None,
            "phase_gate": None,
        }

        # ----------------------------------------------------------------
        # Step 1: Input Gate
        # ----------------------------------------------------------------
        if self.input_gate is not None:
            t0 = time.time()
            input_passed, input_viols = self.input_gate.validate(query, session_state)
            gate_overhead_ms += (time.time() - t0) * 1000

            passed_gates["input_gate"] = input_passed
            if input_viols:
                all_violations.extend(input_viols)

            if not input_passed:
                return {
                    "response": (
                        "Query rejected by Input Gate due to constraint violations. "
                        "Please rephrase your query to include valid entity references.\n"
                        "Violations: " + "; ".join(input_viols)
                    ),
                    "violations": all_violations,
                    "gate_overhead_ms": gate_overhead_ms,
                    "n_regenerations": 0,
                    "passed_gates": passed_gates,
                }
        else:
            passed_gates["input_gate"] = True

        # ----------------------------------------------------------------
        # Step 2: Context Assembly
        # ----------------------------------------------------------------
        retrieved_docs = self.context_assembler.retrieve(query, k=5)

        # ----------------------------------------------------------------
        # Step 3: LLM Inference (with output gate loop)
        # ----------------------------------------------------------------
        system_prompt = self._build_system_prompt(retrieved_docs, self.rule_set)
        response = ""
        output_passed = False
        output_violations = []

        for attempt in range(self.max_regen + 1):
            if attempt > 0:
                n_regenerations += 1

            # Build user message (include constraint feedback on retry)
            user_message = query
            if attempt > 0 and output_violations:
                feedback = "\n".join(f"  - {v}" for v in output_violations[:5])
                user_message = (
                    f"{query}\n\n"
                    f"[IMPORTANT: Your previous response violated the following "
                    f"ontology constraints. Please regenerate a corrected response "
                    f"that satisfies all constraints:]\n{feedback}"
                )

            response = self._llm_generate(system_prompt, user_message)

            # ----------------------------------------------------------------
            # Step 4: Output Gate
            # ----------------------------------------------------------------
            t0 = time.time()
            output_passed, output_violations = self.output_gate.validate(response, query)
            gate_overhead_ms += (time.time() - t0) * 1000

            if output_violations:
                all_violations.extend(output_violations)

            if output_passed:
                break

            if attempt < self.max_regen:
                logger.info(
                    f"[AgentRuntime] Output gate failed (attempt {attempt+1}), "
                    f"regenerating... Violations: {output_violations[:2]}"
                )
            else:
                logger.warning(
                    f"[AgentRuntime] Output gate still failing after {self.max_regen} "
                    f"regenerations. Returning best available response."
                )

        passed_gates["output_gate"] = output_passed

        # ----------------------------------------------------------------
        # Step 5: Phase Gate
        # ----------------------------------------------------------------
        t0 = time.time()
        phase_passed, phase_viols = self.phase_gate.check_preconditions(
            current_phase="inference",
            action="respond",
            state=session_state,
        )
        gate_overhead_ms += (time.time() - t0) * 1000

        passed_gates["phase_gate"] = phase_passed
        if phase_viols:
            all_violations.extend(phase_viols)

        # Update session state
        session_state = self.phase_gate.update_state(
            "respond", {"success": True, "response": response}, session_state
        )

        return {
            "response": response,
            "violations": all_violations,
            "gate_overhead_ms": gate_overhead_ms,
            "n_regenerations": n_regenerations,
            "passed_gates": passed_gates,
        }

    def _build_system_prompt(self, retrieved_docs: list, rule_set: HarnessRuleSet) -> str:
        """
        Build the LLM system prompt with ontology context and retrieved docs.

        Args:
            retrieved_docs: List of retrieved context document strings.
            rule_set: Harness rule set for domain context.

        Returns:
            System prompt string.
        """
        from phase2.rule_types import RuleType

        # Get key constraints summary
        output_rules = rule_set.get_rules_by_type(RuleType.OUTPUT_CONSTRAINT)
        key_constraints = []
        for r in output_rules[:8]:
            key_constraints.append(f"  - {r.constraint_predicate}")
        constraints_text = "\n".join(key_constraints) if key_constraints else "  - Follow domain ontology"

        # Get input validation rules summary
        input_rules = rule_set.get_rules_by_type(RuleType.INPUT_VALIDATION)
        entity_types = list({r.entity_class for r in input_rules if r.entity_class})[:8]
        entity_text = ", ".join(entity_types) if entity_types else "as defined in domain ontology"

        # Retrieved context
        context_text = ""
        if retrieved_docs:
            context_parts = [f"[Doc {i+1}] {doc[:400]}" for i, doc in enumerate(retrieved_docs)]
            context_text = "\n\n".join(context_parts)

        system_prompt = f"""You are an ontology-grounded AI agent for the {rule_set.domain} domain.
You operate under strict ontology constraints derived from an OWL knowledge graph.

## DOMAIN ENTITY TYPES
The following entity types are defined in the domain ontology: {entity_text}

## ONTOLOGY CONSTRAINTS
Your responses MUST satisfy these constraints:
{constraints_text}

## RETRIEVED CONTEXT
Use the following relevant domain documents to answer queries accurately:

{context_text if context_text else "[No additional context retrieved]"}

## INSTRUCTIONS
- Ground your responses in the ontology-defined entity types and relationships
- Use precise, factual language based on the provided context
- If information is not available in the context, say so explicitly — do not hallucinate
- Respect all domain constraints listed above
- For numerical values, always include units (e.g., °C, kWh, m²)
- For control commands, always specify the target entity and expected outcome"""

        return system_prompt

    def _llm_generate(self, system: str, user: str) -> str:
        """
        Call the LLM to generate a response.

        Args:
            system: System prompt string.
            user: User message string.

        Returns:
            Generated response string.
        """
        try:
            return self.llm_client.generate(system=system, user=user, max_tokens=1024)
        except RuntimeError as e:
            logger.error(f"LLM generation failed: {e}")
            return f"[Error: LLM generation failed: {e}]"


if __name__ == "__main__":
    from llm_client import get_client
    from phase2.harness_compiler import HarnessCompiler
    from domains.smart_building import DOMAIN_DOCS, MANUAL_ONTOLOGY_TTL

    client = get_client()

    compiler = HarnessCompiler("smart_building")
    rule_set = compiler.compile(MANUAL_ONTOLOGY_TTL)

    docs = [p.strip() for p in DOMAIN_DOCS.split("\n\n") if p.strip()]
    assembler = ContextAssembler(docs, MANUAL_ONTOLOGY_TTL, use_ontology_guidance=True)
    assembler.build_index()

    config = {
        "enable_input_gate": True,
        "enable_output_gate": True,
        "enable_phase_gate": True,
        "max_regeneration_attempts": 2,
    }

    runtime = AgentRuntime(client, rule_set, assembler, config)
    result = runtime.run("Zone B-103 temperature is 28.5°C with setpoint 22°C. What action should the HVAC take?")
    print("Response:", result["response"][:300])
    print("Gate overhead:", result["gate_overhead_ms"], "ms")
    print("Regenerations:", result["n_regenerations"])
    print("Passed gates:", result["passed_gates"])
