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


def _strip_code_fence(text: str) -> str:
    """Strip a single wrapping markdown code fence (```turtle / ```ttl / ```)."""
    s = text.strip()
    for marker in ("```turtle", "```ttl", "```"):
        if s.startswith(marker):
            content_start = len(marker)
            nl = s.find("\n", content_start)
            content_start = nl + 1 if nl != -1 else content_start
            end = s.rfind("```")
            if end > content_start:
                return s[content_start:end].strip()
            return s[content_start:].strip()
    return s


def _filter_turtle_lines(text: str) -> str:
    """Remove natural-language prose lines that would cause rdflib parse failures.

    ONLY safe to call on TTL that has already failed to parse — applying it to
    valid Turtle can corrupt multi-line triples (e.g. unindented `a owl:Class ;`).

    Keeps lines that:
      - are blank (separators)
      - start with a Turtle syntax character: # @ : _ < ; , . [ ] ( ) " '
      - are indented (continuation lines)
      - start with a known prefix name (e.g. owl:Class, rdfs:subClassOf)
      - are the bare `a` keyword (rdf:type shorthand at column 0)
    Drops lines that start with plain English words (LLM explanatory prose).
    """
    _TURTLE_STARTERS = frozenset('#@:_<;,.[]()"\'`')
    kept = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            kept.append(line)
        elif s[0] in _TURTLE_STARTERS:
            kept.append(line)
        elif line[:1] in (" ", "\t"):
            kept.append(line)
        elif s == "a" or s.startswith(("a ", "a\t")):
            kept.append(line)  # rdf:type shorthand
        elif re.match(r"^[a-zA-Z][a-zA-Z0-9_]*:[a-zA-Z_]", s):
            kept.append(line)  # prefixed name like owl:Class, rdfs:label
        # else: natural language prose — drop
    return "\n".join(kept)


def _is_valid_turtle(ttl: str) -> bool:
    """Return True if the Turtle is syntactically parseable by rdflib."""
    if not ttl.strip():
        return True
    try:
        import rdflib
        rdflib.Graph().parse(data=ttl, format="turtle")
        return True
    except Exception:
        return False


def merge_ontologies(base_ttl: str, delta_oi: str) -> str:
    """Merge delta-Oi into accumulated ontology, deduplicating prefixes."""
    # Defensive: strip any residual code fence that AxiomGenerator may have missed
    delta_oi = _strip_code_fence(delta_oi)
    # If delta_oi fails to parse (e.g. LLM prose mixed in), strip prose-only lines
    # and retry.  ONLY filter on failure — valid Turtle must never be modified.
    if delta_oi.strip() and not _is_valid_turtle(BASE_PREFIXES + "\n" + delta_oi.strip()):
        filtered = _filter_turtle_lines(delta_oi)
        if filtered.strip():
            logger.debug("merge_ontologies: stripped non-Turtle prose lines from delta_oi")
            delta_oi = filtered
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
    """
    Check OWL consistency using rdflib structural checks.

    owlready2 does not parse Turtle reliably, so we use rdflib to:
      1. Verify the TTL is syntactically valid
      2. Detect common OWL inconsistencies:
         - Class declared both disjoint and in subClassOf hierarchy
         - Property with identical domain and range declared disjoint
    Returns True if no inconsistency is detected and TTL parses cleanly.
    """
    if not ontology_ttl or not ontology_ttl.strip():
        return True  # empty ontology has no axioms to violate — structurally valid
    try:
        import rdflib
        g = rdflib.Graph()
        try:
            g.parse(data=ontology_ttl, format="turtle")
        except Exception as parse_err:
            # Parse errors are already surfaced by FQ-PARSE gate; suppress noisy WARNING.
            logger.debug(f"check_consistency: Turtle parse failed (FQ gate handles this): {parse_err}")
            return False

        # Check 1: disjoint classes that also share a subclass
        q_disjoint_subclass = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        ASK {
            ?a owl:disjointWith ?b .
            ?c rdfs:subClassOf ?a .
            ?c rdfs:subClassOf ?b .
            FILTER(?a != ?b && ?a != ?c && ?b != ?c)
        }"""
        if bool(g.query(q_disjoint_subclass)):
            logger.info("check_consistency: disjoint+subClassOf conflict detected")
            return False

        # Check 2: property declared functional with conflicting range disjointness
        q_functional = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        ASK {
            ?p a owl:FunctionalProperty ;
               rdfs:range ?r1 ;
               rdfs:range ?r2 .
            ?r1 owl:disjointWith ?r2 .
            FILTER(?r1 != ?r2)
        }"""
        if bool(g.query(q_functional)):
            logger.info("check_consistency: FunctionalProperty range disjointness conflict detected")
            return False

        return True
    except Exception as e:
        logger.warning(f"check_consistency: unexpected error: {e}")
        return False


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
            def get_depth(cls, cache):
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
