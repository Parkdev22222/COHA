"""COHA v2 성능 측정 실행기.

run_experiments.py → repair_ttl.py → merge_synonyms.py → run_test.py
순서로 실행하는 파이프라인의 마지막 단계입니다.

cache/ 에 저장된 TTL 파일과 harness 메타데이터를 불러와 평가 지표를 계산하고
results/ 에 저장합니다.

사용 예
--------
# 특정 variant 하나 평가
python run_test.py --variant COHA-full

# 수정된 TTL 파일 직접 지정 (repair/synonym merge 후)
python run_test.py --variant COHA-full --ttl cache/COHA_full_ontology_merged.ttl

# main experiment 전체 평가
python run_test.py --experiment main

# ablation study 전체 평가
python run_test.py --experiment ablation

# 전체 평가 (main + ablation)
python run_test.py --experiment all

# cache/ 디렉터리의 모든 TTL 파일 평가
python run_test.py --all-cached

# 결과 저장 없이 콘솔 출력만
python run_test.py --variant COHA-full --no-save
"""
import argparse
import json
import logging
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from experiments.main_experiment import VARIANT_KEYS, load_harness_result, save_eval_result, _safe_filename


# ---------------------------------------------------------------------------
# 단일 variant 평가
# ---------------------------------------------------------------------------

def evaluate_variant(
    variant_name: str,
    evaluator,
    cache_dir: str,
    results_dir: str,
    ttl_override: str = "",
    save: bool = True,
) -> dict:
    """TTL을 불러와 평가하고 결과를 반환합니다."""
    print(f"\n[Eval] {variant_name} ...")

    harness_result = load_harness_result(variant_name, cache_dir, ttl_override=ttl_override)

    if not harness_result.get("ontology_ttl", "").strip():
        logger.warning("%s: TTL이 비어 있습니다. cache/ 에 파일이 있는지 확인하세요.", variant_name)
        return {"variant": variant_name, "error": "TTL not found"}

    try:
        metrics = evaluator.evaluate(harness_result, variant_name)
        print(
            f"  CCR={metrics.get('ccr', 0):.2%}, "
            f"OC={metrics.get('oc')}, "
            f"SC={metrics.get('sc', {}).get('sc', 0):.2%}, "
            f"sparql_ccr={metrics.get('sparql_ccr', 0):.2%}"
        )
        if save:
            save_eval_result(variant_name, metrics, results_dir)
        return metrics
    except Exception as e:
        logger.error("Eval %s 실패: %s", variant_name, e, exc_info=True)
        return {"variant": variant_name, "error": str(e)}


# ---------------------------------------------------------------------------
# 결과 후처리 (DRC/FRC, 비교 테이블)
# ---------------------------------------------------------------------------

def _post_process(eval_results: dict, evaluator, results_dir: str, save: bool, summary_filename: str):
    from evaluation.metrics import compute_drc, compute_frc

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
        logger.warning("비교 테이블 생성 실패: %s", e)

    try:
        ce_df = evaluator.compute_ce_table(eval_results)
        if not ce_df.empty:
            print(f"\n{'=' * 60}\nCONTEXT EFFICIENCY\n{'=' * 60}")
            print(ce_df.to_string())
    except Exception as e:
        logger.warning("CE 테이블 생성 실패: %s", e)

    if save:
        os.makedirs(results_dir, exist_ok=True)
        save_path = os.path.join(results_dir, summary_filename)
        output = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "results": {
                k: {kk: vv for kk, vv in v.items() if kk not in ("qic_data",)}
                for k, v in eval_results.items()
                if "error" not in v
            },
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"\n[Results] 저장 완료 → {save_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_MAIN_VARIANTS = [
    "B1-WholeOntology", "B2-Vanilla-CQbyCQ", "B3-Memoryless", "B4-Ontogenia",
    "B5-OntoGPT", "B5-SPIRES", "B7-Static-Gate",
    "COHA-no-reset", "COHA-no-FQ", "COHA-no-DK", "COHA-full",
    "COHA+Ontogenia", "COHA+OntoGPT",
]

_ABLATION_VARIANTS = [
    "COHA-full", "COHA-no-reset", "COHA-no-DK",
    "COHA-no-FQ", "COHA-static-gate", "Vanilla-CQbyCQ",
]


def main():
    parser = argparse.ArgumentParser(description="COHA v2 — 성능 측정 실행기")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--variant",
        choices=VARIANT_KEYS,
        metavar="VARIANT",
        help=f"단일 variant 평가. 선택지: {VARIANT_KEYS}",
    )
    group.add_argument(
        "--experiment",
        choices=["main", "ablation", "all"],
        help="실험 종류 전체 평가",
    )
    group.add_argument(
        "--all-cached",
        action="store_true",
        help="cache/ 디렉터리의 모든 *_ontology.ttl 파일 평가",
    )
    parser.add_argument(
        "--ttl",
        default="",
        metavar="PATH",
        help="평가할 TTL 파일 직접 지정 (--variant 와 함께 사용, repair/synonym merge 후 TTL 경로)",
    )
    parser.add_argument("--variant-name", default="", help="--ttl 단독 사용 시 variant 이름 지정")
    parser.add_argument("--no-save", action="store_true", help="결과 파일 저장 안 함")
    parser.add_argument("--model", type=str, default=None, help="LLM 모델명 override")
    parser.add_argument(
        "--cache-dir", default="", help="TTL/메타 파일 경로 (기본: config.CACHE_DIR)"
    )
    parser.add_argument(
        "--results-dir", default="", help="결과 저장 경로 (기본: config.RESULTS_DIR)"
    )
    args = parser.parse_args()

    import config
    if args.model:
        config.MODEL_NAME = args.model

    if config.MODEL_NAME.startswith("claude") and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    from llm_client import get_client
    from domain.military_cq_benchmark import ALL_CQS, GOLD_STANDARD_TTL
    from evaluation.evaluator import COHAEvaluator

    cache_dir   = args.cache_dir   or config.CACHE_DIR
    results_dir = args.results_dir or config.RESULTS_DIR
    save        = not args.no_save

    client    = get_client()
    evaluator = COHAEvaluator(client, ALL_CQS, GOLD_STANDARD_TTL)

    print("\n" + "=" * 60)
    print("COHA 성능 측정")
    print("=" * 60 + "\n")

    # ── 단일 variant ──────────────────────────────────────────────
    if args.variant:
        result = evaluate_variant(
            args.variant, evaluator, cache_dir, results_dir,
            ttl_override=args.ttl, save=save,
        )
        return

    # ── experiment 전체 ───────────────────────────────────────────
    if args.experiment:
        suites = []
        if args.experiment in ("main", "all"):
            suites.append(("main", _MAIN_VARIANTS, "main_results.json"))
        if args.experiment in ("ablation", "all"):
            suites.append(("ablation", _ABLATION_VARIANTS, "ablation_results.json"))

        for suite_name, variant_list, summary_file in suites:
            print(f"\n{'=' * 60}\n{suite_name.upper()} EXPERIMENT 평가\n{'=' * 60}")
            eval_results = {}
            for name in variant_list:
                eval_results[name] = evaluate_variant(
                    name, evaluator, cache_dir, results_dir, save=False
                )
            _post_process(eval_results, evaluator, results_dir, save, summary_file)
        return

    # ── cache/ 전체 TTL 파일 ─────────────────────────────────────
    if args.all_cached:
        import re
        ttl_files = sorted(
            f for f in os.listdir(cache_dir) if f.endswith("_ontology.ttl")
        )
        if not ttl_files:
            print(f"[오류] {cache_dir} 에 *_ontology.ttl 파일이 없습니다.")
            sys.exit(1)

        eval_results = {}
        for fname in ttl_files:
            # COHA_full_ontology.ttl → "COHA_full" → "COHA-full" 역변환 시도
            safe = fname.replace("_ontology.ttl", "")
            # _safe_filename 역변환: 단순히 safe 이름으로 variant 조회
            matched = next(
                (v for v in VARIANT_KEYS if _safe_filename(v) == safe), safe
            )
            ttl_path = os.path.join(cache_dir, fname)
            eval_results[matched] = evaluate_variant(
                matched, evaluator, cache_dir, results_dir,
                ttl_override=ttl_path, save=save,
            )

        _post_process(eval_results, evaluator, results_dir, save, "cached_results.json")


if __name__ == "__main__":
    main()
