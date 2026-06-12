"""
Deterministic Formal Quality (FQ) checker.

Replaces LLM-based FQ validation with programmatic rdflib checks. Each check
is an objective OWL 2 structural best-practice rule evaluated directly against
the parsed RDF graph — no LLM judgment, fully reproducible.

This removes the n=1 self-referential weakness from FQ validation: a structural
violation is now decided by the OWL/RDF standard, not by the same LLM that
generated the axioms.

Each check has:
  id   — stable identifier (used as the "FQ rule" stored in the Handoff Artifact)
  desc — human-readable description
  fn   — (graph) -> list[str] of concrete violation messages (empty == pass)

Accumulation semantics (paper §3.2.2) are preserved at the gate level: the set
of *active* check ids grows over CQs (self-improving), but each check itself is
a fixed deterministic function.
"""
import logging
from typing import List, Callable, Dict

logger = logging.getLogger(__name__)

OWL = "http://www.w3.org/2002/07/owl#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XSD = "http://www.w3.org/2001/XMLSchema#"

_BASE_PREFIXES = f"""@prefix : <http://coha.org/military#> .
@prefix owl: <{OWL}> .
@prefix rdfs: <{RDFS}> .
@prefix rdf: <{RDF}> .
@prefix xsd: <{XSD}> .
"""


def _parse(delta_oi: str):
    """Parse delta-Oi into an rdflib graph, injecting base prefixes if missing."""
    import rdflib
    text = delta_oi if "@prefix" in delta_oi else _BASE_PREFIXES + "\n" + delta_oi
    g = rdflib.Graph()
    g.parse(data=text, format="turtle")
    return g


def _local(uri) -> str:
    s = str(uri)
    for sep in ("#", "/"):
        if sep in s:
            return s.rsplit(sep, 1)[-1]
    return s


# ── Individual checks (each returns a list of violation messages) ───────────────

def _check_objprop_domain_range(g) -> List[str]:
    """Every owl:ObjectProperty must declare both rdfs:domain and rdfs:range."""
    import rdflib
    OBJ = rdflib.URIRef(OWL + "ObjectProperty")
    DOM = rdflib.URIRef(RDFS + "domain")
    RAN = rdflib.URIRef(RDFS + "range")
    TYPE = rdflib.RDF.type
    out = []
    for p in set(g.subjects(TYPE, OBJ)):
        if (p, DOM, None) not in g:
            out.append(f"ObjectProperty :{_local(p)} is missing rdfs:domain")
        if (p, RAN, None) not in g:
            out.append(f"ObjectProperty :{_local(p)} is missing rdfs:range")
    return out


def _check_datatypeprop_range_xsd(g) -> List[str]:
    """owl:DatatypeProperty range must be an xsd: datatype."""
    import rdflib
    DTP = rdflib.URIRef(OWL + "DatatypeProperty")
    RAN = rdflib.URIRef(RDFS + "range")
    TYPE = rdflib.RDF.type
    out = []
    for p in set(g.subjects(TYPE, DTP)):
        ranges = list(g.objects(p, RAN))
        if not ranges:
            out.append(f"DatatypeProperty :{_local(p)} is missing rdfs:range")
            continue
        for r in ranges:
            if not str(r).startswith(XSD):
                out.append(
                    f"DatatypeProperty :{_local(p)} range :{_local(r)} is not an xsd: datatype"
                )
    return out


def _check_class_has_label(g) -> List[str]:
    """Every owl:Class must have an rdfs:label."""
    import rdflib
    CLS = rdflib.URIRef(OWL + "Class")
    LBL = rdflib.URIRef(RDFS + "label")
    TYPE = rdflib.RDF.type
    out = []
    for c in set(g.subjects(TYPE, CLS)):
        if isinstance(c, rdflib.BNode):
            continue  # anonymous class expressions are exempt
        if (c, LBL, None) not in g:
            out.append(f"Class :{_local(c)} is missing rdfs:label")
    return out


def _check_property_has_label(g) -> List[str]:
    """Every object/datatype property must have an rdfs:label."""
    import rdflib
    LBL = rdflib.URIRef(RDFS + "label")
    TYPE = rdflib.RDF.type
    out = []
    for ptype in ("ObjectProperty", "DatatypeProperty"):
        PT = rdflib.URIRef(OWL + ptype)
        for p in set(g.subjects(TYPE, PT)):
            if (p, LBL, None) not in g:
                out.append(f"Property :{_local(p)} is missing rdfs:label")
    return out


def _check_subclass_target_is_resource(g) -> List[str]:
    """rdfs:subClassOf target must be a class resource, not a literal."""
    import rdflib
    SUB = rdflib.URIRef(RDFS + "subClassOf")
    out = []
    for s, _, o in g.triples((None, SUB, None)):
        if isinstance(o, rdflib.Literal):
            out.append(f"Class :{_local(s)} has rdfs:subClassOf pointing to a literal")
    return out


def _check_no_property_type_conflict(g) -> List[str]:
    """A property must not be both owl:ObjectProperty and owl:DatatypeProperty."""
    import rdflib
    OBJ = rdflib.URIRef(OWL + "ObjectProperty")
    DTP = rdflib.URIRef(OWL + "DatatypeProperty")
    TYPE = rdflib.RDF.type
    obj_props = set(g.subjects(TYPE, OBJ))
    dat_props = set(g.subjects(TYPE, DTP))
    return [
        f"Property :{_local(p)} is declared both ObjectProperty and DatatypeProperty"
        for p in (obj_props & dat_props)
    ]


def _check_class_not_also_property(g) -> List[str]:
    """An entity must not be declared as both a Class and a property (punning abuse)."""
    import rdflib
    CLS = rdflib.URIRef(OWL + "Class")
    TYPE = rdflib.RDF.type
    classes = set(g.subjects(TYPE, CLS))
    props = set()
    for ptype in ("ObjectProperty", "DatatypeProperty"):
        props |= set(g.subjects(TYPE, rdflib.URIRef(OWL + ptype)))
    return [
        f"Entity :{_local(e)} is declared both a Class and a property"
        for e in (classes & props)
    ]


# ── Catalog ─────────────────────────────────────────────────────────────────────

FQ_CHECKS: Dict[str, Dict] = {
    "FQ-OBJPROP-DOMRANGE": {
        "desc": "owl:ObjectProperty must have explicit rdfs:domain and rdfs:range",
        "fn": _check_objprop_domain_range,
    },
    "FQ-DATPROP-XSD-RANGE": {
        "desc": "owl:DatatypeProperty range must be an xsd: datatype",
        "fn": _check_datatypeprop_range_xsd,
    },
    "FQ-CLASS-LABEL": {
        "desc": "owl:Class declarations must include rdfs:label",
        "fn": _check_class_has_label,
    },
    "FQ-PROP-LABEL": {
        "desc": "Object/Datatype properties must include rdfs:label",
        "fn": _check_property_has_label,
    },
    "FQ-SUBCLASS-RESOURCE": {
        "desc": "rdfs:subClassOf target must be a class resource, not a literal",
        "fn": _check_subclass_target_is_resource,
    },
    "FQ-NO-PROP-TYPE-CONFLICT": {
        "desc": "A property must not be both ObjectProperty and DatatypeProperty",
        "fn": _check_no_property_type_conflict,
    },
    "FQ-NO-CLASS-PROP-CONFLICT": {
        "desc": "An entity must not be declared both a Class and a property",
        "fn": _check_class_not_also_property,
    },
}

ALL_CHECK_IDS = list(FQ_CHECKS.keys())


def run_checks(delta_oi: str, check_ids: List[str]) -> Dict[str, List[str]]:
    """Run the given checks against delta-Oi.

    Returns {check_id: [violation messages]} for checks that produced violations.
    A parse failure is itself reported as a violation under 'FQ-PARSE'.
    """
    if not delta_oi or not delta_oi.strip():
        return {}
    try:
        g = _parse(delta_oi)
    except Exception as e:
        return {"FQ-PARSE": [f"delta-Oi is not valid Turtle: {e}"]}

    results = {}
    for cid in check_ids:
        spec = FQ_CHECKS.get(cid)
        if not spec:
            continue
        try:
            violations = spec["fn"](g)
            if violations:
                results[cid] = violations
        except Exception as e:
            logger.warning(f"FQ check {cid} raised: {e}")
    return results


def describe(check_id: str) -> str:
    spec = FQ_CHECKS.get(check_id)
    return f"{check_id}: {spec['desc']}" if spec else check_id
