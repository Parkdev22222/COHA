"""COHA v2 Experiment Runner — 온톨로지 생성 전용.

생성된 TTL과 harness 메타데이터를 cache/ 에 저장합니다.
평가(성능 측정)는 run_test.py 에서 별도로 수행합니다.

전체 파이프라인:
  1. python run_experiments.py   →  TTL 생성  (cache/ 저장)
  2. python tools/repair_ttl.py  →  TTL 문법 수정
  3. python tools/merge_synonyms.py → 동의어 병합
  4. python run_test.py           →  성능 측정 (results/ 저장)

사용 예
--------
# 특정 variant 하나만 생성
python run_experiments.py --variant COHA-full
python run_experiments.py --variant COHA-no-DK

# 전체 main experiment 생성
python run_experiments.py --experiment main

# ablation study 생성
python run_experiments.py --experiment ablation

# 전체 생성 (main + ablation)
python run_experiments.py --experiment all
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
    parser = argparse.ArgumentParser(
        description="COHA v2 — 온톨로지 생성 실행기 (평가 제외)"
    )
    parser.add_argument(
        "--experiment",
        choices=["main", "ablation", "all"],
        default="all",
        help="실행할 실험 종류 (--variant 설정 시 무시됨)",
    )
    parser.add_argument(
        "--variant",
        choices=VARIANT_KEYS,
        default=None,
        metavar="VARIANT",
        help=f"단일 variant 실행. 선택지: {VARIANT_KEYS}",
    )
    parser.add_argument("--no-save", action="store_true", help="TTL/메타 파일 저장 안 함")
    parser.add_argument("--model", type=str, default=None, help="LLM 모델명 override")
    args = parser.parse_args()

    import config
    if args.model:
        config.MODEL_NAME = args.model

    import os
    if config.MODEL_NAME.startswith("claude") and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    save = not args.no_save

    if args.variant:
        from experiments.main_experiment import run_single_variant
        run_single_variant(args.variant, save_results=save, evaluate=False)
        return

    if args.experiment in ["main", "all"]:
        from experiments.main_experiment import run_main_experiment
        run_main_experiment(save_results=save, evaluate=False)

    if args.experiment in ["ablation", "all"]:
        from experiments.ablation_study import run_ablation_study
        run_ablation_study(save_results=save, evaluate=False)


if __name__ == "__main__":
    main()
