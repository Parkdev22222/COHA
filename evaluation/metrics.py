"""
Evaluation metrics for COHA v2.

Ontology Quality:
  CCR  - CQ Coverage Rate
  OC   - OWL Consistency
  SC   - Structural Completeness vs Gold Standard

COHA-specific Dynamic Improvement:
  QIC  - Quality Improvement Curve (CCR at each CQ index k)
  RAR  - Rule Accumulation Rate (rules added per gate pass)
  DRC  - Domain Rule Contribution (CCR: COHA-full - COHA-no-DK)
  FRC  - Formal Rule Contribution (OC: COHA-full - COHA-no-FQ)

Efficiency:
  GO   - Gate Overhead (gate_time / total_time)
  CE   - Context Efficiency (token_ratio vs Vanilla)
"""
import re
import logging
import numpy as np

logger = logging.getLogger(__name__)


def compute_ccr(cqs: list, ontology_ttl: str, llm_client) -> float:
    """
    CQ Coverage Rate: fraction of CQs answerable by the generated ontology.

    Judge checks for SPECIFIC axioms (not just vocabulary presence):
    - The required class must be declared as owl:Class
    - The required property must exist with domain/range
    - A subClassOf or restriction linking the concepts must be present

    Uses chunked ontology view (up to 6000 chars) to avoid truncation bias
    that favors WholeOntology Prompting (which front-loads all classes).
    """
    if not cqs or not ontology_ttl.strip():
        return 0.0

    # Use more of the ontology (6000 chars), not just the front
    onto_len = len(ontology_ttl)
    if onto_len <= 6000:
        onto_snippet = ontology_ttl
    else:
        # Take beginning + middle sample to avoid front-loading bias
        onto_snippet = ontology_ttl[:3000] + "\n...\n" + ontology_ttl[onto_len//2: onto_len//2 + 3000]

    covered = 0
    for cq in cqs:
        q_text = cq["question"] if isinstance(cq, dict) else cq
        prompt = (
            "You are a strict OWL ontology evaluator.\n\n"
            "Evaluate whether the ontology below contains the SPECIFIC OWL axioms "
            "needed to formally answer the Competency Question.\n\n"
            "Answer YES only if ALL of the following are present:\n"
            "1. The key concepts are declared as owl:Class (not just mentioned in comments)\n"
            "2. The required relationships exist as owl:ObjectProperty or owl:DatatypeProperty\n"
            "3. There is at least one axiom (subClassOf, domain, range, or restriction) "
            "linking the concepts relevant to the CQ\n\n"
            "Answer NO if the ontology only mentions vocabulary without proper OWL axioms.\n\n"
            f"ONTOLOGY:\n```turtle\n{onto_snippet}\n```\n\n"
            f"CQ: {q_text}\n\n"
            "First line must be YES or NO. Then one sentence explaining why."
        )
        try:
            resp = llm_client.generate(system="", user=prompt, max_tokens=128)
            if resp.strip().upper().startswith("YES"):
                covered += 1
        except Exception as e:
            logger.warning(f"CCR judge error: {e}")
    return covered / len(cqs)


def compute_oc(ontology_ttl: str) -> bool:
    """OWL Consistency: True if HermiT reasoner finds no inconsistency."""
    from coha.owl_utils import check_consistency
    return check_consistency(ontology_ttl)


def compute_sc(generated_ttl: str, gold_standard_ttl: str) -> dict:
    """
    Structural Completeness vs Gold Standard.
    Returns class_coverage, property_coverage, overall_sc.
    """
    from coha.owl_utils import extract_class_names, extract_property_names
    gen_classes = set(extract_class_names(generated_ttl))
    gold_classes = set(extract_class_names(gold_standard_ttl))
    gen_props = set(extract_property_names(generated_ttl))
    gold_props = set(extract_property_names(gold_standard_ttl))

    class_coverage = len(gen_classes & gold_classes) / max(len(gold_classes), 1)
    prop_coverage = len(gen_props & gold_props) / max(len(gold_props), 1)
    overall_sc = (class_coverage + prop_coverage) / 2

    return {
        "class_coverage": round(class_coverage, 4),
        "property_coverage": round(prop_coverage, 4),
        "sc": round(overall_sc, 4),
        "n_classes_generated": len(gen_classes),
        "n_classes_gold": len(gold_classes),
        "n_props_generated": len(gen_props),
        "n_props_gold": len(gold_props),
    }


def compute_qic(qic_data: list) -> list:
    """
    Quality Improvement Curve: list of (k, cq_text, n_classes_accumulated) tuples.
    Structural quality proxy — cumulative class count at each CQ step k.
    True CCR-based QIC would require O(n²) LLM judge calls; structural proxy
    is computable without additional LLM calls and shows the same trend.
    """
    return qic_data  # pre-computed in harness as (k, cq_text, n_classes)


def compute_rar(rar_data: list) -> dict:
    """Rule Accumulation Rate statistics."""
    if not rar_data:
        return {"mean_rar": 0.0, "total_rules_added": 0, "rar_per_cq": []}
    values = [v for _, v in rar_data]
    return {
        "mean_rar": float(np.mean(values)),
        "total_rules_added": int(sum(values)),
        "rar_per_cq": rar_data,
    }


def compute_drc(ccr_full: float, ccr_fq_only: float) -> float:
    """Domain Rule Contribution: CCR improvement from DK Rules."""
    return round(ccr_full - ccr_fq_only, 4)


def compute_frc(oc_full: float, oc_dk_only: float) -> float:
    """Formal Rule Contribution: OC improvement from FQ Rules."""
    full_val = 1.0 if oc_full else 0.0
    dk_val = 1.0 if oc_dk_only else 0.0
    return round(full_val - dk_val, 4)


def compute_go(gate_times: list, total_times: list) -> float:
    """Gate Overhead: mean(gate_time / total_time)."""
    if not gate_times or not total_times:
        return 0.0
    n = min(len(gate_times), len(total_times))
    overheads = [min(1.0, gate_times[i] / max(total_times[i], 1)) for i in range(n)]
    return float(np.mean(overheads))


def compute_ce(total_times_coha: list, total_times_vanilla: list) -> float:
    """Context Efficiency: proxy via total latency ratio (vanilla / coha)."""
    if not total_times_coha or not total_times_vanilla:
        return 1.0
    return float(np.sum(total_times_vanilla) / max(np.sum(total_times_coha), 1))


def _clean_turtle_for_rdflib(ttl: str) -> str:
    """Strip markdown fences from Turtle text before rdflib parsing."""
    for marker in ["```turtle", "```ttl", "```"]:
        if marker in ttl:
            start = ttl.find(marker) + len(marker)
            nl = ttl.find("\n", start)
            start = nl + 1 if nl != -1 else start
            end = ttl.rfind("```")
            if end > start:
                return ttl[start:end].strip()
    return ttl.strip()


def compute_sparql_ccr(cqs: list, ontology_ttl: str, llm_client) -> dict:
    """
    SPARQL-based CQ Coverage Rate (TBox queries).

    For each CQ:
      1. LLM generates a SPARQL ASK or SELECT query targeting the TBox
         (class declarations, subClassOf, domain/range — NOT individuals)
      2. rdflib executes the query against the parsed ontology graph
      3. ASK=true or non-empty SELECT → covered

    More objective than LLM-as-judge: execution is deterministic.
    Falls back to 0 for queries that fail to parse/execute.
    """
    try:
        from rdflib import Graph, OWL, RDF, RDFS
        from rdflib.namespace import Namespace
    except ImportError:
        logger.warning("rdflib not available; skipping SPARQL CCR.")
        return {"coverage_rate": 0.0, "passed": 0, "total": len(cqs), "details": []}

    if not cqs or not ontology_ttl.strip():
        return {"coverage_rate": 0.0, "passed": 0, "total": len(cqs), "details": []}

    # Pre-process: strip markdown fences before parsing
    clean_ttl = _clean_turtle_for_rdflib(ontology_ttl)

    g = Graph()
    try:
        g.parse(data=clean_ttl, format="turtle")
    except Exception as e:
        logger.warning(f"SPARQL CCR: ontology parse failed: {e}")
        return {"coverage_rate": 0.0, "passed": 0, "total": len(cqs), "details": []}

    MIL = Namespace("http://coha.org/military#")

    # Build TBox schema summary for the LLM prompt
    classes = sorted(set(
        str(s).rsplit("#", 1)[-1]
        for s, _, o in g.triples((None, RDF.type, OWL.Class))
        if str(s).startswith("http://coha.org/military#")
    ))[:40]
    obj_props = sorted(set(
        str(s).rsplit("#", 1)[-1]
        for s, _, o in g.triples((None, RDF.type, OWL.ObjectProperty))
        if str(s).startswith("http://coha.org/military#")
    ))[:30]
    subclass_pairs = [
        (str(s).rsplit("#", 1)[-1], str(o).rsplit("#", 1)[-1])
        for s, _, o in g.triples((None, RDFS.subClassOf, None))
        if str(s).startswith("http://coha.org/military#")
        and str(o).startswith("http://coha.org/military#")
    ][:20]

    schema_hint = ""
    if classes:
        schema_hint += f"Classes: {', '.join(classes)}\n"
    if obj_props:
        schema_hint += f"ObjectProperties: {', '.join(obj_props)}\n"
    if subclass_pairs:
        schema_hint += "SubClassOf: " + ", ".join(f"{s}→{o}" for s, o in subclass_pairs[:10]) + "\n"

    results = []
    passed = 0

    for cq in cqs:
        q_text = cq["question"] if isinstance(cq, dict) else cq

        # Step 1: Generate TBox-level SPARQL query
        sparql_prompt = (
            "You are querying an OWL ontology TBox (schema only — NO individuals exist).\n"
            "Generate a SPARQL query that checks whether the ontology SCHEMA contains\n"
            "the classes and properties needed to answer the Competency Question.\n\n"
            f"ONTOLOGY SCHEMA:\n{schema_hint}\n"
            f"PREFIX : <http://coha.org/military#>\n\n"
            f"Competency Question: {q_text}\n\n"
            "Rules:\n"
            "1. Use PREFIX : <http://coha.org/military#> and standard prefixes\n"
            "   (owl: <http://www.w3.org/2002/07/owl#>, "
            "rdfs: <http://www.w3.org/2000/01/rdf-schema#>)\n"
            "2. Prefer ASK queries: ASK { :SomeClass a owl:Class }\n"
            "3. Or SELECT over schema: SELECT ?c WHERE { ?c rdfs:subClassOf :SomeClass }\n"
            "4. Do NOT query for individuals (none exist)\n"
            "5. Return ONLY the SPARQL query, no explanation\n\n"
            "SPARQL:"
        )
        sparql_query = ""
        try:
            raw = llm_client.generate(system="", user=sparql_prompt, max_tokens=256)
            if "```" in raw:
                start = raw.find("```") + 3
                nl = raw.find("\n", start)
                start = nl + 1 if nl != -1 else start
                end = raw.find("```", start)
                sparql_query = raw[start:end].strip() if end != -1 else raw[start:].strip()
            else:
                sparql_query = raw.strip()
        except Exception as e:
            logger.warning(f"SPARQL generation failed for CQ: {e}")

        # Step 2: Execute — handle both ASK and SELECT
        status = "error"
        result_count = 0
        if sparql_query:
            try:
                qres = g.query(sparql_query)
                # ASK query returns boolean result
                if qres.type == "ASK":
                    passed_this = bool(qres.askAnswer)
                    result_count = 1 if passed_this else 0
                else:
                    rows = list(qres)
                    result_count = len(rows)
                    passed_this = result_count > 0
                status = "pass" if passed_this else "fail"
                if passed_this:
                    passed += 1
            except Exception as e:
                status = "error"
                logger.debug(f"SPARQL exec failed: {e}")

        results.append({
            "cq": q_text,
            "status": status,
            "result_count": result_count,
        })

    total = len(cqs)
    return {
        "coverage_rate": round(passed / total, 4) if total else 0.0,
        "passed": passed,
        "total": total,
        "details": results,
    }


def compute_llm_judge_detailed(cqs: list, ontology_ttl: str, llm_client) -> dict:
    """
    4-dimension LLM judge (annotation-free ontology evaluation).

    Scores each CQ on:
      - answerability  (1-5): can the CQ be answered from ontology structure?
      - completeness   (1-5): are all necessary concepts present?
      - precision      (1-5): concepts correctly scoped (not too broad/narrow)?
      - domain_validity(1-5): concepts valid for military tactical domain?

    verdict: "pass" (avg≥3.5) | "partial" (2≤avg<3.5) | "fail" (avg<2)

    Returns aggregated means and per-CQ details.
    """
    import json as _json

    if not cqs or not ontology_ttl.strip():
        return _empty_judge_result(len(cqs))

    onto_len = len(ontology_ttl)
    onto_snippet = (
        ontology_ttl
        if onto_len <= 6000
        else ontology_ttl[:3000] + "\n...\n" + ontology_ttl[onto_len // 2: onto_len // 2 + 3000]
    )

    details = []
    score_sums = {"answerability": 0, "completeness": 0, "precision": 0, "domain_validity": 0}
    verdicts = {"pass": 0, "partial": 0, "fail": 0}

    for cq in cqs:
        q_text = cq["question"] if isinstance(cq, dict) else cq

        prompt = (
            "You are an ontology quality evaluator for military tactical operations.\n\n"
            f"ONTOLOGY:\n```turtle\n{onto_snippet}\n```\n\n"
            f"Competency Question: {q_text}\n\n"
            "Score each dimension 1-5 and assign a verdict.\n"
            "Dimensions:\n"
            "  answerability: Can this CQ be answered from the ontology structure? (1=no, 5=fully)\n"
            "  completeness: Are all necessary concepts present? (1=missing most, 5=all present)\n"
            "  precision: Are concepts correctly scoped — not too broad or too narrow? (1=poor, 5=exact)\n"
            "  domain_validity: Are concepts valid for military tactical operations? (1=invalid, 5=correct)\n"
            "verdict: pass (avg≥3.5) | partial (2≤avg<3.5) | fail (avg<2)\n\n"
            'Respond ONLY in JSON (no markdown):\n'
            '{"answerability":<1-5>,"completeness":<1-5>,"precision":<1-5>,'
            '"domain_validity":<1-5>,"verdict":"pass|partial|fail"}'
        )

        entry = {
            "cq": q_text,
            "answerability": 0,
            "completeness": 0,
            "precision": 0,
            "domain_validity": 0,
            "verdict": "error",
        }
        try:
            raw = llm_client.generate(system="", user=prompt, max_tokens=128)
            # Extract JSON
            raw = raw.strip()
            if "{" in raw:
                raw = raw[raw.find("{"):raw.rfind("}") + 1]
            parsed = _json.loads(raw)
            for dim in ("answerability", "completeness", "precision", "domain_validity"):
                val = int(parsed.get(dim, 0))
                entry[dim] = val
                score_sums[dim] += val
            entry["verdict"] = parsed.get("verdict", "fail")
            verdicts[entry["verdict"]] = verdicts.get(entry["verdict"], 0) + 1
        except Exception as e:
            logger.warning(f"LLM judge detail parse failed: {e}")

        details.append(entry)

    n = max(len(cqs), 1)
    return {
        "mean_answerability": round(score_sums["answerability"] / n, 3),
        "mean_completeness": round(score_sums["completeness"] / n, 3),
        "mean_precision": round(score_sums["precision"] / n, 3),
        "mean_domain_validity": round(score_sums["domain_validity"] / n, 3),
        "mean_overall": round(sum(score_sums.values()) / (4 * n), 3),
        "verdicts": verdicts,
        "details": details,
    }


def _empty_judge_result(n_cqs: int) -> dict:
    return {
        "mean_answerability": 0.0, "mean_completeness": 0.0,
        "mean_precision": 0.0, "mean_domain_validity": 0.0,
        "mean_overall": 0.0,
        "verdicts": {"pass": 0, "partial": 0, "fail": n_cqs},
        "details": [],
    }


def compute_overall_score(ccr: float, oc: bool, structural: dict) -> float:
    """
    Composite quality score (annotation-free).

    Formula (from design doc):
      overall = CCR × 0.5 + OC × 0.3 + depth_score × 0.2

    depth_score = min(avg_depth / 5.0, 1.0)  — normalized to [0,1]
    """
    avg_depth = structural.get("avg_depth", 0.0)
    depth_score = min(avg_depth / 5.0, 1.0)
    oc_val = 1.0 if oc else 0.0
    return round(ccr * 0.5 + oc_val * 0.3 + depth_score * 0.2, 4)


def compute_des_scaffold(ontology_ttl: str, cqs: list) -> dict:
    """
    Domain Expert Score (DES) scaffold.

    DES requires human expert evaluation (1-5 scale on accuracy,
    completeness, usability). This function returns the evaluation
    template and auto-computable proxies.

    Full DES requires domain expert (active/reserve military officer)
    to fill in the template manually.

    Returns:
        dict with auto_proxy scores and an empty expert_scores template.
    """
    from coha.owl_utils import extract_structural_metrics

    struct = extract_structural_metrics(ontology_ttl)
    n_cqs = len(cqs)

    # Auto-proxy: structural richness as a rough proxy for completeness
    n_classes = struct.get("n_classes", 0)
    n_props = struct.get("n_object_properties", 0) + struct.get("n_datatype_properties", 0)
    proxy_completeness = min(1.0, (n_classes + n_props) / max(n_cqs, 1))

    return {
        "des_auto_proxy": round(proxy_completeness * 5, 2),  # scaled to 1-5
        "expert_scores": {
            "accuracy": None,      # Expert fill: 1-5
            "completeness": None,  # Expert fill: 1-5
            "usability": None,     # Expert fill: 1-5
            "des_mean": None,      # Mean of above three
        },
        "evaluation_notes": (
            "DES requires human expert evaluation. "
            "Provide the generated .ttl file to a domain expert "
            "(active/reserve military officer) for manual scoring."
        ),
    }
