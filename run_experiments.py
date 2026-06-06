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

    args = parser.parse_args()

    # Override config.MODEL_NAME if --model is provided
    if args.model is not None:
        import config as _config
        _config.MODEL_NAME = args.model

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
            try:
                print(f"\n--- Running Main Experiment ({domain}) ---")
                main_res = run_main_experiment(domain, save_results=save)
                domain_results["main"] = main_res
            except Exception as e:
                logging.error(f"Main experiment failed for {domain}: {e}", exc_info=True)
                domain_results["main"] = {"error": str(e)}

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

        if "main" in results and isinstance(results["main"], dict) and "error" not in results["main"]:
            main_res = results["main"]
            # Find COHA-Full vs best baseline
            if "COHA-Full" in main_res:
                coha_cvr = main_res["COHA-Full"].get("cvr", "N/A")
                coha_tsr = main_res["COHA-Full"].get("tsr", "N/A")
                print(f"  COHA-Full:    CVR={coha_cvr:.2%}, TSR={coha_tsr:.2%}" if isinstance(coha_cvr, float) else f"  COHA-Full:    CVR={coha_cvr}, TSR={coha_tsr}")

            if "VanillaAgent" in main_res:
                v_cvr = main_res["VanillaAgent"].get("cvr", "N/A")
                v_tsr = main_res["VanillaAgent"].get("tsr", "N/A")
                print(f"  VanillaAgent: CVR={v_cvr:.2%}, TSR={v_tsr:.2%}" if isinstance(v_cvr, float) else f"  VanillaAgent: CVR={v_cvr}, TSR={v_tsr}")

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
