"""COHA v2 Experiment Runner."""
import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="COHA v2 Experiment Runner")
    parser.add_argument(
        "--experiment",
        choices=["main", "ablation", "all"],
        default="all",
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

    if args.experiment in ["main", "all"]:
        from experiments.main_experiment import run_main_experiment
        run_main_experiment(save_results=save)

    if args.experiment in ["ablation", "all"]:
        from experiments.ablation_study import run_ablation_study
        run_ablation_study(save_results=save)


if __name__ == "__main__":
    main()
