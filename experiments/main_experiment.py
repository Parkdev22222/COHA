"""
Main Experiment: COHA vs All Baselines.

Runs the full 3-phase COHA pipeline and evaluates COHA against all baselines:
  - Vanilla Agent
  - RAG Agent
  - GraphRAG Agent
  - OG-RAG Agent
  - Paper 2604 Agent (arXiv:2604.00555)
  - COHA (full)

Results saved to results/{domain}_main_results.json.
"""

import os
import json
import time
import logging

from llm_client import get_client

logger = logging.getLogger(__name__)


def _load_domain_data(domain: str):
    """Load domain data (docs, stories, ontology, benchmark)."""
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


def _load_or_build_ontology(
    client,
    domain: str,
    domain_docs: str,
    user_stories: str,
    n_cqs: int,
    onto_method: str = "cqbycq",
) -> dict:
    """
    Load ontology from cache if available, otherwise run Phase 1 to build it.

    Args:
        client: UnifiedLLMClient instance.
        domain: Domain identifier.
        domain_docs: Domain documentation string.
        user_stories: User stories string.
        n_cqs: Number of CQs to generate.
        onto_method: Ontology construction method ("cqbycq", "text2onto", "ontogpt").

    Returns:
        OntologyBuilder result dict.
    """
    from config import CACHE_DIR

    # Each method gets its own cache file; cqbycq keeps the legacy name.
    method_tag = f"_{onto_method}" if onto_method != "cqbycq" else ""
    cache_path = os.path.join(CACHE_DIR, f"{domain}{method_tag}_ontology.json")

    if os.path.exists(cache_path):
        print(f"[Phase 1] Loading cached ontology from {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"[Phase 1] Building ontology for domain: {domain} (method: {onto_method})")
    from phase1.consistency_validator import ConsistencyValidator
    from phase1.ontology_builder import OntologyBuilder

    validator = ConsistencyValidator()
    builder = OntologyBuilder(client, domain.replace("_", " ").title(), validator)
    result = builder.build(domain_docs, user_stories, n_cqs=n_cqs, method=onto_method)

    # Cache the result
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_data = {
        "ontology_ttl": result["ontology_ttl"],
        "cqs": result["cqs"],
        "cq_coverage_rate": result["cq_coverage_rate"],
        "is_consistent": result["is_consistent"],
        "n_iterations": result["n_iterations"],
    }
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2)
    print(f"[Phase 1] Ontology cached to {cache_path}")

    # Save standalone .ttl for use in external tools (Protégé, SPARQL, etc.)
    ttl_path = os.path.join(CACHE_DIR, f"{domain}{method_tag}_ontology.ttl")
    with open(ttl_path, "w", encoding="utf-8") as f:
        f.write(result["ontology_ttl"])
    print(f"[Phase 1] Ontology saved as Turtle: {ttl_path}")

    return result


def _build_coha_agent(
    client,
    domain: str,
    ontology_ttl: str,
    documents: list,
    config_override: dict = None,
):
    """
    Build a COHA AgentRuntime instance.

    Args:
        client: UnifiedLLMClient instance.
        domain: Domain identifier.
        ontology_ttl: OWL ontology in Turtle format.
        documents: List of document strings.
        config_override: Optional config dict to override defaults.

    Returns:
        AgentRuntime instance.
    """
    from phase2.harness_compiler import HarnessCompiler
    from phase3.context_assembly import ContextAssembler
    from phase3.agent_runtime import AgentRuntime

    # Phase 2: Compile harness rules
    print(f"[Phase 2] Compiling harness rules for domain: {domain}")
    compiler = HarnessCompiler(domain)
    rule_set = compiler.compile(ontology_ttl)
    print(f"[Phase 2] Compiled {len(rule_set.rules)} rules in {rule_set.compilation_time_ms:.1f} ms")

    # Context assembler with ontology guidance
    assembler = ContextAssembler(documents, ontology_ttl, use_ontology_guidance=True)
    assembler.build_index()

    # Default config
    config = {
        "enable_input_gate": True,
        "enable_output_gate": True,
        "enable_phase_gate": True,
        "max_regeneration_attempts": 3,
    }
    if config_override:
        config.update(config_override)

    return AgentRuntime(client, rule_set, assembler, config)


def run_main_experiment(
    domain: str = "smart_building",
    save_results: bool = True,
    onto_method: str = None,
):
    """
    Run the main COHA experiment: COHA vs all baselines.

    Args:
        domain: Domain to evaluate ("smart_building" or "military_tactical").
        save_results: Whether to save results to JSON.
        onto_method: Ontology construction method ("cqbycq", "text2onto", "ontogpt").
                     Defaults to config.ONTOLOGY_METHOD.

    Returns:
        dict mapping agent_name → evaluation metrics.
    """
    from config import DOMAINS_CONFIG, RESULTS_DIR

    print(f"\n{'='*60}")
    print(f"COHA Main Experiment — Domain: {domain}")
    print(f"{'='*60}\n")

    # Initialize LLM client
    client = get_client()

    # Resolve ontology method (arg > config default)
    if onto_method is None:
        import config as _cfg
        onto_method = getattr(_cfg, "ONTOLOGY_METHOD", "cqbycq")

    # Load domain data
    domain_docs, user_stories, manual_ontology_ttl, benchmark_qa = _load_domain_data(domain)
    domain_config = DOMAINS_CONFIG.get(domain, {})
    n_cqs = domain_config.get("n_cqs", 10)

    # Split docs into document list for retrieval
    documents = [p.strip() for p in domain_docs.split("\n\n") if p.strip() and len(p.strip()) > 50]
    print(f"[Data] Loaded {len(documents)} documents, {len(benchmark_qa)} benchmark QA pairs.")

    # ─── Phase 1: Ontology Building ─────────────────────────────────────
    builder_result = _load_or_build_ontology(
        client, domain, domain_docs, user_stories, n_cqs, onto_method
    )
    auto_ontology_ttl = builder_result["ontology_ttl"]
    cq_coverage = builder_result["cq_coverage_rate"]
    is_consistent = builder_result["is_consistent"]

    # Save manual (reference) ontology as .ttl for external tooling
    from config import CACHE_DIR
    os.makedirs(CACHE_DIR, exist_ok=True)
    manual_ttl_path = os.path.join(CACHE_DIR, f"{domain}_manual_ontology.ttl")
    if not os.path.exists(manual_ttl_path):
        with open(manual_ttl_path, "w", encoding="utf-8") as f:
            f.write(manual_ontology_ttl)
        print(f"[Phase 1] Manual ontology saved as Turtle: {manual_ttl_path}")

    print(f"[Phase 1] CQ Coverage: {cq_coverage:.2%}, Consistent: {is_consistent}")

    # ─── Phase 2 + 3: Build COHA Agent ──────────────────────────────────
    coha_agent = _build_coha_agent(client, domain, auto_ontology_ttl, documents)

    # ─── Build Baselines ────────────────────────────────────────────────
    print("[Baselines] Initializing baseline agents...")
    from baselines.vanilla_agent import VanillaAgent
    from baselines.rag_agent import RAGAgent
    from baselines.graphrag_agent import GraphRAGAgent
    from baselines.ograg_agent import OGRAGAgent
    from baselines.paper_2604_agent import Paper2604Agent

    vanilla = VanillaAgent(client)
    rag = RAGAgent(client, documents)
    graphrag = GraphRAGAgent(client, documents)
    ograg = OGRAGAgent(client, documents, manual_ontology_ttl)
    paper2604 = Paper2604Agent(client, manual_ontology_ttl)

    # Build GraphRAG community summaries upfront
    print("[Baselines] Building GraphRAG community summaries...")
    graphrag.build_community_summaries()

    # ─── Evaluation ─────────────────────────────────────────────────────
    from evaluation.evaluator import COHAEvaluator

    evaluator = COHAEvaluator(client, benchmark_qa, auto_ontology_ttl)

    agents_to_evaluate = [
        (vanilla, "VanillaAgent"),
        (rag, "RAGAgent"),
        (graphrag, "GraphRAGAgent"),
        (ograg, "OGRAGAgent"),
        (paper2604, "Paper2604Agent"),
        (coha_agent, "COHA-Full"),
    ]

    all_results = {}

    for agent, name in agents_to_evaluate:
        try:
            metrics = evaluator.evaluate_agent(agent, name)
            all_results[name] = metrics
        except Exception as e:
            logger.error(f"Evaluation of {name} failed: {e}")
            all_results[name] = {"agent_name": name, "error": str(e)}

    # ─── Comparison Table ────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"RESULTS: {domain.upper()}")
    print(f"{'='*60}")

    try:
        df = evaluator.compare_all(all_results)
        print(df.to_string())
    except Exception as e:
        logger.warning(f"Could not build comparison table: {e}")
        for name, metrics in all_results.items():
            print(f"  {name}: CVR={metrics.get('cvr', 'N/A'):.2%}, "
                  f"TSR={metrics.get('tsr', 'N/A'):.2%}")

    # ─── Ontology Quality ────────────────────────────────────────────────
    onto_quality = evaluator.evaluate_ontology_quality(builder_result)
    print(f"\nOntology Quality:")
    print(f"  CQ Coverage Rate: {onto_quality['cq_coverage_rate']:.2%}")
    print(f"  OWL Consistent: {onto_quality['is_consistent']}")

    # ─── Save Results ────────────────────────────────────────────────────
    if save_results:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        save_path = os.path.join(RESULTS_DIR, f"{domain}_main_results.json")

        serializable_results = {}
        for name, metrics in all_results.items():
            serializable_results[name] = {
                k: v for k, v in metrics.items()
                if k != "all_responses"  # exclude verbose per-query results for size
            }

        output = {
            "domain": domain,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ontology_quality": onto_quality,
            "results": serializable_results,
        }

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"\n[Results] Saved to {save_path}")

    return all_results


if __name__ == "__main__":
    run_main_experiment("smart_building")
