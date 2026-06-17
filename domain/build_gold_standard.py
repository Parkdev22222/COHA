"""
Build gold standard ontology from ADP 3-90 PDF using Ontogenia-style extraction.

Usage:
    # PDF를 domain/ADP_3-90.pdf 에 놓고 실행
    python domain/build_gold_standard.py

    # 다른 모델로 실행
    python domain/build_gold_standard.py --model claude-sonnet-4-6

Output:
    domain/gold_standard.ttl  (GOLD_STANDARD_TTL 자동 로드됨)
"""
import argparse
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Repo root를 sys.path에 추가 (어느 디렉토리에서 실행해도 동작)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

PDF_PATH = os.path.join(os.path.dirname(__file__), "ADP_3-90.pdf")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "gold_standard.ttl")

BASE_PREFIXES = """@prefix : <http://coha.org/military#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> ."""


def _extract_turtle(text: str) -> str:
    """Extract Turtle from LLM response (handles code fences)."""
    for marker in ["```turtle", "```ttl"]:
        if marker in text:
            start = text.find(marker) + len(marker)
            end = text.find("```", start)
            return text[start:end].strip() if end != -1 else text[start:].strip()
    if "```" in text:
        start = text.find("```") + 3
        nl = text.find("\n", start)
        start = nl + 1 if nl != -1 else start
        end = text.find("```", start)
        return text[start:end].strip() if end != -1 else text[start:].strip()
    return text.strip()


def _subdomain_guidance(subdomain: str) -> str:
    """Return extra prompt guidance tailored to each subdomain."""
    if subdomain == "tactical_prescriptions":
        return (
            "SPECIAL FOCUS — UNIT MATCHUPS AND TACTICAL PRESCRIPTIONS:\n"
            "This subdomain requires explicit modelling of:\n"
            "  A) UNIT MATCHUPS (병종 상성): Which unit types defeat which in which terrain?\n"
            "     - Create :UnitMatchup class linking two unit types and a terrain context\n"
            "     - Use :effectiveAgainst (domain :Unit, range :Unit) for superiority\n"
            "     - Use :vulnerableTo (domain :Unit, range :Unit) for disadvantage\n"
            "     - Example: Armor :effectiveAgainst Infantry in OpenTerrain\n"
            "       but Infantry :effectiveAgainst Armor in UrbanTerrain/ForestTerrain\n"
            "     - Aviation :vulnerableTo in MountainTerrain, ForestTerrain (low ceiling)\n"
            "     - Engineer supports Armor in BreachOperation\n"
            "  B) REQUIRED ACTIONS (해야 할 것) per operation type:\n"
            "     - :RequiredAction (subClassOf :TacticalPrescription)\n"
            "     - Must link to :FormOfManeuver or :Mission via :appliesTo / :appliesToManeuver\n"
            "     - Examples: Penetration requires suppression of flanks before exploitation;\n"
            "       MobileDefense requires FixingForce before committing StrikeForce;\n"
            "       TurningMovement requires FixingForce to pin enemy\n"
            "  C) FORBIDDEN ACTIONS (하지 말아야 할 것) per operation type:\n"
            "     - :ForbiddenAction (subClassOf :TacticalPrescription)\n"
            "     - Envelopment: do NOT halt the enveloping force — loss of momentum\n"
            "     - Delay: do NOT become decisively engaged\n"
            "     - Exploitation: do NOT pause to consolidate prematurely\n"
            "     - Withdrawal under pressure: do NOT withdraw without a covering force\n"
            "  D) COURSE OF ACTION CONSTRAINTS:\n"
            "     - :CourseOfAction, :COAConstraint, :OperationalConstraint, :TacticalConstraint\n"
            "     - Armor in UrbanTerrain without Infantry support is a doctrinal violation\n"
            "     - Reconnaissance units must NOT be committed to direct combat\n\n"
        )
    return ""


def build_gold_standard(pdf_text: str, cqs: list, llm_client) -> str:
    """
    Ontogenia-style gold standard extraction.

    Two-pass:
      Pass 1 (per-subdomain): Reflect on needed concepts → extract OWL axioms
      Pass 2 (merge + complete): Merge all passes, fill gaps against full CQ list
    """
    from coha.owl_utils import merge_ontologies

    # Group CQs by subdomain
    from collections import defaultdict
    by_subdomain = defaultdict(list)
    for cq in cqs:
        by_subdomain[cq.get("subdomain", "general")].append(cq)

    # Use first 8000 chars of PDF as doctrine excerpt (fit in prompt)
    doc_excerpt = pdf_text[:8000] if pdf_text else ""

    all_ttls = [BASE_PREFIXES]

    # Pass 1: per-subdomain Ontogenia-style extraction
    for subdomain, sd_cqs in by_subdomain.items():
        cq_list = "\n".join(
            f"  - [{cq['id']}] {cq['question']}  key_entities: {cq.get('key_entities', [])}"
            for cq in sd_cqs
        )
        # Subdomain-specific guidance injected into prompt
        extra_guidance = _subdomain_guidance(subdomain)

        prompt = (
            "You are a military ontology expert constructing a gold standard ontology "
            "from published US Army doctrine (ADP 3-90 Offense and Defense).\n\n"
            f"DOCTRINE EXCERPT:\n{doc_excerpt}\n\n"
            f"SUBDOMAIN: {subdomain}\n"
            f"COMPETENCY QUESTIONS TO COVER:\n{cq_list}\n\n"
            f"{extra_guidance}"
            "STEP 1 — Reflect (3-5 sentences):\n"
            "  What classes, object properties, and datatype properties are needed "
            "to formally answer ALL the above CQs? What doctrine concepts must be captured?\n\n"
            "STEP 2 — Generate OWL axioms (after the marker GENERATE:):\n"
            "Requirements:\n"
            "1. Use @prefix : <http://coha.org/military#>\n"
            "2. Every key_entity MUST appear as owl:Class or owl:ObjectProperty\n"
            "3. Every owl:ObjectProperty MUST have rdfs:domain and rdfs:range\n"
            "4. Every owl:DatatypeProperty MUST have rdfs:domain and xsd: range\n"
            "5. Every class and property MUST have rdfs:label AND rdfs:comment\n"
            "6. Include rdfs:subClassOf hierarchies where doctrine supports it\n"
            "7. Return ONLY valid Turtle after GENERATE: — no markdown, no prose\n\n"
            "Write your reflection, then GENERATE:"
        )
        try:
            raw = llm_client.generate(system="", user=prompt, max_tokens=4096)
            if "GENERATE:" in raw:
                turtle_part = raw.split("GENERATE:", 1)[1].strip()
            else:
                turtle_part = raw
            ttl = _extract_turtle(turtle_part)
            if ttl.strip():
                all_ttls.append(ttl)
                logger.info(f"  [{subdomain}] extracted {len(ttl)} chars of Turtle")
        except Exception as e:
            logger.error(f"  [{subdomain}] extraction failed: {e}")

    # Merge all sub-domain TTLs
    merged = BASE_PREFIXES
    for ttl in all_ttls[1:]:
        merged = merge_ontologies(merged, ttl)

    # Pass 2: completeness check — fill any missing key_entities
    all_entities = sorted(set(
        e for cq in cqs for e in cq.get("key_entities", [])
    ))
    completion_prompt = (
        "You are completing a military OWL 2 gold standard ontology.\n\n"
        f"CURRENT ONTOLOGY:\n```turtle\n{merged[:6000]}\n```\n\n"
        f"ALL REQUIRED key_entities (must each appear as owl:Class or owl:ObjectProperty):\n"
        + "\n".join(f"  :{e}" for e in all_entities)
        + "\n\nAdd ONLY the missing declarations. "
        "Every new owl:ObjectProperty needs rdfs:domain, rdfs:range, and rdfs:label. "
        "Every new owl:Class needs rdfs:label.\n"
        "Return ONLY the NEW axioms in Turtle format (no prefixes, no existing axioms):"
    )
    try:
        raw2 = llm_client.generate(system="", user=completion_prompt, max_tokens=3000)
        patch = _extract_turtle(raw2)
        if patch.strip():
            merged = merge_ontologies(merged, patch)
            logger.info(f"Pass 2 patch: {len(patch)} chars added")
    except Exception as e:
        logger.warning(f"Pass 2 completion failed: {e}")

    # Pass 3: Tactical prescriptions deep-extraction
    # Explicitly generates unit matchup triples and Required/Forbidden action instances
    prescription_prompt = (
        "You are a military ontology expert. "
        "Extend the ontology below with TACTICAL PRESCRIPTIONS drawn from ADP 3-90.\n\n"
        f"CURRENT ONTOLOGY (excerpt):\n```turtle\n{merged[:4000]}\n```\n\n"
        "Generate NEW Turtle axioms covering ALL of the following — do not repeat existing ones:\n\n"
        "1. UNIT MATCHUP RULES (병종 상성) — use :effectiveAgainst and :vulnerableTo:\n"
        "   - Armor effective against Infantry in OpenTerrain and DesertTerrain\n"
        "   - Infantry effective against Armor in UrbanTerrain and ForestTerrain\n"
        "   - Aviation vulnerable to ForestTerrain and MountainTerrain (low ceiling)\n"
        "   - FieldArtillery effective against any unit in OpenTerrain (range advantage)\n"
        "   - SpecialForcesUnit effective against EnemyUnit in denied/complex terrain\n"
        "   - EngineerUnit counters ObstacleBelt (enables Armor in BreachOperation)\n\n"
        "2. REQUIRED ACTIONS (RequiredAction instances) per form of maneuver:\n"
        "   For each: link to FormOfManeuver via :appliesToManeuver, set :isRequired true,\n"
        "   set rdfs:label and :prescriptionText.\n"
        "   - Penetration: suppress flanks before exploitation; mass combat power at breach point\n"
        "   - Envelopment: fix enemy frontally; maintain communication with enveloping force\n"
        "   - TurningMovement: employ FixingForce to hold enemy; threaten logistics\n"
        "   - MobileDefense: establish FixingForce before committing StrikeForce\n"
        "   - Infiltration: maintain noise/light discipline; move at night\n\n"
        "3. FORBIDDEN ACTIONS (ForbiddenAction instances) per operation:\n"
        "   For each: link to Mission or FormOfManeuver, set :isProhibited true,\n"
        "   set rdfs:label and :prescriptionText.\n"
        "   - Delay: do NOT become decisively engaged; do NOT hold ground at all cost\n"
        "   - Exploitation: do NOT halt prematurely; do NOT consolidate before objective secured\n"
        "   - Withdrawal: do NOT withdraw without covering force; do NOT abandon equipment\n"
        "   - Envelopment: do NOT allow enveloping force to be halted or fixed\n"
        "   - UrbanTerrain Armor: do NOT employ armor without infantry support\n\n"
        "4. COA CONSTRAINTS (COAConstraint instances):\n"
        "   - Armor-without-infantry in UrbanTerrain is a doctrinal violation (ForbiddenAction)\n"
        "   - Reconnaissance units committed to direct combat is a ForbiddenAction\n"
        "   - Reserve commitment requires DecisionPoint confirmation (RequiredAction)\n\n"
        "Return ONLY the NEW Turtle axioms (no prefixes, no existing axioms).\n"
        "Every new class needs rdfs:label and rdfs:comment.\n"
        "Every new property needs rdfs:domain, rdfs:range, and rdfs:label."
    )
    try:
        raw3 = llm_client.generate(system="", user=prescription_prompt, max_tokens=4096)
        patch3 = _extract_turtle(raw3)
        if patch3.strip():
            merged = merge_ontologies(merged, patch3)
            logger.info(f"Pass 3 (prescriptions) patch: {len(patch3)} chars added")
    except Exception as e:
        logger.warning(f"Pass 3 prescription extraction failed: {e}")

    return merged


def main():
    parser = argparse.ArgumentParser(description="Build gold standard from ADP 3-90 PDF")
    parser.add_argument("--model", default=None, help="Override model (e.g. claude-sonnet-4-6)")
    parser.add_argument("--pdf", default=PDF_PATH, help="Path to doctrine PDF")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Output TTL path")
    args = parser.parse_args()

    # Load PDF
    if not os.path.exists(args.pdf):
        print(f"ERROR: PDF not found at {args.pdf}")
        print(f"Place ADP_3-90.pdf at: {PDF_PATH}")
        sys.exit(1)

    print(f"Loading PDF: {args.pdf}")
    from domain.pdf_loader import load_pdf_text
    pdf_text = load_pdf_text(args.pdf)
    print(f"  Extracted {len(pdf_text)} chars from PDF")

    # Load CQs
    from domain.military_cq_benchmark import ALL_CQS
    print(f"  {len(ALL_CQS)} CQs loaded")

    # Setup LLM client
    import config
    if args.model:
        config.MODEL_NAME = args.model

    if config.MODEL_NAME.startswith("claude") and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    from llm_client import get_client
    client = get_client()
    print(f"  Model: {config.MODEL_NAME}")

    # Build
    print("\nBuilding gold standard (Ontogenia-style, 2-pass)...")
    ttl = build_gold_standard(pdf_text, ALL_CQS, client)

    # Save
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(ttl)
    print(f"\nSaved: {args.output} ({len(ttl)} chars)")

    # Quick stats
    n_classes = ttl.count("a owl:Class")
    n_props = ttl.count("owl:ObjectProperty") + ttl.count("owl:DatatypeProperty")
    print(f"  ~{n_classes} classes, ~{n_props} properties")


if __name__ == "__main__":
    main()
