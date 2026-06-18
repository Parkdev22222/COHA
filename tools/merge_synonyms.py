"""
Ontology synonym merger: detects and merges semantically equivalent
classes/properties in a COHA-generated TTL using an LLM oracle.

Usage:
    python tools/merge_synonyms.py --onto results/my_ontology.ttl
    python tools/merge_synonyms.py --onto results/my_ontology.ttl --dry-run
    python tools/merge_synonyms.py --onto results/my_ontology.ttl --output merged.ttl
    python tools/merge_synonyms.py --onto results/my_ontology.ttl --gold domain/gold_standard.ttl

Options:
    --onto      Path to input TTL file (required)
    --output    Output path (default: <input>_merged.ttl)
    --gold      Gold standard TTL — prefer its names as canonical where overlap exists
    --dry-run   Show detected synonym groups without modifying anything
    --model     LLM model name (default: reads from config.py)
    --domain    Domain hint for LLM prompt (default: "military tactical operations")
"""
import argparse
import json
import logging
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TTL parsing helpers
# ---------------------------------------------------------------------------

def _local_name(uri: str) -> str:
    for sep in ("#", "/"):
        if sep in uri:
            return uri.rsplit(sep, 1)[-1]
    return uri


def _extract_elements(ttl_path: str) -> Tuple[Dict, Dict, Dict, Dict, str]:
    """
    Parse TTL and return (classes, object_props, datatype_props, individuals, base_ns).
    Each dict maps  uri → local_name.
    """
    import rdflib
    from coha.owl_utils import repair_turtle

    raw = open(ttl_path, encoding="utf-8").read()
    g = rdflib.Graph()
    try:
        g.parse(data=raw, format="turtle")
    except Exception as first_err:
        logger.warning("TTL parse error — attempting auto-repair: %s", first_err)
        repaired = repair_turtle(raw)
        if not repaired.strip():
            raise ValueError(f"Could not repair {ttl_path}: {first_err}") from first_err
        try:
            g.parse(data=repaired, format="turtle")
            logger.info("Auto-repair succeeded; repaired TTL loaded.")
        except Exception as second_err:
            raise ValueError(
                f"Auto-repair of {ttl_path} still failed: {second_err}"
            ) from second_err

    OWL  = rdflib.OWL
    RDFS = rdflib.RDFS
    RDF  = rdflib.RDF

    _SKIP_NS  = (str(OWL), str(RDFS), str(RDF), "http://www.w3.org/2001/XMLSchema#")
    _SKIP_URI = {str(OWL.Thing), str(RDFS.Resource), str(RDFS.Class)}

    def _keep(uri_str):
        return uri_str not in _SKIP_URI and not any(uri_str.startswith(n) for n in _SKIP_NS)

    # Detect base namespace (most common non-builtin prefix)
    base_ns = ""
    ns_counts: Dict[str, int] = {}
    for s in g.subjects():
        if isinstance(s, rdflib.URIRef):
            u = str(s)
            if _keep(u):
                for sep in ("#", "/"):
                    idx = u.rfind(sep)
                    if idx >= 0:
                        ns = u[:idx + 1]
                        ns_counts[ns] = ns_counts.get(ns, 0) + 1
                        break
    if ns_counts:
        base_ns = max(ns_counts, key=ns_counts.__getitem__)

    classes, obj_props, dat_props, individuals = {}, {}, {}, {}

    for s in g.subjects(RDF.type, OWL.Class):
        if isinstance(s, rdflib.URIRef) and _keep(str(s)):
            classes[str(s)] = _local_name(str(s))

    # Infer classes from rdfs:subClassOf
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        for u in (s, o):
            if isinstance(u, rdflib.URIRef) and _keep(str(u)) and str(u) not in classes:
                classes[str(u)] = _local_name(str(u))

    for p in g.subjects(RDF.type, OWL.ObjectProperty):
        if isinstance(p, rdflib.URIRef) and _keep(str(p)):
            obj_props[str(p)] = _local_name(str(p))

    # Infer object properties from rdfs:domain (no explicit typing)
    _XSD = "http://www.w3.org/2001/XMLSchema#"
    for p in g.subjects(RDFS.domain, None):
        if not isinstance(p, rdflib.URIRef) or not _keep(str(p)) or str(p) in obj_props:
            continue
        range_val = g.value(p, RDFS.range)
        if range_val and str(range_val).startswith(_XSD):
            continue
        obj_props[str(p)] = _local_name(str(p))

    for p in g.subjects(RDF.type, OWL.DatatypeProperty):
        if isinstance(p, rdflib.URIRef) and _keep(str(p)):
            dat_props[str(p)] = _local_name(str(p))

    for s in g.subjects(RDF.type, OWL.NamedIndividual):
        if isinstance(s, rdflib.URIRef) and _keep(str(s)):
            individuals[str(s)] = _local_name(str(s))

    return classes, obj_props, dat_props, individuals, base_ns


def _count_uri_occurrences(ttl_path: str) -> Dict[str, int]:
    """Count how many triples each URI appears in (as subject or object)."""
    import rdflib
    g = rdflib.Graph()
    g.parse(ttl_path, format="turtle")
    counts: Dict[str, int] = {}
    for s, p, o in g:
        for node in (s, p, o):
            if isinstance(node, rdflib.URIRef):
                u = str(node)
                counts[u] = counts.get(u, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# LLM synonym detection
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an ontology engineer. Your task is to find semantically equivalent
(synonym) ontology elements — i.e. elements that represent the SAME concept
but use different names. Focus on domain-level equivalence, not just superficial
similarity. Only flag pairs/groups that are genuinely the same concept.\
"""


def _build_user_prompt(
    class_locals: List[str],
    objprop_locals: List[str],
    datprop_locals: List[str],
    domain_hint: str,
) -> str:
    lines = [
        f"Domain: {domain_hint}",
        "",
        "Below are the ontology elements. Identify groups of elements that are "
        "semantically equivalent (same concept, different names). "
        "Only group elements of the same kind (class with class, property with property).",
        "",
    ]
    if class_locals:
        lines.append("Classes:")
        for c in sorted(class_locals):
            lines.append(f"  - {c}")
        lines.append("")
    if objprop_locals:
        lines.append("Object Properties:")
        for p in sorted(objprop_locals):
            lines.append(f"  - {p}")
        lines.append("")
    if datprop_locals:
        lines.append("Datatype Properties:")
        for p in sorted(datprop_locals):
            lines.append(f"  - {p}")
        lines.append("")
    lines += [
        'Return ONLY a valid JSON object (no prose, no markdown fences):',
        '{',
        '  "class_synonyms": [["NameA", "NameB"], ...],',
        '  "property_synonyms": [["propA", "propB"], ...]',
        '}',
        'Include a group only if it has 2+ elements. '
        'If nothing is equivalent, return empty lists.',
    ]
    return "\n".join(lines)


def _call_llm(system: str, user: str, model: Optional[str]) -> str:
    from llm_client import UnifiedLLMClient
    client = UnifiedLLMClient(model) if model else UnifiedLLMClient()
    logger.info(f"Querying LLM ({client.model_name}) for synonym detection…")
    return client.generate(system=system, user=user, max_tokens=2048)


def _parse_llm_response(response: str) -> Tuple[List[List[str]], List[List[str]]]:
    """Extract class_synonyms and property_synonyms from LLM JSON response."""
    # Strip markdown fences if present
    text = re.sub(r"```(?:json)?", "", response).strip()
    # Find first { ... } block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        logger.warning("LLM response contained no JSON object")
        return [], []
    try:
        data = json.loads(m.group())
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM JSON: {e}")
        return [], []
    class_syn  = data.get("class_synonyms",    [])
    prop_syn   = data.get("property_synonyms", [])
    # Normalise: each group must be a list of >= 2 strings
    def _clean(groups):
        result = []
        for g in groups:
            if isinstance(g, list) and len(g) >= 2:
                result.append([str(x) for x in g])
        return result
    return _clean(class_syn), _clean(prop_syn)


# ---------------------------------------------------------------------------
# Canonical name selection
# ---------------------------------------------------------------------------

def _pick_canonical(
    group: List[str],
    uri_map: Dict[str, str],      # local_name → uri
    occ_counts: Dict[str, int],   # uri → occurrence count
    gold_locals: set,             # local names from gold standard TTL (preferred)
) -> str:
    """
    Pick the canonical name for a synonym group.
    Priority: gold standard name > most occurrences in graph > alphabetical first.
    """
    gold_hits = [n for n in group if n in gold_locals]
    if gold_hits:
        return gold_hits[0]

    def _occ(local):
        uri = uri_map.get(local, "")
        return occ_counts.get(uri, 0)

    best = max(group, key=lambda n: (_occ(n), -len(n)))
    return best


# ---------------------------------------------------------------------------
# TTL rewriting
# ---------------------------------------------------------------------------

def _build_uri_map(
    classes: Dict[str, str],
    obj_props: Dict[str, str],
    dat_props: Dict[str, str],
    individuals: Dict[str, str],
) -> Dict[str, str]:
    """local_name → uri (first one wins on collision)."""
    result = {}
    for dct in (classes, obj_props, dat_props, individuals):
        for uri, local in dct.items():
            if local not in result:
                result[local] = uri
    return result


def _apply_merges(
    ttl_path: str,
    class_groups: List[Tuple[str, List[str]]],   # (canonical_uri, [alias_uri, ...])
    prop_groups:  List[Tuple[str, List[str]]],
) -> str:
    """
    Rewrite the TTL:
    - Replace every alias URI with canonical URI
    - Add owl:equivalentClass / owl:equivalentProperty axioms (informational)
    Returns the new TTL text.
    """
    import rdflib
    from rdflib.namespace import OWL, RDF, RDFS

    g = rdflib.Graph()
    g.parse(ttl_path, format="turtle")

    # Build full alias→canonical URI map
    replace: Dict[str, str] = {}
    for canonical_uri, aliases in class_groups + prop_groups:
        for alias in aliases:
            replace[alias] = canonical_uri

    if not replace:
        logger.info("No merges to apply.")
        with open(ttl_path, encoding="utf-8") as f:
            return f.read()

    # Rebuild the graph with remapped URIs
    new_g = rdflib.Graph()
    # Copy namespace bindings
    for prefix, ns in g.namespaces():
        new_g.bind(prefix, ns)

    def _remap(node):
        if isinstance(node, rdflib.URIRef) and str(node) in replace:
            return rdflib.URIRef(replace[str(node)])
        return node

    for s, p, o in g:
        new_g.add((_remap(s), _remap(p), _remap(o)))

    # Add informational equivalence axioms
    for canonical_uri, aliases in class_groups:
        for alias in aliases:
            new_g.add((rdflib.URIRef(canonical_uri), OWL.equivalentClass,
                       rdflib.URIRef(alias)))
    for canonical_uri, aliases in prop_groups:
        for alias in aliases:
            new_g.add((rdflib.URIRef(canonical_uri), OWL.equivalentProperty,
                       rdflib.URIRef(alias)))

    return new_g.serialize(format="turtle")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(
    onto_path: str,
    output_path: Optional[str],
    gold_path: Optional[str],
    dry_run: bool,
    model: Optional[str],
    domain_hint: str,
) -> None:
    if not os.path.exists(onto_path):
        logger.error(f"File not found: {onto_path}")
        sys.exit(1)

    logger.info(f"Parsing: {onto_path}")
    classes, obj_props, dat_props, individuals, base_ns = _extract_elements(onto_path)
    occ_counts = _count_uri_occurrences(onto_path)

    logger.info(
        f"Found: {len(classes)} classes, {len(obj_props)} obj-props, "
        f"{len(dat_props)} data-props, {len(individuals)} individuals"
    )

    # Gold standard names (preferred as canonical)
    gold_locals: set = set()
    if gold_path and os.path.exists(gold_path):
        _, gop, gdp, _, _ = _extract_elements(gold_path)
        _, gcl, _, _, _ = _extract_elements(gold_path)
        gold_locals = set(gcl.values()) | set(gop.values()) | set(gdp.values())
        logger.info(f"Gold standard: {len(gold_locals)} reference names loaded")

    # Build local→uri map
    uri_map = _build_uri_map(classes, obj_props, dat_props, individuals)

    # Ask LLM
    user_prompt = _build_user_prompt(
        class_locals=list(classes.values()),
        objprop_locals=list(obj_props.values()),
        datprop_locals=list(dat_props.values()),
        domain_hint=domain_hint,
    )
    raw_response = _call_llm(_SYSTEM_PROMPT, user_prompt, model)
    logger.debug(f"LLM raw response:\n{raw_response}")

    class_syn_groups, prop_syn_groups = _parse_llm_response(raw_response)

    if not class_syn_groups and not prop_syn_groups:
        logger.info("No synonym groups detected by LLM.")
        return

    # Resolve canonical names and build merge plan
    print("\n" + "="*60)
    print("DETECTED SYNONYM GROUPS")
    print("="*60)

    class_merges: List[Tuple[str, List[str]]] = []   # (canonical_uri, [alias_uri])
    prop_merges:  List[Tuple[str, List[str]]] = []

    def _resolve_group(group: List[str], kind: str, dct: Dict[str, str]) -> Optional[Tuple[str, List[str]]]:
        # Filter to names actually present in the ontology
        present = [n for n in group if n in uri_map]
        if len(present) < 2:
            logger.warning(f"Synonym group {group} has <2 members in ontology — skipping")
            return None
        canonical = _pick_canonical(present, uri_map, occ_counts, gold_locals)
        aliases   = [n for n in present if n != canonical]
        canon_uri = uri_map[canonical]
        alias_uris = [uri_map[a] for a in aliases]
        print(f"\n[{kind}] Canonical: {canonical}")
        for a in aliases:
            occ = occ_counts.get(uri_map[a], 0)
            print(f"         Merge ← {a}  (occurrences: {occ})")
        return canon_uri, alias_uris

    for group in class_syn_groups:
        result = _resolve_group(group, "CLASS", classes)
        if result:
            class_merges.append(result)

    for group in prop_syn_groups:
        result = _resolve_group(group, "PROP", obj_props)
        if result:
            prop_merges.append(result)

    total_merges = sum(len(a) for _, a in class_merges + prop_merges)
    print(f"\nTotal: {total_merges} URI(s) will be replaced")
    print("="*60)

    if dry_run:
        print("\n[dry-run] No changes written.")
        return

    if total_merges == 0:
        print("Nothing to merge.")
        return

    # Apply merges
    logger.info("Applying merges to TTL…")
    new_ttl = _apply_merges(onto_path, class_merges, prop_merges)

    # Write output
    if output_path is None:
        stem, ext = os.path.splitext(onto_path)
        output_path = stem + "_merged.ttl"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(new_ttl)

    logger.info(f"Saved merged ontology → {output_path}")

    # Summary
    print(f"\nMerged TTL saved: {output_path}")
    print(f"  Classes merged:    {sum(len(a) for _, a in class_merges)}")
    print(f"  Properties merged: {sum(len(a) for _, a in prop_merges)}")


def main():
    parser = argparse.ArgumentParser(
        description="Detect and merge synonym classes/properties in a COHA-generated TTL"
    )
    parser.add_argument("--onto",    required=True, help="Input TTL file path")
    parser.add_argument("--output",  default=None,  help="Output TTL path (default: <input>_merged.ttl)")
    parser.add_argument("--gold",    default=None,  help="Gold standard TTL — prefer its names as canonical")
    parser.add_argument("--dry-run", action="store_true", help="Show synonym groups without writing output")
    parser.add_argument("--model",   default=None,  help="LLM model name (default: from config.py)")
    parser.add_argument("--domain",  default="military tactical operations",
                        help="Domain hint for LLM prompt")
    args = parser.parse_args()

    run(
        onto_path=args.onto,
        output_path=args.output,
        gold_path=args.gold,
        dry_run=args.dry_run,
        model=args.model,
        domain_hint=args.domain,
    )


if __name__ == "__main__":
    main()
