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


def _save_single_result(name: str, metrics: dict, harness_result: dict, results_dir: str, cache_dir: str):
    """Save one variant's metrics to <name>_exp.json and TTL to cache/."""
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    safe = _safe_filename(name)
    json_path = os.path.join(results_dir, f"{safe}_exp.json")
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "variant": name,
        "results": {kk: vv for kk, vv in metrics.items() if kk != "qic_data"},
    }
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  [Saved] {json_path}")

    ttl = harness_result.get("ontology_ttl", "")
    if ttl:
        ttl_path = os.path.join(cache_dir, f"{safe}_ontology.ttl")
        with open(ttl_path, "w") as f:
            f.write(ttl)
        print(f"  [Saved] {ttl_path}")


def run_single_variant(variant_name: str, save_results: bool = True) -> dict:
    """Run a single named variant and save <VariantName>_exp.json + .ttl."""
    from config import RESULTS_DIR, CACHE_DIR
    from llm_client import get_client
    from domain.military_cq_benchmark import ALL_CQS, GOLD_STANDARD_TTL, USER_STORY
    from domain.military_docs import DOMAIN_DOCS
    from evaluation.evaluator import COHAEvaluator

    print("\n" + "=" * 60)
    print(f"COHA Single-Variant Experiment: {variant_name}")
    print("=" * 60 + "\n")

    client = get_client()
    evaluator = COHAEvaluator(client, ALL_CQS, GOLD_STANDARD_TTL)

    all_variants = dict(_build_variants(client, ALL_CQS, USER_STORY, DOMAIN_DOCS))
    if variant_name not in all_variants:
        raise ValueError(
            f"Unknown variant '{variant_name}'. Valid choices: {list(all_variants)}"
        )

    print(f"[Run] {variant_name}...")
    result = all_variants[variant_name]()
    metrics = evaluator.evaluate(result, variant_name)
    print(
        f"  CCR={metrics.get('ccr', 0):.2%}, "
        f"OC={metrics.get('oc')}, "
        f"SC={metrics.get('sc', {}).get('sc', 0):.2%}, "
        f"sparql_ccr={metrics.get('sparql_ccr', 0):.2%}"
    )

    if save_results:
        _save_single_result(variant_name, metrics, result, RESULTS_DIR, CACHE_DIR)

    return {variant_name: metrics}


def run_main_experiment(save_results: bool = True) -> dict:
    """Run main comparison experiment (all variants)."""
    from config import RESULTS_DIR, CACHE_DIR
    from llm_client import get_client
    from domain.military_cq_benchmark import ALL_CQS, GOLD_STANDARD_TTL, USER_STORY
    from domain.military_docs import DOMAIN_DOCS
    from evaluation.evaluator import COHAEvaluator

    print("\n" + "=" * 60)
    print("COHA Main Experiment: All Variants vs Baselines")
    print("=" * 60 + "\n")

    client = get_client()
    evaluator = COHAEvaluator(client, ALL_CQS, GOLD_STANDARD_TTL)

    # All 10 automated baselines + 6 COHA ablation conditions (paper §4.3, §4.5)
    # B11 (Human Expert) is not automated — evaluated offline against Gold Standard
    variants = _build_variants(client, ALL_CQS, USER_STORY, DOMAIN_DOCS)

    all_results = {}
    harness_results = {}

    for name, run_fn in variants:
        print(f"\n[Main] Running {name}...")
        try:
            result = run_fn()
            harness_results[name] = result
            metrics = evaluator.evaluate(result, name)
            all_results[name] = metrics
            print(
                f"  {name}: CCR={metrics.get('ccr', 0):.2%}, "
                f"OC={metrics.get('oc')}, "
                f"SC={metrics.get('sc', {}).get('sc', 0):.2%}"
            )
        except Exception as e:
            logger.error(f"{name} failed: {e}", exc_info=True)
            all_results[name] = {"variant": name, "error": str(e)}

    # Compute DRC and FRC
    from evaluation.metrics import compute_drc, compute_frc
    if "COHA-full" in all_results and "COHA-no-DK" in all_results:
        drc = compute_drc(
            all_results["COHA-full"].get("ccr", 0),
            all_results["COHA-no-DK"].get("ccr", 0),
        )
        all_results["COHA-full"]["drc"] = drc
        print(f"\n[DRC] Domain Rule Contribution: {drc:+.2%}")
    if "COHA-full" in all_results and "COHA-no-FQ" in all_results:
        frc = compute_frc(
            all_results["COHA-full"].get("oc", False),
            all_results["COHA-no-FQ"].get("oc", False),
        )
        all_results["COHA-full"]["frc"] = frc
        print(f"[FRC] Formal Rule Contribution: {frc:+.2f}")

    # Print comparison table
    try:
        df = evaluator.compare_all(all_results)
        print(f"\n{'=' * 60}\nRESULTS\n{'=' * 60}")
        print(df.to_string())
    except Exception as e:
        logger.warning(f"Table generation failed: {e}")

    # Print Ontogenia-style token efficiency table
    try:
        ce_df = evaluator.compute_ce_table(all_results)
        if not ce_df.empty:
            print(f"\n{'=' * 60}\nCONTEXT EFFICIENCY (Ontogenia-style token tracking)\n{'=' * 60}")
            print(ce_df.to_string())
    except Exception as e:
        logger.warning(f"CE table generation failed: {e}")

    # Save results
    if save_results:
        # Per-variant JSON + TTL files
        for name, metrics in all_results.items():
            if "error" not in metrics:
                _save_single_result(name, metrics, harness_results.get(name, {}), RESULTS_DIR, CACHE_DIR)

        # Consolidated main_results.json (full run summary)
        os.makedirs(RESULTS_DIR, exist_ok=True)
        save_path = os.path.join(RESULTS_DIR, "main_results.json")
        output = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "n_cqs": len(ALL_CQS),
            "results": {
                k: {kk: vv for kk, vv in v.items() if kk not in ("qic_data",)}
                for k, v in all_results.items()
            },
        }
        with open(save_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\n[Results] Full summary → {save_path}")

    return all_results
