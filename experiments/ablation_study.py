"""
Ablation Study: COHA Variants.

Evaluates 5 ablation variants of the COHA system to isolate the contribution
of each component:

  - COHA-full:        All gates ON, automatically generated ontology
  - COHA-no-outgate:  Output gate OFF, auto ontology
  - COHA-manual-onto: All gates ON, manual (hand-crafted) ontology
  - COHA-input-only:  Only input gate ON, auto ontology
  - COHA-no-onto:     No ontology, no gates (baseline equivalent)

Results saved to results/{domain}_ablation_results.json.
"""

import os
import json
import time
import logging

from llm_client import get_client

logger = logging.getLogger(__name__)


def _load_domain_data(domain: str):
    """Load domain data."""
    if domain == "smart_building":
        from domains.smart_building import (
            DOMAIN_DOCS, USER_STORIES, MANUAL_ONTOLOGY_TTL, BENCHMARK_QA
        )
    elif domain == "military_tactical":
        from domains.military_tactical import (
            DOMAIN_DOCS, USER_STORIES, MANUAL_ONTOLOGY_TTL, BENCHMARK_QA
        )
    else:
        raise ValueError(f"Unknown domain: {domain}")
    return DOMAIN_DOCS, USER_STORIES, MANUAL_ONTOLOGY_TTL, BENCHMARK_QA


def _load_cached_ontology(domain: str) -> dict:
    """Load cached auto-generated ontology or return empty fallback."""
    from config import CACHE_DIR, RESULTS_DIR
    cache_path = os.path.join(CACHE_DIR, f"{domain}_ontology.json")

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Check if main experiment was run — use manual ontology as fallback
    logger.warning(
        f"No cached ontology for {domain}. "
        "Run main_experiment first, or ablation will use a stub ontology."
    )
    return {
        "ontology_ttl": "",
        "cqs": [],
        "cq_coverage_rate": 0.0,
        "is_consistent": False,
        "n_iterations": 0,
    }


def _build_coha_variant(
    client,
    domain: str,
    ontology_ttl: str,
    documents: list,
    config: dict,
    variant_name: str,
):
    """
    Build a COHA variant with the given configuration.

    Args:
        client: UnifiedLLMClient instance.
        domain: Domain identifier.
        ontology_ttl: OWL ontology in Turtle format.
        documents: Document list for retrieval.
        config: Gate configuration dict.
        variant_name: Human-readable variant name.

    Returns:
        AgentRuntime instance configured for the variant.
    """
    from phase2.harness_compiler import HarnessCompiler
    from phase3.context_assembly import ContextAssembler
    from phase3.agent_runtime import AgentRuntime

    print(f"[Ablation] Building variant: {variant_name}")

    # Compile rules (even if no-onto: will produce minimal rule set)
    compiler = HarnessCompiler(domain)
    rule_set = compiler.compile(ontology_ttl if ontology_ttl else _stub_ontology(domain))

    # Context assembly
    use_guidance = bool(ontology_ttl)
    assembler = ContextAssembler(documents, ontology_ttl, use_ontology_guidance=use_guidance)
    assembler.build_index()

    return AgentRuntime(client, rule_set, assembler, config)


def _stub_ontology(domain: str) -> str:
    """Return a minimal stub ontology for no-onto variant."""
    slug = domain.replace(" ", "_")
    return f"""@prefix : <http://coha.org/{slug}#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<http://coha.org/{slug}> a owl:Ontology .
:Entity a owl:Class .
"""


class _NoOntoAgent:
    """
    COHA-no-onto variant: no ontology, no gates, plain LLM with retrieval.
    Uses ContextAssembler with no ontology guidance, no gates.
    """

    def __init__(self, llm_client, documents: list):
        from phase3.context_assembly import ContextAssembler
        self.llm_client = llm_client
        self.assembler = ContextAssembler(documents, "", use_ontology_guidance=False)
        self.assembler.build_index()

    def run(self, query: str) -> dict:
        import time as _time
        t = _time.time()
        docs = self.assembler.retrieve(query, k=5)
        context = "\n\n".join(f"[Doc {i+1}] {d[:400]}" for i, d in enumerate(docs))
        prompt = f"Context:\n{context}\n\nQuery: {query}\n\nAnswer:"

        try:
            response = self.llm_client.generate(system="", user=prompt, max_tokens=1024)
        except RuntimeError as e:
            response = f"[Error: {e}]"

        latency_ms = (_time.time() - t) * 1000
        return {
            "response": response,
            "violations": [],
            "gate_overhead_ms": 0.0,
            "n_regenerations": 0,
            "passed_gates": {},
            "latency_ms": latency_ms,
        }


def run_ablation_study(domain: str = "smart_building", save_results: bool = True):
    """
    Run the ablation study comparing COHA variants.

    Args:
        domain: Domain to evaluate ("smart_building" or "military_tactical").
        save_results: Whether to save results to JSON.

    Returns:
        dict mapping variant_name → evaluation metrics.
    """
    from config import RESULTS_DIR

    print(f"\n{'='*60}")
    print(f"COHA Ablation Study — Domain: {domain}")
    print(f"{'='*60}\n")

    client = get_client()

    # Load domain data
    domain_docs, user_stories, manual_ontology_ttl, benchmark_qa = _load_domain_data(domain)
    documents = [p.strip() for p in domain_docs.split("\n\n") if p.strip() and len(p.strip()) > 50]

    # Load auto-generated ontology from cache
    cached = _load_cached_ontology(domain)
    auto_ontology_ttl = cached.get("ontology_ttl", "") or manual_ontology_ttl

    print(f"[Ablation] Auto-ontology loaded: {len(auto_ontology_ttl)} chars")
    print(f"[Ablation] Manual ontology: {len(manual_ontology_ttl)} chars")
    print(f"[Ablation] Documents: {len(documents)}, Benchmark: {len(benchmark_qa)} QAs\n")

    # ─── Define 5 COHA Variants ──────────────────────────────────────────
    all_gates_config = {
        "enable_input_gate": True,
        "enable_output_gate": True,
        "enable_phase_gate": True,
        "max_regeneration_attempts": 3,
    }
    no_outgate_config = {
        "enable_input_gate": True,
        "enable_output_gate": False,
        "enable_phase_gate": True,
        "max_regeneration_attempts": 3,
    }
    input_only_config = {
        "enable_input_gate": True,
        "enable_output_gate": False,
        "enable_phase_gate": False,
        "max_regeneration_attempts": 3,
    }

    variants = [
        # (variant_name, ontology_ttl, config, is_no_onto)
        ("COHA-full", auto_ontology_ttl, all_gates_config, False),
        ("COHA-no-outgate", auto_ontology_ttl, no_outgate_config, False),
        ("COHA-manual-onto", manual_ontology_ttl, all_gates_config, False),
        ("COHA-input-only", auto_ontology_ttl, input_only_config, False),
        ("COHA-no-onto", "", None, True),  # Special case: plain retrieval + LLM
    ]

    # Build agents
    agents_to_evaluate = []

    for variant_name, ontology_ttl, config, is_no_onto in variants:
        try:
            if is_no_onto:
                agent = _NoOntoAgent(client, documents)
            else:
                agent = _build_coha_variant(
                    client, domain, ontology_ttl, documents, config, variant_name
                )
            agents_to_evaluate.append((agent, variant_name))
        except Exception as e:
            logger.error(f"Failed to build variant {variant_name}: {e}")

    # ─── Evaluate All Variants ────────────────────────────────────────────
    from evaluation.evaluator import COHAEvaluator

    # Use auto ontology as reference for faithfulness evaluation
    evaluator = COHAEvaluator(client, benchmark_qa, auto_ontology_ttl or manual_ontology_ttl)

    all_results = {}

    for agent, name in agents_to_evaluate:
        try:
            metrics = evaluator.evaluate_agent(agent, name)
            all_results[name] = metrics
        except Exception as e:
            logger.error(f"Evaluation of {name} failed: {e}")
            all_results[name] = {"agent_name": name, "error": str(e)}

    # ─── Ablation Table ───────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"ABLATION RESULTS: {domain.upper()}")
    print(f"{'='*60}")

    try:
        df = evaluator.compare_all(all_results)
        print(df.to_string())

        # Print component contribution analysis
        print("\n[Component Contribution Analysis]")
        if "COHA-full" in all_results and "COHA-no-outgate" in all_results:
            full_tsr = all_results["COHA-full"].get("tsr", 0)
            no_out_tsr = all_results["COHA-no-outgate"].get("tsr", 0)
            print(f"  Output gate contribution to TSR: {full_tsr - no_out_tsr:+.2%}")

        if "COHA-full" in all_results and "COHA-input-only" in all_results:
            full_cvr = all_results["COHA-full"].get("cvr", 0)
            input_cvr = all_results["COHA-input-only"].get("cvr", 0)
            print(f"  Output gate contribution to CVR reduction: {input_cvr - full_cvr:+.2%}")

        if "COHA-full" in all_results and "COHA-manual-onto" in all_results:
            full_rf = all_results["COHA-full"].get("rf", 0)
            manual_rf = all_results["COHA-manual-onto"].get("rf", 0)
            print(f"  Auto-ontology vs manual ontology RF delta: {full_rf - manual_rf:+.3f}")

    except Exception as e:
        logger.warning(f"Could not build ablation table: {e}")
        for name, metrics in all_results.items():
            if "error" not in metrics:
                print(f"  {name}: CVR={metrics.get('cvr', 0):.2%}, "
                      f"TSR={metrics.get('tsr', 0):.2%}, "
                      f"RF={metrics.get('rf', 0):.3f}")

    # ─── Save Results ─────────────────────────────────────────────────────
    if save_results:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        save_path = os.path.join(RESULTS_DIR, f"{domain}_ablation_results.json")

        serializable_results = {}
        for name, metrics in all_results.items():
            serializable_results[name] = {
                k: v for k, v in metrics.items()
                if k != "all_responses"
            }

        output = {
            "domain": domain,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "variants": list(serializable_results.keys()),
            "results": serializable_results,
        }

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"\n[Results] Saved to {save_path}")

    return all_results


if __name__ == "__main__":
    run_ablation_study("smart_building")
