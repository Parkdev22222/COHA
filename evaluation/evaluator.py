"""
COHA Evaluator: orchestrates all experiments and computes all metrics.
"""
import time
import logging
import json
import os
import pandas as pd

logger = logging.getLogger(__name__)


class COHAEvaluator:
    def __init__(self, llm_client, cqs: list, gold_standard_ttl: str):
        self.llm_client = llm_client
        self.cqs = cqs
        self.gold_standard_ttl = gold_standard_ttl

    def evaluate(self, harness_result: dict, variant_name: str) -> dict:
        """Evaluate a single harness run result."""
        from evaluation.metrics import (
            compute_ccr, compute_oc, compute_sc,
            compute_rar, compute_go, compute_des_scaffold,
            compute_sparql_ccr, compute_llm_judge_detailed, compute_overall_score,
            compute_odp_coverage,
        )
        from coha.owl_utils import extract_structural_metrics, extract_deep_structural_metrics

        onto_ttl = harness_result.get("ontology_ttl", "")

        print(f"  [Evaluator] Computing CCR for {variant_name}...")
        ccr = compute_ccr(self.cqs, onto_ttl, self.llm_client)
        oc = compute_oc(onto_ttl)
        sc = compute_sc(onto_ttl, self.gold_standard_ttl)
        rar = compute_rar(harness_result.get("rar_data", []))
        go = compute_go(
            harness_result.get("gate_times", []),
            harness_result.get("total_times", []),
        )
        struct = extract_structural_metrics(onto_ttl)

        print(f"  [Evaluator] Computing deep structural metrics for {variant_name}...")
        deep_struct = extract_deep_structural_metrics(onto_ttl)

        print(f"  [Evaluator] Computing SPARQL CCR for {variant_name}...")
        sparql_ccr = compute_sparql_ccr(self.cqs, onto_ttl, self.llm_client)

        print(f"  [Evaluator] Computing 4-dim LLM judge for {variant_name}...")
        llm_judge = compute_llm_judge_detailed(self.cqs, onto_ttl, self.llm_client)

        overall = compute_overall_score(ccr, oc, deep_struct)
        des = compute_des_scaffold(onto_ttl, self.cqs)

        # Ontogenia-inspired: ODP utilization + token efficiency
        odp = compute_odp_coverage(onto_ttl)
        usage_stats = harness_result.get("usage_stats", {})

        return {
            "variant": variant_name,
            "ccr": round(ccr, 4),
            "sparql_ccr": sparql_ccr["coverage_rate"],
            "oc": oc,
            "sc": sc,
            "llm_judge": {
                "mean_answerability": llm_judge["mean_answerability"],
                "mean_completeness": llm_judge["mean_completeness"],
                "mean_precision": llm_judge["mean_precision"],
                "mean_domain_validity": llm_judge["mean_domain_validity"],
                "mean_overall": llm_judge["mean_overall"],
                "verdicts": llm_judge["verdicts"],
            },
            "overall_score": overall,
            "rar": rar,
            "go": round(go, 4),
            "structural": {**struct, **deep_struct},
            "n_fq_rules": len(harness_result.get("final_fq_rules", [])),
            "n_dk_rules": len(harness_result.get("final_dk_rules", [])),
            "n_retries": harness_result.get("n_retries_total", 0),
            "qic_data": harness_result.get("qic_data", []),
            "des": des,
            "odp_coverage": odp,
            "usage_stats": usage_stats,
        }

    def compare_all(self, results: dict) -> pd.DataFrame:
        """
        Create comparison DataFrame for all variants.

        Columns
        -------
        Quality:     CCR, SPARQL-CCR, OC, SC(fuzzy), SC(exact), Judge, Overall
        Structural:  AvgDepth, Tangles
        COHA-specific: GO (gate overhead), FQ rules, DK rules
        Ontogenia-inspired: ODP↑ (design pattern utilisation), Tokens (total LLM cost)
        """
        rows = []
        for name, m in results.items():
            judge = m.get("llm_judge", {})
            odp = m.get("odp_coverage", {})
            usage = m.get("usage_stats", {})
            rows.append({
                "Variant":       name,
                # ── Quality ──────────────────────────────────────────────
                "CCR↑":          f"{m.get('ccr', 0):.2%}",
                "SPARQL-CCR↑":   f"{m.get('sparql_ccr', 0):.2%}",
                "OC↑":           "Y" if m.get("oc") else "N",
                "SC(fuzzy)↑":    f"{m.get('sc', {}).get('sc', 0):.2%}",
                "SC(exact)↑":    f"{m.get('sc', {}).get('sc_exact', 0):.2%}",
                "Judge(1-5)↑":   f"{judge.get('mean_overall', 0):.2f}",
                "Overall↑":      f"{m.get('overall_score', 0):.3f}",
                # ── Structural ────────────────────────────────────────────
                "AvgDepth↑":     f"{m.get('structural', {}).get('avg_depth', 0):.2f}",
                "Tangles↓":      f"{m.get('structural', {}).get('tangledness', 0):.2%}",
                # ── COHA-specific ─────────────────────────────────────────
                "GO↓":           f"{m.get('go', 0):.2%}",
                "FQ":            m.get("n_fq_rules", 0),
                "DK":            m.get("n_dk_rules", 0),
                # ── Ontogenia-inspired ────────────────────────────────────
                "ODP↑":          f"{odp.get('n_odps_covered', 0)}/{odp.get('n_odps_total', 5)}",
                "Tokens":        usage.get("total_tokens", "-"),
            })
        df = pd.DataFrame(rows).set_index("Variant") if rows else pd.DataFrame()
        return df

    def compute_ce_table(self, results: dict, baseline_name: str = "B2-Vanilla-CQbyCQ") -> pd.DataFrame:
        """
        Context Efficiency table (Ontogenia-style token-efficiency comparison).

        CE = baseline_tokens / variant_tokens  (higher = more token-efficient).
        Requires usage_stats to be populated (i.e. run via COHAHarness, not baselines).
        """
        from evaluation.metrics import compute_ce
        if baseline_name not in results:
            return pd.DataFrame()
        base_usage = results[baseline_name].get("usage_stats", {})
        rows = []
        for name, m in results.items():
            variant_usage = m.get("usage_stats", {})
            ce = compute_ce(variant_usage, base_usage) if variant_usage else None
            rows.append({
                "Variant": name,
                "LLM Calls": variant_usage.get("call_count", "-"),
                "Input Tokens": variant_usage.get("input_tokens", "-"),
                "Output Tokens": variant_usage.get("output_tokens", "-"),
                "Total Tokens": variant_usage.get("total_tokens", "-"),
                f"CE (vs {baseline_name})↑": f"{ce:.3f}" if ce is not None else "-",
            })
        return pd.DataFrame(rows).set_index("Variant") if rows else pd.DataFrame()
