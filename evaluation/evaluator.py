"""
COHA Evaluator.

Orchestrates evaluation of all agents and ablation variants across all metrics.
Produces comprehensive comparison tables and saves results to JSON.
"""

import time
import logging
import json
import os
import anthropic
import numpy as np
import pandas as pd

from evaluation.metrics import (
    compute_cvr,
    compute_tsr,
    compute_hr,
    compute_rf,
    compute_cq_coverage_rate,
    compute_gate_overhead,
    compute_msc,
)

logger = logging.getLogger(__name__)


class COHAEvaluator:
    """
    Evaluates COHA agents and baselines across all performance and quality metrics.

    Runs agents over the full benchmark dataset, computes all metrics,
    and produces comparison DataFrames for reporting.
    """

    def __init__(
        self,
        llm_client: anthropic.Anthropic,
        benchmark: list,
        ontology_ttl: str,
    ):
        """
        Initialize the evaluator.

        Args:
            llm_client: Anthropic API client for LLM judge calls.
            benchmark: List of benchmark QA dicts.
            ontology_ttl: OWL ontology in Turtle format.
        """
        self.llm_client = llm_client
        self.benchmark = benchmark
        self.ontology_ttl = ontology_ttl

    def evaluate_agent(self, agent, agent_name: str) -> dict:
        """
        Evaluate an agent over the full benchmark dataset.

        Runs the agent on all benchmark queries, collecting responses and
        timing data, then computes all performance metrics.

        Args:
            agent: Agent instance with a .run(query) method.
            agent_name: Human-readable name for reporting.

        Returns:
            Comprehensive metrics dict with keys:
                agent_name, cvr, tsr, hr, rf,
                gate_overhead, n_violations, n_regenerations,
                mean_latency_ms, all_responses
        """
        logger.info(f"[Evaluator] Evaluating agent: {agent_name}")
        print(f"[Evaluator] Evaluating {agent_name} on {len(self.benchmark)} queries...")

        all_responses = []
        gate_times = []
        total_times = []
        n_violations_total = 0
        n_regen_total = 0
        latencies = []

        for i, qa in enumerate(self.benchmark):
            query = qa.get("query", "")
            if not query:
                continue

            t_start = time.time()
            try:
                result = agent.run(query)
            except Exception as e:
                logger.warning(f"Agent {agent_name} failed on query {i+1}: {e}")
                result = {"response": f"[Agent error: {e}]"}

            total_time_ms = (time.time() - t_start) * 1000
            total_times.append(total_time_ms)

            # Extract response text
            if isinstance(result, dict):
                response_text = result.get("response", "")
                gate_overhead_ms = result.get("gate_overhead_ms", 0.0)
                n_violations = len(result.get("violations", []))
                n_regen = result.get("n_regenerations", 0)
                latency = result.get("latency_ms", total_time_ms)
            else:
                response_text = str(result)
                gate_overhead_ms = 0.0
                n_violations = 0
                n_regen = 0
                latency = total_time_ms

            gate_times.append(gate_overhead_ms)
            n_violations_total += n_violations
            n_regen_total += n_regen
            latencies.append(latency)

            all_responses.append({
                "query": query,
                "response": response_text,
                "gate_overhead_ms": gate_overhead_ms,
                "n_violations": n_violations,
                "n_regenerations": n_regen,
                "latency_ms": latency,
                "task_type": qa.get("task_type", "unknown"),
            })

            if (i + 1) % 5 == 0:
                print(f"  [{agent_name}] Completed {i+1}/{len(self.benchmark)} queries.")

        print(f"[Evaluator] Computing metrics for {agent_name}...")

        # Compute metrics
        cvr = compute_cvr(all_responses, self.benchmark, self.llm_client)
        tsr = compute_tsr(all_responses, self.benchmark, self.llm_client)
        hr = compute_hr(all_responses, self.benchmark, self.llm_client)
        rf = compute_rf(all_responses, self.ontology_ttl, self.llm_client)
        go = compute_gate_overhead(gate_times, total_times)

        metrics = {
            "agent_name": agent_name,
            "cvr": round(cvr, 4),
            "tsr": round(tsr, 4),
            "hr": round(hr, 4),
            "rf": round(rf, 4),
            "gate_overhead": round(go, 4),
            "n_violations_total": n_violations_total,
            "n_regenerations_total": n_regen_total,
            "mean_latency_ms": round(float(np.mean(latencies)), 1) if latencies else 0.0,
            "n_queries": len(all_responses),
            "all_responses": all_responses,
        }

        print(
            f"[Evaluator] {agent_name}: CVR={cvr:.2%}, TSR={tsr:.2%}, "
            f"HR={hr:.2%}, RF={rf:.3f}"
        )

        return metrics

    def evaluate_ontology_quality(self, builder_result: dict) -> dict:
        """
        Evaluate the quality of an automatically built ontology.

        Args:
            builder_result: Output dict from OntologyBuilder.build().

        Returns:
            Dict with ontology quality metrics:
                cq_coverage_rate, is_consistent, n_cqs, n_iterations
        """
        cqs = builder_result.get("cqs", [])
        ontology_ttl = builder_result.get("ontology_ttl", "")
        is_consistent = builder_result.get("is_consistent", False)
        n_iterations = builder_result.get("n_iterations", 0)

        # Recompute CQ coverage rate with the evaluator's LLM client
        if cqs and ontology_ttl:
            cq_coverage = compute_cq_coverage_rate(cqs, ontology_ttl, self.llm_client)
        else:
            cq_coverage = builder_result.get("cq_coverage_rate", 0.0)

        return {
            "cq_coverage_rate": round(cq_coverage, 4),
            "is_consistent": is_consistent,
            "n_cqs": len(cqs),
            "n_iterations": n_iterations,
        }

    def compare_all(self, results: dict) -> pd.DataFrame:
        """
        Create a comparison table across all evaluated agents.

        Args:
            results: Dict mapping agent_name → metrics dict (from evaluate_agent).

        Returns:
            pandas DataFrame with agents as rows and metrics as columns.
        """
        rows = []
        for agent_name, metrics in results.items():
            row = {
                "Agent": agent_name,
                "CVR ↓": f"{metrics.get('cvr', 0):.2%}",
                "TSR ↑": f"{metrics.get('tsr', 0):.2%}",
                "HR ↓": f"{metrics.get('hr', 0):.2%}",
                "RF ↑": f"{metrics.get('rf', 0):.3f}",
                "GO ↓": f"{metrics.get('gate_overhead', 0):.2%}",
                "Latency (ms) ↓": f"{metrics.get('mean_latency_ms', 0):.0f}",
                "# Violations": metrics.get("n_violations_total", 0),
                "# Regen": metrics.get("n_regenerations_total", 0),
            }
            rows.append(row)

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.set_index("Agent")
        return df


if __name__ == "__main__":
    import os
    from domains.smart_building import BENCHMARK_QA, MANUAL_ONTOLOGY_TTL
    from baselines.vanilla_agent import VanillaAgent

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    evaluator = COHAEvaluator(client, BENCHMARK_QA[:3], MANUAL_ONTOLOGY_TTL)

    vanilla = VanillaAgent(client)
    result = evaluator.evaluate_agent(vanilla, "VanillaAgent-Test")
    print(f"CVR: {result['cvr']:.2%}, TSR: {result['tsr']:.2%}, HR: {result['hr']:.2%}")
