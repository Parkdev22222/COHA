"""
Ablation Study: isolates contribution of each COHA component.

Conditions (from paper Sec 4.5):
  COHA-full        : context_reset=T, FQ=T, DK=T  (proposed method)
  COHA-no-reset    : context_reset=F, FQ=T, DK=T  (effect of context reset)
  COHA-no-DK       : context_reset=T, FQ=T, DK=F  (effect of DK Rules)
  COHA-no-FQ       : context_reset=T, FQ=F, DK=T  (effect of FQ Rules)
  COHA-static-gate : context_reset=T, FQ=fixed, DK=F (effect of dynamic update)
  Vanilla CQbyCQ   : context_reset=F, FQ=F, DK=F  (baseline)
"""
import os
import json
import time
import logging

logger = logging.getLogger(__name__)


def run_ablation_study(save_results: bool = True) -> dict:
    from config import RESULTS_DIR
    from llm_client import get_client
    from domain.military_cq_benchmark import ALL_CQS, GOLD_STANDARD_TTL, USER_STORY
    from coha.harness import COHAHarness, HarnessConfig
    from baselines.vanilla_cqbycq import VanillaCQbyCQ
    from evaluation.evaluator import COHAEvaluator

    print("\n" + "=" * 60)
    print("COHA Ablation Study")
    print("=" * 60 + "\n")

    client = get_client()
    from experiments.main_experiment import _get_eval_client
    eval_client = _get_eval_client(client)
    evaluator = COHAEvaluator(eval_client, ALL_CQS, GOLD_STANDARD_TTL)

    ablation_conditions = [
        ("COHA-full",        lambda: COHAHarness(client, HarnessConfig.coha_full()).run(ALL_CQS, USER_STORY)),
        ("COHA-no-reset",    lambda: COHAHarness(client, HarnessConfig.coha_no_reset()).run(ALL_CQS, USER_STORY)),
        ("COHA-no-DK",       lambda: COHAHarness(client, HarnessConfig.coha_no_dk()).run(ALL_CQS, USER_STORY)),
        ("COHA-no-FQ",       lambda: COHAHarness(client, HarnessConfig.coha_no_fq()).run(ALL_CQS, USER_STORY)),
        ("COHA-static-gate", lambda: COHAHarness(client, HarnessConfig.coha_static_gate()).run(ALL_CQS, USER_STORY)),
        ("Vanilla-CQbyCQ",   lambda: VanillaCQbyCQ(client).run(ALL_CQS, USER_STORY)),
    ]

    all_results = {}
    for name, run_fn in ablation_conditions:
        print(f"\n[Ablation] Running {name}...")
        try:
            result = run_fn()
            metrics = evaluator.evaluate(result, name)
            all_results[name] = metrics
            print(
                f"  {name}: CCR={metrics['ccr']:.2%}, OC={metrics['oc']}, "
                f"FQ_rules={metrics['n_fq_rules']}, DK_rules={metrics['n_dk_rules']}"
            )
        except Exception as e:
            logger.error(f"Ablation {name} failed: {e}", exc_info=True)
            all_results[name] = {"variant": name, "error": str(e)}

    try:
        df = evaluator.compare_all(all_results)
        print(f"\n{'=' * 60}\nABLATION RESULTS\n{'=' * 60}")
        print(df.to_string())
    except Exception as e:
        logger.warning(f"Table failed: {e}")

    if save_results:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        save_path = os.path.join(RESULTS_DIR, "ablation_results.json")
        output = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "results": {
                k: {kk: vv for kk, vv in v.items() if kk not in ("qic_data",)}
                for k, v in all_results.items()
            },
        }
        with open(save_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\n[Ablation] Results saved to {save_path}")

    return all_results
