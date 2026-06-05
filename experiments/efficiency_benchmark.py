"""
Efficiency Benchmark.

Measures three efficiency metrics for the COHA system:
  - RCT (Rule Compilation Time): time to compile OWL axioms → harness rules
  - GO  (Gate Overhead): fraction of per-query time spent in gate checks
  - MSC (Multi-Session Consistency): rule set stability across context resets

Results saved to results/{domain}_efficiency_results.json.
"""

import os
import json
import time
import logging
import numpy as np
import anthropic

logger = logging.getLogger(__name__)


def _load_domain_data(domain: str):
    """Load domain data."""
    if domain == "smart_building":
        from domains.smart_building import DOMAIN_DOCS, MANUAL_ONTOLOGY_TTL, BENCHMARK_QA
    elif domain == "military_tactical":
        from domains.military_tactical import DOMAIN_DOCS, MANUAL_ONTOLOGY_TTL, BENCHMARK_QA
    else:
        raise ValueError(f"Unknown domain: {domain}")
    return DOMAIN_DOCS, MANUAL_ONTOLOGY_TTL, BENCHMARK_QA


def _get_ontology_for_domain(domain: str, manual_ttl: str) -> str:
    """Load auto-generated ontology from cache, fall back to manual."""
    from config import CACHE_DIR
    cache_path = os.path.join(CACHE_DIR, f"{domain}_ontology.json")
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            ttl = data.get("ontology_ttl", "")
            if ttl:
                return ttl
    return manual_ttl


def measure_rct(domain: str, ontology_ttl: str, n_trials: int = 10) -> dict:
    """
    Measure Rule Compilation Time (RCT).

    Compiles the harness rules n_trials times and reports statistics.

    Args:
        domain: Domain identifier.
        ontology_ttl: OWL ontology in Turtle format.
        n_trials: Number of compilation trials.

    Returns:
        Dict with mean_ms, std_ms, min_ms, max_ms, n_rules.
    """
    from phase2.harness_compiler import HarnessCompiler

    compiler = HarnessCompiler(domain)
    times_ms = []
    n_rules = 0

    for i in range(n_trials):
        t_start = time.time()
        rule_set = compiler.compile(ontology_ttl)
        elapsed_ms = (time.time() - t_start) * 1000
        times_ms.append(elapsed_ms)
        n_rules = len(rule_set.rules)

    return {
        "mean_ms": float(np.mean(times_ms)),
        "std_ms": float(np.std(times_ms)),
        "min_ms": float(np.min(times_ms)),
        "max_ms": float(np.max(times_ms)),
        "n_rules": n_rules,
        "n_trials": n_trials,
    }


def measure_go(
    client: anthropic.Anthropic,
    domain: str,
    ontology_ttl: str,
    documents: list,
    benchmark_qa: list,
    n_queries: int = 20,
) -> dict:
    """
    Measure Gate Overhead (GO) per query.

    Runs n_queries through the full COHA pipeline, measuring gate check
    time vs total response time.

    Args:
        client: Anthropic API client.
        domain: Domain identifier.
        ontology_ttl: OWL ontology in Turtle format.
        documents: Document list.
        benchmark_qa: Benchmark QA list.
        n_queries: Number of queries to run.

    Returns:
        Dict with mean_go, std_go, mean_gate_ms, mean_total_ms, per_query_data.
    """
    from phase2.harness_compiler import HarnessCompiler
    from phase3.context_assembly import ContextAssembler
    from phase3.agent_runtime import AgentRuntime

    compiler = HarnessCompiler(domain)
    rule_set = compiler.compile(ontology_ttl)

    assembler = ContextAssembler(documents, ontology_ttl, use_ontology_guidance=True)
    assembler.build_index()

    config = {
        "enable_input_gate": True,
        "enable_output_gate": True,
        "enable_phase_gate": True,
        "max_regeneration_attempts": 1,  # Limit regen to speed up benchmark
    }
    runtime = AgentRuntime(client, rule_set, assembler, config)

    queries = [qa["query"] for qa in benchmark_qa[:n_queries]]

    gate_times = []
    total_times = []
    per_query = []

    for i, query in enumerate(queries):
        print(f"  [GO] Query {i+1}/{len(queries)}: {query[:50]}...")
        t_start = time.time()

        try:
            result = runtime.run(query)
            total_ms = (time.time() - t_start) * 1000
            gate_ms = result.get("gate_overhead_ms", 0.0)
        except Exception as e:
            logger.warning(f"Query {i+1} failed: {e}")
            total_ms = (time.time() - t_start) * 1000
            gate_ms = 0.0

        gate_times.append(gate_ms)
        total_times.append(total_ms)
        per_query.append({
            "query_idx": i,
            "gate_ms": gate_ms,
            "total_ms": total_ms,
            "go": gate_ms / total_ms if total_ms > 0 else 0.0,
        })

    from evaluation.metrics import compute_gate_overhead
    go_values = [p["go"] for p in per_query]

    return {
        "mean_go": float(np.mean(go_values)),
        "std_go": float(np.std(go_values)),
        "mean_gate_ms": float(np.mean(gate_times)),
        "mean_total_ms": float(np.mean(total_times)),
        "n_queries": len(queries),
        "per_query_data": per_query,
    }


def measure_msc(
    domain: str,
    ontology_ttl: str,
    n_sessions: int = 5,
) -> dict:
    """
    Measure Multi-Session Consistency (MSC).

    Simulates multiple context resets by recompiling harness rules n_sessions
    times and comparing the resulting rule sets for consistency.

    Args:
        domain: Domain identifier.
        ontology_ttl: OWL ontology in Turtle format.
        n_sessions: Number of simulated sessions.

    Returns:
        Dict with msc_score, rule_counts, mean_rules, std_rules.
    """
    from phase2.harness_compiler import HarnessCompiler
    from evaluation.metrics import compute_msc

    compiler = HarnessCompiler(domain)
    rule_sets = []

    for i in range(n_sessions):
        try:
            rule_set = compiler.compile(ontology_ttl)
            rule_sets.append(rule_set)
        except Exception as e:
            logger.warning(f"Session {i+1} rule compilation failed: {e}")

    if not rule_sets:
        return {"msc_score": 0.0, "rule_counts": [], "mean_rules": 0, "std_rules": 0}

    msc_score = compute_msc(rule_sets)
    rule_counts = [len(rs.rules) for rs in rule_sets]

    return {
        "msc_score": float(msc_score),
        "rule_counts": rule_counts,
        "mean_rules": float(np.mean(rule_counts)),
        "std_rules": float(np.std(rule_counts)),
        "n_sessions": len(rule_sets),
    }


def run_efficiency_benchmark(
    domain: str = "smart_building",
    n_queries: int = 20,
    save_results: bool = True,
) -> dict:
    """
    Run all efficiency benchmarks for a domain.

    Args:
        domain: Domain to benchmark ("smart_building" or "military_tactical").
        n_queries: Number of queries for GO measurement.
        save_results: Whether to save results to JSON.

    Returns:
        Dict with rct, go, and msc sub-dicts.
    """
    from config import ANTHROPIC_API_KEY, RESULTS_DIR

    print(f"\n{'='*60}")
    print(f"COHA Efficiency Benchmark — Domain: {domain}")
    print(f"{'='*60}\n")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    domain_docs, manual_ontology_ttl, benchmark_qa = _load_domain_data(domain)
    ontology_ttl = _get_ontology_for_domain(domain, manual_ontology_ttl)
    documents = [p.strip() for p in domain_docs.split("\n\n") if p.strip() and len(p.strip()) > 50]

    print(f"[Efficiency] Using ontology: {len(ontology_ttl)} chars")

    # ─── RCT: Rule Compilation Time ──────────────────────────────────────
    print("\n[RCT] Measuring Rule Compilation Time (10 trials)...")
    rct_results = measure_rct(domain, ontology_ttl, n_trials=10)
    print(f"  RCT: mean={rct_results['mean_ms']:.2f} ms, "
          f"std={rct_results['std_ms']:.2f} ms, "
          f"rules={rct_results['n_rules']}")

    # ─── GO: Gate Overhead ───────────────────────────────────────────────
    print(f"\n[GO] Measuring Gate Overhead ({n_queries} queries)...")
    go_results = measure_go(
        client, domain, ontology_ttl, documents, benchmark_qa, n_queries=n_queries
    )
    print(f"  GO: mean={go_results['mean_go']:.2%}, "
          f"gate={go_results['mean_gate_ms']:.0f} ms, "
          f"total={go_results['mean_total_ms']:.0f} ms")

    # ─── MSC: Multi-Session Consistency ──────────────────────────────────
    print("\n[MSC] Measuring Multi-Session Consistency (5 sessions)...")
    msc_results = measure_msc(domain, ontology_ttl, n_sessions=5)
    print(f"  MSC: score={msc_results['msc_score']:.3f}, "
          f"mean_rules={msc_results['mean_rules']:.1f}, "
          f"std_rules={msc_results['std_rules']:.2f}")

    # ─── Summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"EFFICIENCY SUMMARY: {domain.upper()}")
    print(f"{'='*60}")
    print(f"  RCT (Rule Compilation Time): {rct_results['mean_ms']:.2f} ± {rct_results['std_ms']:.2f} ms")
    print(f"  GO  (Gate Overhead):         {go_results['mean_go']:.2%} of query time")
    print(f"  MSC (Multi-Session Consist): {msc_results['msc_score']:.3f}")

    results = {
        "domain": domain,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rct": rct_results,
        "go": {k: v for k, v in go_results.items() if k != "per_query_data"},
        "msc": msc_results,
    }

    # ─── Save Results ─────────────────────────────────────────────────────
    if save_results:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        save_path = os.path.join(RESULTS_DIR, f"{domain}_efficiency_results.json")
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\n[Results] Saved to {save_path}")

    return results


if __name__ == "__main__":
    run_efficiency_benchmark("smart_building", n_queries=5)
