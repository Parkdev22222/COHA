"""
COHA Harness: main orchestration loop for ontology generation with Self-Improving Phase Gate.

Supports all experimental conditions:
  - COHA-full       : context_reset=T, fq=T, dk=T
  - COHA-no-reset   : context_reset=F, fq=T, dk=T
  - COHA-no-DK      : context_reset=T, fq=T, dk=F
  - COHA-no-FQ      : context_reset=T, fq=F, dk=T
  - COHA-static     : context_reset=T, fixed FQ rules, no accumulation
  - Vanilla         : context_reset=F, no gate at all
  - COHA+Ontogenia  : context_reset=T, fq=T, dk=T, metacognitive generation + ODP injection
"""
import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from coha.handoff_artifact import HandoffArtifact, AccumulatedOntology
from coha.phase_gate import SelfImprovingPhaseGate, GateConfig
from coha.axiom_generator import AxiomGenerator
from coha.owl_utils import (
    merge_ontologies,
    check_consistency,
    extract_class_names,
    extract_property_names,
)

logger = logging.getLogger(__name__)


@dataclass
class HarnessConfig:
    context_reset: bool = True
    gate_config: GateConfig = field(default_factory=GateConfig.coha_full)
    max_retries: int = 3
    name: str = "COHA-full"
    use_metacognition: bool = False  # Ontogenia-style 2-phase generation with ODP injection

    @classmethod
    def coha_full(cls):
        return cls(context_reset=True, gate_config=GateConfig.coha_full(), name="COHA-full")

    @classmethod
    def coha_no_reset(cls):
        return cls(context_reset=False, gate_config=GateConfig.coha_full(), name="COHA-no-reset")

    @classmethod
    def coha_no_dk(cls):
        return cls(context_reset=True, gate_config=GateConfig.coha_no_dk(), name="COHA-no-DK")

    @classmethod
    def coha_no_fq(cls):
        return cls(context_reset=True, gate_config=GateConfig.coha_no_fq(), name="COHA-no-FQ")

    @classmethod
    def coha_static_gate(cls):
        return cls(context_reset=True, gate_config=GateConfig.static_gate(), name="COHA-static-gate")

    @classmethod
    def coha_ontogenia(cls):
        """COHA+Ontogenia: full COHA gate + metacognitive generation with ODP injection."""
        return cls(
            context_reset=True,
            gate_config=GateConfig.coha_full(),
            name="COHA+Ontogenia",
            use_metacognition=True,
        )

    @classmethod
    def vanilla(cls):
        return cls(context_reset=False, gate_config=GateConfig.no_gate(), name="Vanilla-CQbyCQ")


class COHAHarness:
    def __init__(self, llm_client, config: HarnessConfig):
        self.llm_client = llm_client
        self.config = config
        self.generator = AxiomGenerator(llm_client)
        self.phase_gate = SelfImprovingPhaseGate(llm_client, config.gate_config)

    def run(self, cqs: List[str], user_story: str) -> dict:
        """
        Run the COHA harness over all CQs.

        Returns dict with:
          ontology_ttl, handoff, qic_data, rar_data,
          gate_times, total_times, n_retries_total,
          final_fq_rules, final_dk_rules
        """
        # Reset token/call counters so each variant is measured independently
        if hasattr(self.llm_client, "reset_stats"):
            self.llm_client.reset_stats()

        handoff = HandoffArtifact.initial()
        accumulated_ttl = ""  # only used for vanilla (no-reset)
        qic_data = []   # [(cq_index, cq_text, ccr_so_far)]
        rar_data = []   # [(cq_index, n_rules_added)]
        gate_times = []
        total_times = []
        n_retries_total = 0

        for i, cq in enumerate(cqs):
            cq_text = cq["question"] if isinstance(cq, dict) else cq
            cq_entities = cq.get("key_entities", []) if isinstance(cq, dict) else []
            print(f"  [{self.config.name}] CQ {i+1}/{len(cqs)}: {cq_text[:60]}...")
            n_rules_before = (
                len(handoff.formal_quality_rules) + len(handoff.domain_knowledge_rules)
            )
            t_start = time.time()

            delta_oi = None
            gate_result = None
            succeeded = False
            prev_violations = []  # violations from previous attempt, fed back to generator

            for attempt in range(self.config.max_retries):
                if attempt > 0:
                    n_retries_total += 1

                # Generate delta-Oi, injecting previous gate violations on retry
                if self.config.context_reset:
                    if self.config.use_metacognition:
                        delta_oi = self.generator.generate_with_metacognition_reset(
                            cq_text, user_story, handoff,
                            key_entities=cq_entities,
                            violations=prev_violations,
                        )
                    else:
                        delta_oi = self.generator.generate_with_reset(
                            cq_text, user_story, handoff,
                            key_entities=cq_entities,
                            violations=prev_violations,
                        )
                else:
                    delta_oi = self.generator.generate_full_context(
                        cq_text, user_story, accumulated_ttl,
                        key_entities=cq_entities,
                        violations=prev_violations,
                    )

                # Apply Phase Gate (if any rules or accumulation is active)
                has_gate = (
                    self.config.gate_config.fq_accumulate
                    or self.config.gate_config.dk_accumulate
                    or bool(self.config.gate_config.initial_fq_rules)
                )

                if has_gate:
                    gate_result = self.phase_gate.process(delta_oi, handoff, cq_text)
                    gate_times.append(gate_result.latency_ms)
                    if gate_result.passed or attempt == self.config.max_retries - 1:
                        succeeded = gate_result.passed
                        break
                    # Pass violations to next generation attempt
                    prev_violations = gate_result.violations
                    print(f"    Gate failed (attempt {attempt+1}): {gate_result.violations[:2]}")
                else:
                    gate_result = None
                    succeeded = True
                    break

            total_ms = (time.time() - t_start) * 1000
            total_times.append(total_ms)

            if not delta_oi:
                logger.warning(f"Skipping CQ {i+1}: no delta generated.")
                continue

            # Skip merge if gate rejected on all attempts
            if gate_result is not None and not succeeded:
                logger.warning(f"CQ {i+1}: gate rejected after {self.config.max_retries} attempts, discarding delta.")
                rar_data.append((i + 1, 0))
                # QIC: gate rejected — quality stays at current accumulated level
                current_classes = len(handoff.accumulated_ontology.classes)
                qic_data.append((i + 1, cq_text, current_classes))
                # Still update rule sets from gate extraction
                new_fq = list(dict.fromkeys(handoff.formal_quality_rules + gate_result.new_fq_rules))
                new_dk = list(dict.fromkeys(handoff.domain_knowledge_rules + gate_result.new_dk_rules))
                handoff = HandoffArtifact(
                    iteration=i + 1,
                    completed_cqs=handoff.completed_cqs + [cq_text],
                    accumulated_ontology=handoff.accumulated_ontology,
                    formal_quality_rules=new_fq,
                    domain_knowledge_rules=new_dk,
                    next_cq=cqs[i + 1] if i + 1 < len(cqs) else "",
                    coverage_gaps=[],
                )
                if isinstance(handoff.next_cq, dict):
                    handoff.next_cq = handoff.next_cq.get("question", "")
                continue

            # Merge into accumulated ontology
            if self.config.context_reset:
                new_ttl = merge_ontologies(handoff.accumulated_ontology.ttl, delta_oi)
            else:
                new_ttl = merge_ontologies(accumulated_ttl, delta_oi)
                accumulated_ttl = new_ttl

            is_consistent = check_consistency(new_ttl)
            classes = extract_class_names(new_ttl)
            properties = extract_property_names(new_ttl)

            # Update rule sets (FQ: simple union+dedup; DK: conflict resolution per §3.2.2)
            new_fq = list(handoff.formal_quality_rules)
            new_dk = list(handoff.domain_knowledge_rules)
            if gate_result:
                new_fq.extend(gate_result.new_fq_rules)
                new_fq = list(dict.fromkeys(new_fq))
                if gate_result.new_dk_rules:
                    new_dk = self.phase_gate.resolve_dk_conflicts(new_dk, gate_result.new_dk_rules)
                else:
                    new_dk = list(dict.fromkeys(new_dk))

            # RAR: rules added this iteration
            n_rules_after = len(new_fq) + len(new_dk)
            rar_data.append((i + 1, n_rules_after - n_rules_before))

            # QIC: cumulative class count at step k (structural quality proxy)
            qic_data.append((i + 1, cq_text, len(classes)))

            # Update handoff
            next_cq = cqs[i + 1] if i + 1 < len(cqs) else ""
            if isinstance(next_cq, dict):
                next_cq = next_cq.get("question", "")
            handoff = HandoffArtifact(
                iteration=i + 1,
                completed_cqs=handoff.completed_cqs + [cq_text],
                accumulated_ontology=AccumulatedOntology(
                    classes=classes,
                    properties=properties,
                    axioms=[],
                    consistency="VALID" if is_consistent else "INVALID",
                    ttl=new_ttl,
                ),
                formal_quality_rules=new_fq,
                domain_knowledge_rules=new_dk,
                next_cq=next_cq,
                coverage_gaps=[],
            )

        final_ttl = (
            handoff.accumulated_ontology.ttl if self.config.context_reset else accumulated_ttl
        )

        return {
            "ontology_ttl": final_ttl,
            "handoff": handoff,
            "qic_data": qic_data,
            "rar_data": rar_data,
            "gate_times": gate_times,
            "total_times": total_times,
            "n_retries_total": n_retries_total,
            "final_fq_rules": handoff.formal_quality_rules,
            "final_dk_rules": handoff.domain_knowledge_rules,
            "is_consistent": handoff.accumulated_ontology.consistency == "VALID",
            "usage_stats": (
                self.llm_client.get_usage_stats()
                if hasattr(self.llm_client, "get_usage_stats")
                else {}
            ),
        }
