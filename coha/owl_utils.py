"""
OWL utilities: merge ontologies, check consistency, compute structural metrics.
"""
import re
import logging

logger = logging.getLogger(__name__)

BASE_PREFIXES = """@prefix : <http://coha.org/military#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

<http://coha.org/military> a owl:Ontology ;
    rdfs:label "Military Tactical Ontology" .

"""


def merge_ontologies(base_ttl: str, delta_oi: str) -> str:
    """Merge delta-Oi into accumulated ontology, deduplicating prefixes."""
    if not base_ttl.strip():
        return BASE_PREFIXES + "\n" + delta_oi.strip()
    if not delta_oi.strip():
        return base_ttl

    existing_prefixes = set(re.findall(r"@prefix\s+\S+\s+<[^>]+>\s*\.", base_ttl))
    filtered_lines = []
    for line in delta_oi.strip().split("\n"):
        if re.match(r"@prefix\s+", line):
            if line.strip() not in existing_prefixes:
                filtered_lines.append(line)
                existing_prefixes.add(line.strip())
        else:
            filtered_lines.append(line)

    delta_clean = "\n".join(filtered_lines).strip()
    if not delta_clean:
        return base_ttl
    return base_ttl.rstrip() + "\n\n# --- CQ delta ---\n" + delta_clean + "\n"


def check_consistency(ontology_ttl: str) -> bool:
    """Check OWL consistency using owlready2. Returns True if consistent."""
    try:
        import owlready2
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False, encoding="utf-8") as f:
            f.write(ontology_ttl)
            tmp = f.name
        try:
            onto = owlready2.get_ontology(f"file://{tmp}").load()
            with onto:
                owlready2.sync_reasoner_hermit(infer_property_values=False)
            return True
        except Exception:
            return False
        finally:
            os.unlink(tmp)
    except ImportError:
        logger.warning("owlready2 not available; skipping consistency check.")
        return True


def extract_structural_metrics(ontology_ttl: str) -> dict:
    """Extract structural quality metrics from Turtle source."""
    n_classes = len(set(re.findall(r"(\S+)\s+a\s+owl:Class", ontology_ttl)))
    n_obj_props = len(set(re.findall(r"(\S+)\s+a\s+owl:ObjectProperty", ontology_ttl)))
    n_dat_props = len(set(re.findall(r"(\S+)\s+a\s+owl:DatatypeProperty", ontology_ttl)))
    n_subclass = len(re.findall(r"rdfs:subClassOf", ontology_ttl))
    n_disjoint = len(re.findall(r"owl:disjointWith", ontology_ttl))
    return {
        "n_classes": n_classes,
        "n_object_properties": n_obj_props,
        "n_datatype_properties": n_dat_props,
        "n_subclass_axioms": n_subclass,
        "n_disjoint_axioms": n_disjoint,
        "total_axioms": n_classes + n_obj_props + n_dat_props + n_subclass + n_disjoint,
    }


def extract_class_names(ontology_ttl: str) -> list:
    """Extract declared class local names from Turtle."""
    names = []
    for m in re.finditer(r":([A-Z][a-zA-Z0-9_]+)\s+a\s+owl:Class", ontology_ttl):
        names.append(m.group(1))
    return list(dict.fromkeys(names))


def extract_property_names(ontology_ttl: str) -> list:
    names = []
    for pattern in [r":([a-z][a-zA-Z0-9_]+)\s+a\s+owl:ObjectProperty",
                    r":([a-z][a-zA-Z0-9_]+)\s+a\s+owl:DatatypeProperty"]:
        for m in re.finditer(pattern, ontology_ttl):
            names.append(m.group(1))
    return list(dict.fromkeys(names))
