"""
Main Experiment: COHA-full vs all baselines (Vanilla, Static Gate).
Evaluates all variants on the 60-CQ military benchmark.
"""
import os
import json
import time
import logging

logger = logging.getLogger(__name__)

VARIANT_KEYS = [
    "B1-WholeOntology",
    "B2-Vanilla-CQbyCQ",
    "B3-Memoryless",
    "B4-Ontogenia",
    "B5-OntoGPT",
    "B5-SPIRES",
    "B7-Static-Gate",
    "COHA-no-reset",
    "COHA-no-FQ",
    "COHA-no-DK",
    "COHA-full",
    "COHA+Ontogenia",
    "COHA+OntoGPT",
]


def _safe_filename(name: str) -> str:
    """Convert variant name to a filesystem-safe string (e.g. 'COHA-full' → 'COHA_full')."""
    return name.replace("+", "_plus_").replace("-", "_").replace(" ", "_")


def _make_coha_ontogpt(client, ALL_CQS, USER_STORY, DOMAIN_DOCS):
    """Return a zero-argument callable for the COHA+OntoGPT variant.

    OntoGPT runs first (single-pass schema extraction) to produce a seed TTL.
    COHA-full then iterates over all 60 CQs starting from that warm ontology.
    """
    from baselines.ontogpt_agent import OntoGPTAgent
    from coha.harness import COHAHarness, HarnessConfig

    def _run():
        print("  [COHA+OntoGPT] Phase 1: OntoGPT seed extraction...")
        base = OntoGPTAgent(client).run(ALL_CQS, USER_STORY, DOMAIN_DOCS)
        seed_ttl = base.get("ontology_ttl", "")
        print(f"  [COHA+OntoGPT] Phase 2: COHA-full warm start from {len(seed_ttl)} chars of seed TTL.")
        config = HarnessConfig.coha_ontogpt(seed_ttl=seed_ttl)
        return COHAHarness(client, config, domain_docs=DOMAIN_DOCS).run(ALL_CQS, USER_STORY)

    return _run


def _build_variants(client, ALL_CQS, USER_STORY, DOMAIN_DOCS):
    """Return the full ordered list of (name, run_fn) pairs."""
    from coha.harness import COHAHarness, HarnessConfig
    from baselines.whole_ontology_prompting import WholeOntologyPrompting
    from baselines.vanilla_cqbycq import VanillaCQbyCQ
    from baselines.memoryless_cqbycq import MemorylessCQbyCQ
    from baselines.ontogenia_agent import OntoGeniaAgent
    from baselines.ontogpt_agent import OntoGPTAgent
    from baselines.spires_agent import SPIRESAgent
    from baselines.static_gate_cqbycq import StaticGateCQbyCQ

    return [
        ("B1-WholeOntology",  lambda: WholeOntologyPrompting(client).run(ALL_CQS, USER_STORY, DOMAIN_DOCS)),
        ("B3-Memoryless",     lambda: MemorylessCQbyCQ(client).run(ALL_CQS, USER_STORY)),
        ("B4-Ontogenia",      lambda: OntoGeniaAgent(client).run(ALL_CQS, USER_STORY)),
        ("B5-OntoGPT",        lambda: OntoGPTAgent(client).run(ALL_CQS, USER_STORY, DOMAIN_DOCS)),
        ("B5-SPIRES",         lambda: SPIRESAgent(client).run(ALL_CQS, USER_STORY, DOMAIN_DOCS)),
        ("B2-Vanilla-CQbyCQ", lambda: VanillaCQbyCQ(client).run(ALL_CQS, USER_STORY)),
        ("B7-Static-Gate",    lambda: StaticGateCQbyCQ(client).run(ALL_CQS, USER_STORY)),
        ("COHA-no-reset",     lambda: COHAHarness(client, HarnessConfig.coha_no_reset(), domain_docs=DOMAIN_DOCS).run(ALL_CQS, USER_STORY)),
        ("COHA-no-FQ",        lambda: COHAHarness(client, HarnessConfig.coha_no_fq(), domain_docs=DOMAIN_DOCS).run(ALL_CQS, USER_STORY)),
        ("COHA-no-DK",        lambda: COHAHarness(client, HarnessConfig.coha_no_dk(), domain_docs=DOMAIN_DOCS).run(ALL_CQS, USER_STORY)),
        ("COHA-full",         lambda: COHAHarness(client, HarnessConfig.coha_full(), domain_docs=DOMAIN_DOCS).run(ALL_CQS, USER_STORY)),
        ("COHA+Ontogenia",    lambda: COHAHarness(client, HarnessConfig.coha_ontogenia(), domain_docs=DOMAIN_DOCS).run(ALL_CQS, USER_STORY)),
        ("COHA+OntoGPT",      _make_coha_ontogpt(client, ALL_CQS, USER_STORY, DOMAIN_DOCS)),
    ]


_HARNESS_META_KEYS = (
    "rar_data", "gate_times", "total_times", "usage_stats",
    "final_fq_rules", "final_dk_rules", "n_retries_total", "qic_data",
)


def save_harness_outputs(name: str, harness_result: dict, cache_dir: str) -> str:
    """Save TTL and harness metadata (no evaluation metrics) to cache/.

    Returns the TTL file path (empty string if no TTL).
    Harness metadata is saved as {safe}_harness_meta.json — used by run_test.py
    to reconstruct harness context (rar_data, gate_times, etc.) during evaluation.
    """
    os.makedirs(cache_dir, exist_ok=True)
    safe = _safe_filename(name)

    ttl = harness_result.get("ontology_ttl", "")
    ttl_path = ""
    if ttl:
        ttl_path = os.path.join(cache_dir, f"{safe}_ontology.ttl")
        with open(ttl_path, "w", encoding="utf-8") as f:
            f.write(ttl)
        print(f"  [Saved] {ttl_path}")

    meta = {k: harness_result.get(k, [] if k != "usage_stats" else {})
            for k in _HARNESS_META_KEYS}
    meta["variant"] = name
    meta["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    meta_path = os.path.join(cache_dir, f"{safe}_harness_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"  [Saved] {meta_path}")

    return ttl_path


def load_harness_result(name: str, cache_dir: str, ttl_override: str = "") -> dict:
    """Load TTL + harness metadata from cache/ and reconstruct a harness result dict.

    If ttl_override is given (e.g. a repaired/synonym-merged TTL path), that TTL
    is used instead of the cached one — allowing the pipeline:
      run_experiments → repair_ttl → merge_synonyms → run_test
    """
    safe = _safe_filename(name)

    if ttl_override:
        ttl_path = ttl_override
    else:
        ttl_path = os.path.join(cache_dir, f"{safe}_ontology.ttl")

    ttl = ""
    if os.path.isfile(ttl_path):
        with open(ttl_path, encoding="utf-8") as f:
            ttl = f.read()
    else:
        logger.warning("TTL not found: %s", ttl_path)

    meta_path = os.path.join(cache_dir, f"{safe}_harness_meta.json")
    meta: dict = {}
    if os.path.isfile(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

    return {
        "ontology_ttl": ttl,
        "rar_data": meta.get("rar_data", []),
        "gate_times": meta.get("gate_times", []),
        "total_times": meta.get("total_times", []),
        "usage_stats": meta.get("usage_stats", {}),
        "final_fq_rules": meta.get("final_fq_rules", []),
        "final_dk_rules": meta.get("final_dk_rules", []),
        "n_retries_total": meta.get("n_retries_total", 0),
        "qic_data": meta.get("qic_data", []),
    }


def save_eval_result(name: str, metrics: dict, results_dir: str):
    """Save evaluation metrics to <name>_exp.json."""
    os.makedirs(results_dir, exist_ok=True)
    safe = _safe_filename(name)
    json_path = os.path.join(results_dir, f"{safe}_exp.json")
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "variant": name,
        "results": {kk: vv for kk, vv in metrics.items() if kk != "qic_data"},
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"  [Saved] {json_path}")


def run_single_variant(variant_name: str, save_results: bool = True, evaluate: bool = False) -> dict:
    """Run a single named variant, save TTL + harness metadata to cache/.

    evaluate=False (default): only generate ontology, skip evaluation.
    evaluate=True: also run evaluator and save metrics to results/.
    """
    from config import RESULTS_DIR, CACHE_DIR
    from llm_client import get_client
    from domain.military_cq_benchmark import ALL_CQS, GOLD_STANDARD_TTL, USER_STORY
    from domain.military_docs import DOMAIN_DOCS

    print("\n" + "=" * 60)
    print(f"COHA Single-Variant Experiment: {variant_name}")
    print("=" * 60 + "\n")

    client = get_client()
    all_variants = dict(_build_variants(client, ALL_CQS, USER_STORY, DOMAIN_DOCS))
    if variant_name not in all_variants:
        raise ValueError(
            f"Unknown variant '{variant_name}'. Valid choices: {list(all_variants)}"
        )

    print(f"[Run] {variant_name}...")
    result = all_variants[variant_name]()

    if save_results:
        save_harness_outputs(variant_name, result, CACHE_DIR)

    if evaluate:
        from evaluation.evaluator import COHAEvaluator
        evaluator = COHAEvaluator(client, ALL_CQS, GOLD_STANDARD_TTL)
        metrics = evaluator.evaluate(result, variant_name)
        print(
            f"  CCR={metrics.get('ccr', 0):.2%}, "
            f"OC={metrics.get('oc')}, "
            f"SC={metrics.get('sc', {}).get('sc', 0):.2%}, "
            f"sparql_ccr={metrics.get('sparql_ccr', 0):.2%}"
        )
        if save_results:
            save_eval_result(variant_name, metrics, RESULTS_DIR)
        return {variant_name: metrics}

    return {variant_name: {"ontology_ttl": result.get("ontology_ttl", "")}}


def run_main_experiment(save_results: bool = True, evaluate: bool = False) -> dict:
    """Run main comparison experiment (all variants), saving TTL + harness metadata.

    evaluate=False (default): only generate ontologies, skip evaluation.
    evaluate=True: also run evaluator and save metrics.
    """
    from config import RESULTS_DIR, CACHE_DIR
    from llm_client import get_client
    from domain.military_cq_benchmark import ALL_CQS, GOLD_STANDARD_TTL, USER_STORY
    from domain.military_docs import DOMAIN_DOCS

    print("\n" + "=" * 60)
    print("COHA Main Experiment: All Variants vs Baselines")
    print("=" * 60 + "\n")

    client = get_client()
    variants = _build_variants(client, ALL_CQS, USER_STORY, DOMAIN_DOCS)

    all_results = {}
    harness_results = {}

    for name, run_fn in variants:
        print(f"\n[Main] Running {name}...")
        try:
            result = run_fn()
            harness_results[name] = result
            all_results[name] = {"variant": name}
            if save_results:
                save_harness_outputs(name, result, CACHE_DIR)
        except Exception as e:
            logger.error(f"{name} failed: {e}", exc_info=True)
            all_results[name] = {"variant": name, "error": str(e)}

    if not evaluate:
        return all_results

    # Evaluation phase (only when evaluate=True)
    from evaluation.evaluator import COHAEvaluator
    from evaluation.metrics import compute_drc, compute_frc
    evaluator = COHAEvaluator(client, ALL_CQS, GOLD_STANDARD_TTL)

    eval_results = {}
    for name, result in harness_results.items():
        print(f"\n[Eval] Evaluating {name}...")
        try:
            metrics = evaluator.evaluate(result, name)
            eval_results[name] = metrics
            print(
                f"  {name}: CCR={metrics.get('ccr', 0):.2%}, "
                f"OC={metrics.get('oc')}, "
                f"SC={metrics.get('sc', {}).get('sc', 0):.2%}"
            )
        except Exception as e:
            logger.error(f"Eval {name} failed: {e}", exc_info=True)
            eval_results[name] = {"variant": name, "error": str(e)}

    # DRC / FRC
    if "COHA-full" in eval_results and "COHA-no-DK" in eval_results:
        drc = compute_drc(
            eval_results["COHA-full"].get("ccr", 0),
            eval_results["COHA-no-DK"].get("ccr", 0),
        )
        eval_results["COHA-full"]["drc"] = drc
        print(f"\n[DRC] Domain Rule Contribution: {drc:+.2%}")
    if "COHA-full" in eval_results and "COHA-no-FQ" in eval_results:
        frc = compute_frc(
            eval_results["COHA-full"].get("oc", False),
            eval_results["COHA-no-FQ"].get("oc", False),
        )
        eval_results["COHA-full"]["frc"] = frc
        print(f"[FRC] Formal Rule Contribution: {frc:+.2f}")

    try:
        df = evaluator.compare_all(eval_results)
        print(f"\n{'=' * 60}\nRESULTS\n{'=' * 60}")
        print(df.to_string())
    except Exception as e:
        logger.warning(f"Table generation failed: {e}")

    try:
        ce_df = evaluator.compute_ce_table(eval_results)
        if not ce_df.empty:
            print(f"\n{'=' * 60}\nCONTEXT EFFICIENCY\n{'=' * 60}")
            print(ce_df.to_string())
    except Exception as e:
        logger.warning(f"CE table failed: {e}")

    if save_results:
        for name, metrics in eval_results.items():
            if "error" not in metrics:
                save_eval_result(name, metrics, RESULTS_DIR)
        os.makedirs(RESULTS_DIR, exist_ok=True)
        save_path = os.path.join(RESULTS_DIR, "main_results.json")
        output = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "n_cqs": len(ALL_CQS),
            "results": {
                k: {kk: vv for kk, vv in v.items() if kk not in ("qic_data",)}
                for k, v in eval_results.items()
            },
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"\n[Results] Full summary → {save_path}")

    return eval_results
