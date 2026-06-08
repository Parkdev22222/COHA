"""
Evaluation metrics for COHA v2.

Ontology Quality:
  CCR  - CQ Coverage Rate
  OC   - OWL Consistency
  SC   - Structural Completeness vs Gold Standard

COHA-specific Dynamic Improvement:
  QIC  - Quality Improvement Curve (CCR at each CQ index k)
  RAR  - Rule Accumulation Rate (rules added per gate pass)
  DRC  - Domain Rule Contribution (CCR: COHA-full - COHA-no-DK)
  FRC  - Formal Rule Contribution (OC: COHA-full - COHA-no-FQ)

Efficiency:
  GO   - Gate Overhead (gate_time / total_time)
  CE   - Context Efficiency (token_ratio vs Vanilla)
"""
import re
import logging
import numpy as np

logger = logging.getLogger(__name__)


def compute_ccr(cqs: list, ontology_ttl: str, llm_client) -> float:
    """CQ Coverage Rate: fraction of CQs answerable from ontology."""
    if not cqs or not ontology_ttl.strip():
        return 0.0
    onto_snippet = ontology_ttl[:3000]
    covered = 0
    for cq in cqs:
        q_text = cq["question"] if isinstance(cq, dict) else cq
        prompt = (
            "Does the OWL ontology below contain sufficient classes, properties, "
            "and axioms to answer this Competency Question?\n\n"
            f"ONTOLOGY (partial):\n```turtle\n{onto_snippet}\n```\n\n"
            f"CQ: {q_text}\n\n"
            "Answer YES if the ontology covers this CQ, NO if axioms are missing.\n"
            "First line: YES or NO."
        )
        try:
            resp = llm_client.generate(system="", user=prompt, max_tokens=64)
            if resp.strip().upper().startswith("YES"):
                covered += 1
        except Exception as e:
            logger.warning(f"CCR judge error: {e}")
    return covered / len(cqs)


def compute_oc(ontology_ttl: str) -> bool:
    """OWL Consistency: True if HermiT reasoner finds no inconsistency."""
    from coha.owl_utils import check_consistency
    return check_consistency(ontology_ttl)


def compute_sc(generated_ttl: str, gold_standard_ttl: str) -> dict:
    """
    Structural Completeness vs Gold Standard.
    Returns class_coverage, property_coverage, overall_sc.
    """
    from coha.owl_utils import extract_class_names, extract_property_names
    gen_classes = set(extract_class_names(generated_ttl))
    gold_classes = set(extract_class_names(gold_standard_ttl))
    gen_props = set(extract_property_names(generated_ttl))
    gold_props = set(extract_property_names(gold_standard_ttl))

    class_coverage = len(gen_classes & gold_classes) / max(len(gold_classes), 1)
    prop_coverage = len(gen_props & gold_props) / max(len(gold_props), 1)
    overall_sc = (class_coverage + prop_coverage) / 2

    return {
        "class_coverage": round(class_coverage, 4),
        "property_coverage": round(prop_coverage, 4),
        "sc": round(overall_sc, 4),
        "n_classes_generated": len(gen_classes),
        "n_classes_gold": len(gold_classes),
        "n_props_generated": len(gen_props),
        "n_props_gold": len(gold_props),
    }


def compute_qic(qic_data: list) -> list:
    """
    Quality Improvement Curve: list of (k, cq_text, n_classes_accumulated) tuples.
    Structural quality proxy — cumulative class count at each CQ step k.
    True CCR-based QIC would require O(n²) LLM judge calls; structural proxy
    is computable without additional LLM calls and shows the same trend.
    """
    return qic_data  # pre-computed in harness as (k, cq_text, n_classes)


def compute_rar(rar_data: list) -> dict:
    """Rule Accumulation Rate statistics."""
    if not rar_data:
        return {"mean_rar": 0.0, "total_rules_added": 0, "rar_per_cq": []}
    values = [v for _, v in rar_data]
    return {
        "mean_rar": float(np.mean(values)),
        "total_rules_added": int(sum(values)),
        "rar_per_cq": rar_data,
    }


def compute_drc(ccr_full: float, ccr_fq_only: float) -> float:
    """Domain Rule Contribution: CCR improvement from DK Rules."""
    return round(ccr_full - ccr_fq_only, 4)


def compute_frc(oc_full: float, oc_dk_only: float) -> float:
    """Formal Rule Contribution: OC improvement from FQ Rules."""
    full_val = 1.0 if oc_full else 0.0
    dk_val = 1.0 if oc_dk_only else 0.0
    return round(full_val - dk_val, 4)


def compute_go(gate_times: list, total_times: list) -> float:
    """Gate Overhead: mean(gate_time / total_time)."""
    if not gate_times or not total_times:
        return 0.0
    n = min(len(gate_times), len(total_times))
    overheads = [min(1.0, gate_times[i] / max(total_times[i], 1)) for i in range(n)]
    return float(np.mean(overheads))


def compute_ce(total_times_coha: list, total_times_vanilla: list) -> float:
    """Context Efficiency: proxy via total latency ratio (vanilla / coha)."""
    if not total_times_coha or not total_times_vanilla:
        return 1.0
    return float(np.sum(total_times_vanilla) / max(np.sum(total_times_coha), 1))
