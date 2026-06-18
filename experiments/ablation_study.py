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


def run_ablation_study(save_results: bool = True, evaluate: bool = False) -> dict:
    """Run ablation study, saving TTL + harness metadata for each condition.

    evaluate=False (default): only generate ontologies, skip evaluation.
    evaluate=True: also run evaluator and save metrics.
    """
    from config import RESULTS_DIR, CACHE_DIR
    from llm_client import get_client
    from domain.military_cq_benchmark import ALL_CQS, GOLD_STANDARD_TTL, USER_STORY
    from domain.military_docs import DOMAIN_DOCS
    from coha.harness import COHAHarness, HarnessConfig
    from baselines.vanilla_cqbycq import VanillaCQbyCQ
    from experiments.main_experiment import save_harness_outputs, save_eval_result

    print("\n" + "=" * 60)
    print("COHA Ablation Study")
    print("=" * 60 + "\n")

    client = get_client()

    ablation_conditions = [
        ("COHA-full",        lambda: COHAHarness(client, HarnessConfig.coha_full(), domain_docs=DOMAIN_DOCS).run(ALL_CQS, USER_STORY)),
        ("COHA-no-reset",    lambda: COHAHarness(client, HarnessConfig.coha_no_reset(), domain_docs=DOMAIN_DOCS).run(ALL_CQS, USER_STORY)),
        ("COHA-no-DK",       lambda: COHAHarness(client, HarnessConfig.coha_no_dk(), domain_docs=DOMAIN_DOCS).run(ALL_CQS, USER_STORY)),
        ("COHA-no-FQ",       lambda: COHAHarness(client, HarnessConfig.coha_no_fq(), domain_docs=DOMAIN_DOCS).run(ALL_CQS, USER_STORY)),
        ("COHA-static-gate", lambda: COHAHarness(client, HarnessConfig.coha_static_gate(), domain_docs=DOMAIN_DOCS).run(ALL_CQS, USER_STORY)),
        ("Vanilla-CQbyCQ",   lambda: VanillaCQbyCQ(client).run(ALL_CQS, USER_STORY)),
    ]

    harness_results = {}
    all_results = {}
    for name, run_fn in ablation_conditions:
        print(f"\n[Ablation] Running {name}...")
        try:
            result = run_fn()
            harness_results[name] = result
            all_results[name] = {"variant": name}
            if save_results:
                save_harness_outputs(name, result, CACHE_DIR)
        except Exception as e:
            logger.error(f"Ablation {name} failed: {e}", exc_info=True)
            all_results[name] = {"variant": name, "error": str(e)}

    if not evaluate:
        return all_results

    from evaluation.evaluator import COHAEvaluator
    evaluator = COHAEvaluator(client, ALL_CQS, GOLD_STANDARD_TTL)

    eval_results = {}
    for name, result in harness_results.items():
        print(f"\n[Eval] Evaluating {name}...")
        try:
            metrics = evaluator.evaluate(result, name)
            eval_results[name] = metrics
            print(
                f"  {name}: CCR={metrics.get('ccr', 0):.2%}, OC={metrics.get('oc')}, "
                f"FQ_rules={metrics.get('n_fq_rules', 'N/A')}, DK_rules={metrics.get('n_dk_rules', 'N/A')}"
            )
        except Exception as e:
            logger.error(f"Eval {name} failed: {e}", exc_info=True)
            eval_results[name] = {"variant": name, "error": str(e)}

    try:
        df = evaluator.compare_all(eval_results)
        print(f"\n{'=' * 60}\nABLATION RESULTS\n{'=' * 60}")
        print(df.to_string())
    except Exception as e:
        logger.warning(f"Table failed: {e}")

    if save_results:
        for name, metrics in eval_results.items():
            if "error" not in metrics:
                save_eval_result(name, metrics, RESULTS_DIR)
        os.makedirs(RESULTS_DIR, exist_ok=True)
        save_path = os.path.join(RESULTS_DIR, "ablation_results.json")
        output = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "results": {
                k: {kk: vv for kk, vv in v.items() if kk not in ("qic_data",)}
                for k, v in eval_results.items()
            },
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"\n[Ablation] Results saved to {save_path}")

    return eval_results
