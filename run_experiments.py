"""
COHA Experiment Runner — Main Entry Point.

Runs COHA experiments across domains and experiment types.
Usage:
  python run_experiments.py [--experiment main|ablation|efficiency|all] [--domain smart_building|military_tactical|both] [--no-save]
"""

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main():
    parser = argparse.ArgumentParser(
        description="COHA Experiment Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_experiments.py --experiment main --domain smart_building
  python run_experiments.py --experiment ablation --domain both
  python run_experiments.py --experiment efficiency --domain military_tactical
  python run_experiments.py --experiment all --domain both
  python run_experiments.py --experiment main --onto-method text2onto --domain smart_building
  python run_experiments.py --experiment main --onto-method all --domain both
        """,
    )
    parser.add_argument(
        "--experiment",
        choices=["main", "ablation", "efficiency", "all"],
        default="all",
        help="Which experiment to run (default: all)",
    )
    parser.add_argument(
        "--domain",
        choices=["smart_building", "military_tactical", "both"],
        default="both",
        help="Which domain(s) to evaluate (default: both)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save results to disk",
    )
    parser.add_argument(
        "--n-queries",
        type=int,
        default=20,
        help="Number of queries for efficiency benchmark (default: 20)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model name (default: config.MODEL_NAME). "
             "Use 'claude-sonnet-4-6' for Anthropic or a HuggingFace model ID.",
    )
    parser.add_argument(
        "--onto-method",
        choices=["cqbycq", "text2onto", "ontogpt", "all"],
        default=None,
        help="Ontology construction method (default: config.ONTOLOGY_METHOD = cqbycq). "
             "cqbycq: iterative CQ-by-CQ loop. "
             "text2onto: multi-pass concept/relation extraction. "
             "ontogpt: single-pass structured schema extraction. "
             "all: run all three methods sequentially and save separate result files.",
    )

    args = parser.parse_args()

    # Override model if provided
    import config as _config
    if args.model is not None:
        _config.MODEL_NAME = args.model

    # Determine which ontology methods to run
    if args.onto_method == "all":
        onto_methods = ["cqbycq", "text2onto", "ontogpt"]
    elif args.onto_method is not None:
        onto_methods = [args.onto_method]
        _config.ONTOLOGY_METHOD = args.onto_method
    else:
        onto_methods = [_config.ONTOLOGY_METHOD]

    # Validate API key only when using Anthropic backend
    import os
    import config as _config_check
    if _config_check.MODEL_NAME.startswith("claude"):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            print(
                "ERROR: ANTHROPIC_API_KEY environment variable is not set.\n"
                "Please export your Anthropic API key:\n"
                "  export ANTHROPIC_API_KEY=your_api_key_here"
            )
            sys.exit(1)

    # Determine domains to run
    if args.domain == "both":
        domains = ["smart_building", "military_tactical"]
    else:
        domains = [args.domain]

    save = not args.no_save

    # Import experiment functions
    from experiments.main_experiment import run_main_experiment
    from experiments.ablation_study import run_ablation_study
    from experiments.efficiency_benchmark import run_efficiency_benchmark

    all_results = {}

    for domain in domains:
        domain_results = {}
        print(f"\n{'#'*70}")
        print(f"# DOMAIN: {domain.upper()}")
        print(f"{'#'*70}")

        if args.experiment in ["main", "all"]:
            for onto_method in onto_methods:
                result_key = f"main_{onto_method}" if len(onto_methods) > 1 else "main"
                try:
                    print(f"\n--- Running Main Experiment ({domain}, method={onto_method}) ---")
                    main_res = run_main_experiment(
                        domain, save_results=save, onto_method=onto_method
                    )
                    domain_results[result_key] = main_res
                except Exception as e:
                    logging.error(
                        f"Main experiment failed for {domain} [{onto_method}]: {e}",
                        exc_info=True,
                    )
                    domain_results[result_key] = {"error": str(e)}

        if args.experiment in ["ablation", "all"]:
            try:
                print(f"\n--- Running Ablation Study ({domain}) ---")
                ablation_res = run_ablation_study(domain, save_results=save)
                domain_results["ablation"] = ablation_res
            except Exception as e:
                logging.error(f"Ablation study failed for {domain}: {e}", exc_info=True)
                domain_results["ablation"] = {"error": str(e)}

        if args.experiment in ["efficiency", "all"]:
            try:
                print(f"\n--- Running Efficiency Benchmark ({domain}) ---")
                eff_res = run_efficiency_benchmark(
                    domain,
                    n_queries=args.n_queries,
                    save_results=save,
                )
                domain_results["efficiency"] = eff_res
            except Exception as e:
                logging.error(f"Efficiency benchmark failed for {domain}: {e}", exc_info=True)
                domain_results["efficiency"] = {"error": str(e)}

        all_results[domain] = domain_results

    # ─── Final Summary ──────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("EXPERIMENT COMPLETE — Summary")
    print(f"{'='*70}")

    for domain, results in all_results.items():
        print(f"\nDomain: {domain}")

        # Collect main-experiment entries: supports both "main" (single) and
        # "main_cqbycq" / "main_text2onto" / "main_ontogpt" (multi-method).
        main_entries = [
            (k, k[len("main_"):] if k.startswith("main_") else onto_methods[0])
            for k in results
            if k == "main" or k.startswith("main_")
        ]
        for result_key, method_label in main_entries:
            main_res = results[result_key]
            if not (isinstance(main_res, dict) and "error" not in main_res):
                continue
            prefix = f"  [{method_label}] " if len(main_entries) > 1 else "  "
            if "COHA-Full" in main_res:
                coha_cvr = main_res["COHA-Full"].get("cvr", "N/A")
                coha_tsr = main_res["COHA-Full"].get("tsr", "N/A")
                print(
                    f"{prefix}COHA-Full:    CVR={coha_cvr:.2%}, TSR={coha_tsr:.2%}"
                    if isinstance(coha_cvr, float)
                    else f"{prefix}COHA-Full:    CVR={coha_cvr}, TSR={coha_tsr}"
                )
            if "VanillaAgent" in main_res:
                v_cvr = main_res["VanillaAgent"].get("cvr", "N/A")
                v_tsr = main_res["VanillaAgent"].get("tsr", "N/A")
                print(
                    f"{prefix}VanillaAgent: CVR={v_cvr:.2%}, TSR={v_tsr:.2%}"
                    if isinstance(v_cvr, float)
                    else f"{prefix}VanillaAgent: CVR={v_cvr}, TSR={v_tsr}"
                )

        if "efficiency" in results and isinstance(results["efficiency"], dict) and "error" not in results["efficiency"]:
            eff = results["efficiency"]
            rct = eff.get("rct", {})
            go = eff.get("go", {})
            msc = eff.get("msc", {})
            print(f"  RCT: {rct.get('mean_ms', 0):.1f} ms | "
                  f"GO: {go.get('mean_go', 0):.1%} | "
                  f"MSC: {msc.get('msc_score', 0):.3f}")

    print("\nAll experiments complete.")
    if save:
        from config import RESULTS_DIR
        print(f"Results saved to: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
