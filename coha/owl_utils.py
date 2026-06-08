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


def extract_deep_structural_metrics(ontology_ttl: str) -> dict:
    """
    owlready2-based deep structural metrics.

    Computes:
      avg_depth, max_depth  — hierarchy depth statistics
      tangledness           — fraction of classes with >1 parent (multiple inheritance)
      richness              — properties per class ratio
      leaf_ratio            — fraction of classes with no subclasses (leaf nodes)
      num_individuals       — declared owl:NamedIndividual count
    """
    try:
        import owlready2
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False, encoding="utf-8"
        ) as f:
            f.write(ontology_ttl)
            tmp = f.name

        try:
            onto = owlready2.get_ontology(f"file://{tmp}").load()
            classes = list(onto.classes())
            props = list(onto.properties())
            individuals = list(onto.individuals())

            if not classes:
                return _empty_deep_metrics()

            # Build parent map (only named superclasses)
            def named_parents(cls):
                return [
                    p for p in cls.is_a
                    if isinstance(p, owlready2.ThingClass) and p is not owlready2.Thing
                ]

            # Depth via BFS from roots
            def get_depth(cls, cache={}):
                if cls in cache:
                    return cache[cls]
                parents = named_parents(cls)
                if not parents:
                    cache[cls] = 0
                    return 0
                d = 1 + max(get_depth(p, cache) for p in parents)
                cache[cls] = d
                return d

            depth_cache = {}
            depths = [get_depth(c, depth_cache) for c in classes]

            # Tangledness: >1 named parent
            tangled = sum(1 for c in classes if len(named_parents(c)) > 1)

            # Children map for leaf detection
            has_children = set()
            for c in classes:
                for p in named_parents(c):
                    has_children.add(p)
            leaf_count = sum(1 for c in classes if c not in has_children)

            return {
                "avg_depth": round(sum(depths) / len(depths), 3),
                "max_depth": max(depths),
                "tangledness": round(tangled / len(classes), 4),
                "richness": round(len(props) / len(classes), 4),
                "leaf_ratio": round(leaf_count / len(classes), 4),
                "num_individuals": len(individuals),
            }

        finally:
            os.unlink(tmp)

    except ImportError:
        logger.warning("owlready2 not available; skipping deep structural metrics.")
        return _empty_deep_metrics()
    except Exception as e:
        logger.warning(f"Deep structural metrics failed: {e}")
        return _empty_deep_metrics()


def _empty_deep_metrics() -> dict:
    return {
        "avg_depth": 0.0,
        "max_depth": 0,
        "tangledness": 0.0,
        "richness": 0.0,
        "leaf_ratio": 0.0,
        "num_individuals": 0,
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
