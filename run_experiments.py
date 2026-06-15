"""COHA v2 Experiment Runner.

Examples
--------
# Run all variants (original behaviour)
python run_experiments.py --experiment main

# Run a single variant and get COHA_full_exp.json + COHA_full_ontology.ttl
python run_experiments.py --variant COHA-full
python run_experiments.py --variant COHA-no-DK
python run_experiments.py --variant B7-Static-Gate
"""
import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from experiments.main_experiment import VARIANT_KEYS


def main():
    parser = argparse.ArgumentParser(description="COHA v2 Experiment Runner")
    parser.add_argument(
        "--experiment",
        choices=["main", "ablation", "all"],
        default="all",
        help="Which experiment suite to run (ignored when --variant is set)",
    )
    parser.add_argument(
        "--variant",
        choices=VARIANT_KEYS,
        default=None,
        metavar="VARIANT",
        help=(
            "Run a single variant only and save <VARIANT>_exp.json. "
            f"Choices: {VARIANT_KEYS}"
        ),
    )
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--model", type=str, default=None)
    args = parser.parse_args()

    import config
    if args.model:
        config.MODEL_NAME = args.model

    import os
    if config.MODEL_NAME.startswith("claude") and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    save = not args.no_save

    # Single-variant mode: run one method, save <name>_exp.json + .ttl
    if args.variant:
        from experiments.main_experiment import run_single_variant
        run_single_variant(args.variant, save_results=save)
        return

    # Full suite mode
    if args.experiment in ["main", "all"]:
        from experiments.main_experiment import run_main_experiment
        run_main_experiment(save_results=save)

    if args.experiment in ["ablation", "all"]:
        from experiments.ablation_study import run_ablation_study
        run_ablation_study(save_results=save)


if __name__ == "__main__":
    main()
