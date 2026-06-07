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
            compute_rar, compute_go,
        )
        from coha.owl_utils import extract_structural_metrics

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

        return {
            "variant": variant_name,
            "ccr": round(ccr, 4),
            "oc": oc,
            "sc": sc,
            "rar": rar,
            "go": round(go, 4),
            "structural": struct,
            "n_fq_rules": len(harness_result.get("final_fq_rules", [])),
            "n_dk_rules": len(harness_result.get("final_dk_rules", [])),
            "n_retries": harness_result.get("n_retries_total", 0),
            "qic_data": harness_result.get("qic_data", []),
        }

    def compare_all(self, results: dict) -> pd.DataFrame:
        """Create comparison DataFrame for all variants."""
        rows = []
        for name, m in results.items():
            rows.append({
                "Variant": name,
                "CCR up": f"{m.get('ccr', 0):.2%}",
                "OC up": "Y" if m.get("oc") else "N",
                "SC up": f"{m.get('sc', {}).get('sc', 0):.2%}",
                "GO down": f"{m.get('go', 0):.2%}",
                "FQ Rules": m.get("n_fq_rules", 0),
                "DK Rules": m.get("n_dk_rules", 0),
                "Retries": m.get("n_retries", 0),
            })
        df = pd.DataFrame(rows).set_index("Variant") if rows else pd.DataFrame()
        return df
