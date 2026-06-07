"""
Evaluation Metrics for COHA.

Implements the four primary agent performance metrics and three efficiency metrics:

Agent Performance:
- CVR (Constraint Violation Rate): fraction of responses that violate constraints
- TSR (Task Success Rate): fraction of responses that correctly answer the query
- HR (Hallucination Rate): fraction of responses with hallucinated content
- RF (Reasoning Faithfulness): mean faithfulness score against ontology-grounded facts

Ontology Quality:
- CQ Coverage Rate: fraction of CQs answerable from the ontology

Efficiency:
- Gate Overhead (GO): ratio of gate time to total response time
- MSC (Multi-session Consistency): consistency across context resets
"""

import re as _re
import time
import logging
import numpy as np

from llm_client import UnifiedLLMClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM Judge helper
# ---------------------------------------------------------------------------

def _llm_judge(
    llm_client: UnifiedLLMClient,
    prompt: str,
    expected_first_word: str = "YES",
    max_retries: int = 3,
) -> bool:
    """
    Binary LLM judge — returns True if first word of response matches expected.

    Args:
        llm_client: UnifiedLLMClient instance.
        prompt: Judge prompt string.
        expected_first_word: Expected first word in response ("YES" or "NO").
        max_retries: Number of retry attempts.

    Returns:
        True if response matches expected_first_word.
    """
    try:
        text = llm_client.generate(system="", user=prompt, max_tokens=64).upper()
        return text.startswith(expected_first_word.upper())
    except RuntimeError as e:
        logger.warning(f"LLM judge call failed: {e}")
        return False


def _llm_score(
    llm_client: UnifiedLLMClient,
    prompt: str,
    max_retries: int = 3,
) -> float:
    """
    Scalar LLM scorer — extracts a 0-1 float score from LLM response.

    Args:
        llm_client: UnifiedLLMClient instance.
        prompt: Scoring prompt.
        max_retries: Number of retry attempts.

    Returns:
        Score in [0, 1].
    """
    try:
        text = llm_client.generate(system="", user=prompt, max_tokens=64).strip()
        # Extract a number from the response
        numbers = _re.findall(r"\d+\.?\d*", text)
        if numbers:
            score = float(numbers[0])
            # Normalize if score is on a different scale
            if score > 1.0:
                score = score / 10.0 if score <= 10.0 else score / 100.0
            return min(1.0, max(0.0, score))
        # Try to infer from YES/NO
        if "YES" in text.upper() or "HIGH" in text.upper():
            return 1.0
        if "NO" in text.upper() or "LOW" in text.upper():
            return 0.0
        return 0.5
    except RuntimeError as e:
        logger.warning(f"LLM scorer call failed: {e}")
        return 0.5


# ---------------------------------------------------------------------------
# Agent Performance Metrics
# ---------------------------------------------------------------------------

def compute_cvr(
    responses: list,
    benchmark: list,
    llm_client: UnifiedLLMClient,
) -> float:
    """
    Compute Constraint Violation Rate (CVR).

    For each response, uses an LLM judge to check if it violates any of
    the constraints listed in benchmark[i]["constraint_labels"].

    Args:
        responses: List of response dicts (each has a "response" key).
        benchmark: List of benchmark dicts with "constraint_labels" key.
        llm_client: Anthropic API client.

    Returns:
        CVR ∈ [0, 1]: fraction of responses that violate at least one constraint.
    """
    if not responses or not benchmark:
        return 0.0

    n = min(len(responses), len(benchmark))
    violations = 0

    for i in range(n):
        response_text = responses[i].get("response", "") if isinstance(responses[i], dict) else str(responses[i])
        constraints = benchmark[i].get("constraint_labels", [])

        if not constraints:
            continue

        constraints_str = ", ".join(constraints)
        prompt = (
            f"You are a domain expert evaluating an AI agent's response.\n\n"
            f"CONSTRAINTS that must NOT be violated:\n{constraints_str}\n\n"
            f"AGENT RESPONSE:\n{response_text[:800]}\n\n"
            f"Does this response violate ANY of the listed constraints?\n"
            f"Answer YES if there is a violation, NO if all constraints are satisfied.\n"
            f"Answer with just YES or NO on the first line."
        )

        violated = _llm_judge(llm_client, prompt, expected_first_word="YES")
        if violated:
            violations += 1

    return violations / n if n > 0 else 0.0


def compute_tsr(
    responses: list,
    benchmark: list,
    llm_client: UnifiedLLMClient,
) -> float:
    """
    Compute Task Success Rate (TSR).

    Compares each response to the ground truth answer using an LLM judge.

    Args:
        responses: List of response dicts (each has a "response" key).
        benchmark: List of benchmark dicts with "ground_truth" key.
        llm_client: Anthropic API client.

    Returns:
        TSR ∈ [0, 1]: fraction of responses correctly completing the task.
    """
    if not responses or not benchmark:
        return 0.0

    n = min(len(responses), len(benchmark))
    successes = 0

    for i in range(n):
        response_text = responses[i].get("response", "") if isinstance(responses[i], dict) else str(responses[i])
        ground_truth = benchmark[i].get("ground_truth", "")
        query = benchmark[i].get("query", "")

        if not ground_truth:
            continue

        prompt = (
            f"You are evaluating an AI agent's response for task correctness.\n\n"
            f"QUESTION:\n{query}\n\n"
            f"GROUND TRUTH (correct answer):\n{ground_truth}\n\n"
            f"AGENT RESPONSE:\n{response_text[:800]}\n\n"
            f"Is the agent's response essentially correct and aligned with the ground truth?\n"
            f"Consider partial credit for responses that get the main answer right "
            f"but miss some details.\n"
            f"Answer YES if substantially correct, NO if incorrect or misleading.\n"
            f"Answer with just YES or NO on the first line."
        )

        correct = _llm_judge(llm_client, prompt, expected_first_word="YES")
        if correct:
            successes += 1

    return successes / n if n > 0 else 0.0


def compute_hr(
    responses: list,
    benchmark: list,
    llm_client: UnifiedLLMClient,
) -> float:
    """
    Compute Hallucination Rate (HR).

    Checks whether each response contains hallucinated content: invented
    entities, impossible values, or factually incorrect domain claims.

    Args:
        responses: List of response dicts (each has a "response" key).
        benchmark: List of benchmark dicts with "query" and "ground_truth" keys.
        llm_client: Anthropic API client.

    Returns:
        HR ∈ [0, 1]: fraction of responses containing hallucinations.
    """
    if not responses or not benchmark:
        return 0.0

    n = min(len(responses), len(benchmark))
    hallucinated = 0

    for i in range(n):
        response_text = responses[i].get("response", "") if isinstance(responses[i], dict) else str(responses[i])
        query = benchmark[i].get("query", "")
        ground_truth = benchmark[i].get("ground_truth", "")

        prompt = (
            f"You are a hallucination detector for AI agent responses.\n\n"
            f"QUESTION:\n{query}\n\n"
            f"CORRECT CONTEXT:\n{ground_truth[:400]}\n\n"
            f"AGENT RESPONSE:\n{response_text[:800]}\n\n"
            f"Does the agent's response contain hallucinations? Hallucinations include:\n"
            f"- Invented entity names, IDs, or values not mentioned in the question\n"
            f"- Numerically impossible states (e.g., temperature -500°C)\n"
            f"- Contradictions with the question's stated facts\n"
            f"- Fabricated rules or constraints not present in the question\n\n"
            f"Answer YES if hallucinations are present, NO if the response is grounded.\n"
            f"Answer with just YES or NO on the first line."
        )

        has_hallucination = _llm_judge(llm_client, prompt, expected_first_word="YES")
        if has_hallucination:
            hallucinated += 1

    return hallucinated / n if n > 0 else 0.0


def compute_rf(
    responses: list,
    ontology_ttl: str,
    llm_client: UnifiedLLMClient,
) -> float:
    """
    Compute Reasoning Faithfulness (RF).

    Checks each response for alignment with ontology-grounded facts.
    Returns mean faithfulness score in [0, 1].

    Args:
        responses: List of response dicts (each has a "response" key).
        ontology_ttl: OWL ontology in Turtle format.
        llm_client: Anthropic API client.

    Returns:
        RF ∈ [0, 1]: mean faithfulness score.
    """
    if not responses:
        return 0.0

    # Use a summary of the ontology (truncated for prompt length)
    onto_summary = ontology_ttl[:2000]

    scores = []
    for resp in responses:
        response_text = resp.get("response", "") if isinstance(resp, dict) else str(resp)

        if not response_text.strip():
            scores.append(0.0)
            continue

        prompt = (
            f"You are evaluating whether an AI agent's response is faithful to "
            f"an OWL ontology.\n\n"
            f"ONTOLOGY (Turtle format, partial):\n```\n{onto_summary}\n```\n\n"
            f"AGENT RESPONSE:\n{response_text[:600]}\n\n"
            f"Rate the faithfulness of the response to the ontology on a scale of "
            f"0 to 10, where:\n"
            f"  10 = Perfectly aligned with ontology entities, relationships, and constraints\n"
            f"  5 = Partially faithful; some ontology terms used but inconsistencies present\n"
            f"  0 = Completely ignores ontology; invented entities and relationships\n\n"
            f"Answer with just a number from 0 to 10 on the first line."
        )

        score = _llm_score(llm_client, prompt)
        scores.append(score)

    return float(np.mean(scores)) if scores else 0.0


# ---------------------------------------------------------------------------
# Ontology Quality Metrics
# ---------------------------------------------------------------------------

def compute_cq_coverage_rate(
    cqs: list,
    ontology_ttl: str,
    llm_client: UnifiedLLMClient,
) -> float:
    """
    Compute CQ Coverage Rate.

    For each CQ, judges whether the ontology contains sufficient axioms
    to answer it.

    Args:
        cqs: List of Competency Question strings.
        ontology_ttl: OWL ontology in Turtle format.
        llm_client: Anthropic API client.

    Returns:
        Coverage rate ∈ [0, 1].
    """
    if not cqs:
        return 0.0

    covered = 0
    onto_snippet = ontology_ttl[:3000]

    for cq in cqs:
        prompt = (
            f"Does the following OWL ontology contain sufficient classes, properties, "
            f"and axioms to answer this Competency Question?\n\n"
            f"ONTOLOGY:\n```turtle\n{onto_snippet}\n```\n\n"
            f"CQ: {cq}\n\n"
            f"Answer YES if the ontology covers this CQ, NO if it lacks necessary axioms.\n"
            f"Answer with just YES or NO on the first line."
        )

        is_covered = _llm_judge(llm_client, prompt, expected_first_word="YES")
        if is_covered:
            covered += 1

    return covered / len(cqs)


# ---------------------------------------------------------------------------
# Ontology Structural Metrics
# ---------------------------------------------------------------------------

def compute_ontology_structural_metrics(ontology_ttl: str) -> dict:
    """
    Compute structural quality metrics of an OWL ontology from its Turtle source.

    All metrics are derived purely from regex/string parsing — no external
    reasoner required.

    Args:
        ontology_ttl: OWL ontology in Turtle format.

    Returns:
        dict with keys:
          - n_classes            : number of owl:Class declarations
          - n_object_properties  : number of owl:ObjectProperty declarations
          - n_datatype_properties: number of owl:DatatypeProperty declarations
          - n_subclass_axioms    : number of rdfs:subClassOf triples
          - n_disjoint_axioms    : number of owl:disjointWith triples
          - hierarchy_depth      : maximum depth of the subclass hierarchy
          - axiom_density        : (object + datatype properties) / classes
          - subsumption_ratio    : fraction of classes participating in subclass relations
    """
    import re

    # ── Class declarations ───────────────────────────────────────────────
    classes = set(
        m.group(1)
        for m in re.finditer(r"(\S+)\s+a\s+owl:Class", ontology_ttl, re.MULTILINE)
    )
    # Also catch full-URI form: <...> a owl:Class
    uri_classes = re.findall(r"<[^>]+>\s+a\s+owl:Class", ontology_ttl, re.MULTILINE)
    n_classes = max(len(classes), len(uri_classes))

    # ── Property declarations ────────────────────────────────────────────
    n_object_properties = len(set(
        m.group(1)
        for m in re.finditer(r"(\S+)\s+a\s+owl:ObjectProperty", ontology_ttl, re.MULTILINE)
    ))
    n_datatype_properties = len(set(
        m.group(1)
        for m in re.finditer(r"(\S+)\s+a\s+owl:DatatypeProperty", ontology_ttl, re.MULTILINE)
    ))

    # ── Subclass / disjoint axioms ───────────────────────────────────────
    n_subclass_axioms = len(re.findall(r"rdfs:subClassOf", ontology_ttl))
    n_disjoint_axioms = len(re.findall(r"owl:disjointWith", ontology_ttl))

    # ── Hierarchy depth ──────────────────────────────────────────────────
    # Build child→parent map from "X rdfs:subClassOf Y" triples
    parent_map: dict = {}
    for m in re.finditer(r"(\S+)\s+rdfs:subClassOf\s+(\S+)", ontology_ttl, re.MULTILINE):
        child  = m.group(1).rstrip(" .")
        parent = m.group(2).rstrip(" .")
        # Skip owl:Thing and blank nodes
        if parent not in ("owl:Thing", "_:") and not parent.startswith("_:"):
            parent_map[child] = parent

    hierarchy_depth = 0
    for start in parent_map:
        depth, visited, node = 0, set(), start
        while node in parent_map and node not in visited:
            visited.add(node)
            node = parent_map[node]
            depth += 1
        hierarchy_depth = max(hierarchy_depth, depth)

    # ── Derived metrics ──────────────────────────────────────────────────
    n_total_props = n_object_properties + n_datatype_properties
    axiom_density = round(n_total_props / max(n_classes, 1), 3)

    classes_in_hierarchy = set(parent_map.keys()) | set(parent_map.values())
    subsumption_ratio = round(
        min(1.0, len(classes_in_hierarchy) / max(n_classes, 1)), 3
    )

    return {
        "n_classes": n_classes,
        "n_object_properties": n_object_properties,
        "n_datatype_properties": n_datatype_properties,
        "n_subclass_axioms": n_subclass_axioms,
        "n_disjoint_axioms": n_disjoint_axioms,
        "hierarchy_depth": hierarchy_depth,
        "axiom_density": axiom_density,
        "subsumption_ratio": subsumption_ratio,
    }


# ---------------------------------------------------------------------------
# Efficiency Metrics
# ---------------------------------------------------------------------------

def compute_gate_overhead(
    gate_times: list,
    total_times: list,
) -> float:
    """
    Compute Gate Overhead (GO).

    Measures the fraction of total response time spent in gate checks.

    Args:
        gate_times: List of gate check times (ms) per query.
        total_times: List of total response times (ms) per query.

    Returns:
        GO ∈ [0, 1]: mean gate overhead fraction.
    """
    if not gate_times or not total_times:
        return 0.0

    n = min(len(gate_times), len(total_times))
    overheads = []

    for i in range(n):
        total = total_times[i]
        gate = gate_times[i]
        if total > 0:
            overheads.append(min(1.0, gate / total))

    return float(np.mean(overheads)) if overheads else 0.0


def compute_msc(rule_sets: list) -> float:
    """
    Compute Multi-Session Consistency (MSC).

    Measures consistency of harness rule sets across multiple simulated
    context resets. A high MSC indicates stable, reproducible rule compilation.

    Args:
        rule_sets: List of HarnessRuleSet objects from multiple compilations.

    Returns:
        MSC ∈ [0, 1]: mean consistency score.
    """
    if len(rule_sets) < 2:
        return 1.0

    # Compare rule counts across sessions
    rule_counts = [len(rs.rules) for rs in rule_sets]
    mean_count = np.mean(rule_counts)

    if mean_count == 0:
        return 1.0

    # Compute coefficient of variation (lower = more consistent)
    std_count = np.std(rule_counts)
    cv = std_count / mean_count

    # Convert to consistency score (1 - normalized CV)
    # Perfect consistency (cv=0) → MSC=1.0
    # High variation (cv=1) → MSC=0.0
    msc = max(0.0, 1.0 - min(1.0, cv))

    # Also compare rule type distributions across sessions
    from phase2.rule_types import RuleType
    type_consistencies = []

    for rt in RuleType:
        type_counts = [len(rs.get_rules_by_type(rt)) for rs in rule_sets]
        mean_tc = np.mean(type_counts)
        if mean_tc > 0:
            cv_tc = np.std(type_counts) / mean_tc
            type_consistencies.append(max(0.0, 1.0 - min(1.0, cv_tc)))

    if type_consistencies:
        msc = (msc + np.mean(type_consistencies)) / 2.0

    return float(msc)


if __name__ == "__main__":
    from llm_client import get_client
    from domains.smart_building import BENCHMARK_QA, MANUAL_ONTOLOGY_TTL

    client = get_client()

    # Test with synthetic responses
    sample_responses = [
        {"response": "The HVAC should issue INCREASE_COOLING to Zone B-103. Deviation is 6.5°C."},
        {"response": "The temperature anomaly in Zone B-103 requires cooling action."},
        {"response": "Zone temperature is 28.5°C against a setpoint of 22°C."},
    ]

    sample_benchmark = BENCHMARK_QA[:3]

    print("Computing CVR...")
    cvr = compute_cvr(sample_responses, sample_benchmark, client)
    print(f"CVR: {cvr:.2%}")

    print("Computing TSR...")
    tsr = compute_tsr(sample_responses, sample_benchmark, client)
    print(f"TSR: {tsr:.2%}")
