"""
Ontology visualizer: reads a TTL file and generates an interactive HTML graph.

Visualizes classes, named individuals, subClassOf hierarchy, and ALL object
property assertions including bridge instances (suitedForTerrain, preferredUnitType,
effectiveInTerrain, requiredSupportUnit, constrainedByTerrain, etc.).

Usage:
    python tools/visualize_ontology.py domain/gold_standard.ttl
    python tools/visualize_ontology.py results/COHA_full_exp.json --output viz.html
    python tools/visualize_ontology.py results/COHA_full_exp.json --compare domain/gold_standard.ttl

Output: <input_stem>_viz.html  (open in browser or display in Colab)

In Colab:
    from tools.visualize_ontology import visualize_to_html, show_in_colab
    html = visualize_to_html("domain/gold_standard.ttl")
    show_in_colab(html)
"""
import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ---------------------------------------------------------------------------
# TTL parsing (rdflib-based, with lightweight regex fallback)
# ---------------------------------------------------------------------------

def _local_name(uri: str) -> str:
    for sep in ("#", "/"):
        if sep in uri:
            return uri.rsplit(sep, 1)[-1]
    return uri


def parse_ontology(ttl_text: str) -> Dict:
    """
    Parse Turtle ontology text.
    Returns dict: classes, individuals, object_props, datatype_props,
                  subclass_edges, prop_edges, stats
    prop_edges entries: {source, target, label, local, edge_kind}
      edge_kind = "schema"   — from declared rdfs:domain / rdfs:range
      edge_kind = "instance" — actual named-individual triple (bridge instances)
    """
    try:
        return _parse_with_rdflib(ttl_text)
    except Exception:
        return _parse_with_regex(ttl_text)


def _parse_with_rdflib(ttl_text: str) -> Dict:
    import rdflib
    OWL  = rdflib.OWL
    RDFS = rdflib.RDFS
    RDF  = rdflib.RDF

    g = rdflib.Graph()
    g.parse(data=ttl_text, format="turtle")

    # Namespaces / URIs to treat as built-ins (never add as user-defined nodes)
    _SKIP_NS  = (str(OWL), str(RDFS), str(RDF), "http://www.w3.org/2001/XMLSchema#")
    _SKIP_URI = {str(OWL.Thing), str(RDFS.Resource), str(RDFS.Class)}
    _XSD_NS   = "http://www.w3.org/2001/XMLSchema#"

    def _domain_uri(uri_str: str) -> bool:
        return uri_str not in _SKIP_URI and not any(uri_str.startswith(n) for n in _SKIP_NS)

    def _make_class(uri: rdflib.URIRef) -> dict:
        local   = _local_name(str(uri))
        label   = str(g.value(uri, RDFS.label)   or local)
        comment = str(g.value(uri, RDFS.comment) or "")
        return {"id": str(uri), "local": local, "label": label,
                "comment": comment, "node_type": "class"}

    # ---- 1. Explicit OWL/RDFS Classes ----
    classes = {}
    for rdf_type in (OWL.Class, RDFS.Class):
        for s in g.subjects(RDF.type, rdf_type):
            if isinstance(s, rdflib.URIRef) and _domain_uri(str(s)):
                classes[str(s)] = _make_class(s)

    # ---- 2. Infer classes from rdfs:subClassOf (many TTLs omit a owl:Class) ----
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        for uri in (s, o):
            if isinstance(uri, rdflib.URIRef) and _domain_uri(str(uri)) and str(uri) not in classes:
                classes[str(uri)] = _make_class(uri)

    # ---- 3. Named Individuals ----
    individuals = {}
    for s in g.subjects(RDF.type, OWL.NamedIndividual):
        if isinstance(s, rdflib.URIRef):
            local   = _local_name(str(s))
            label   = str(g.value(s, RDFS.label)   or local)
            comment = str(g.value(s, RDFS.comment) or "")
            types   = [_local_name(str(o)) for o in g.objects(s, RDF.type)
                       if str(o) != str(OWL.NamedIndividual)]
            individuals[str(s)] = {"id": str(s), "local": local, "label": label,
                                    "comment": comment, "types": types,
                                    "node_type": "individual"}

    # ---- 4. Explicit Object Properties ----
    object_props = {}
    for p in g.subjects(RDF.type, OWL.ObjectProperty):
        if isinstance(p, rdflib.URIRef):
            local   = _local_name(str(p))
            label   = str(g.value(p, RDFS.label)   or local)
            domain  = str(g.value(p, RDFS.domain)  or "")
            range_  = str(g.value(p, RDFS.range)   or "")
            object_props[str(p)] = {"id": str(p), "local": local, "label": label,
                                     "domain": domain, "range": range_}

    # ---- 5. Infer object properties from rdfs:domain (without explicit typing) ----
    for p_uri in g.subjects(RDFS.domain, None):
        if not isinstance(p_uri, rdflib.URIRef) or not _domain_uri(str(p_uri)):
            continue
        if str(p_uri) in object_props:
            continue
        range_val = g.value(p_uri, RDFS.range)
        # Skip if range is an XSD literal type → it's a datatype property
        if range_val and isinstance(range_val, rdflib.URIRef) and str(range_val).startswith(_XSD_NS):
            continue
        local  = _local_name(str(p_uri))
        label  = str(g.value(p_uri, RDFS.label) or local)
        domain = str(g.value(p_uri, RDFS.domain) or "")
        range_ = str(range_val) if isinstance(range_val, rdflib.URIRef) else ""
        object_props[str(p_uri)] = {"id": str(p_uri), "local": local, "label": label,
                                     "domain": domain, "range": range_}

    # ---- 6. Add domain/range targets to classes if missing ----
    for pd in list(object_props.values()):
        for target in (pd["domain"], pd["range"]):
            if target and _domain_uri(target) and target not in classes:
                classes[target] = _make_class(rdflib.URIRef(target))

    # ---- 7. Datatype Properties ----
    datatype_props = {}
    for p in g.subjects(RDF.type, OWL.DatatypeProperty):
        if isinstance(p, rdflib.URIRef):
            local   = _local_name(str(p))
            label   = str(g.value(p, RDFS.label)   or local)
            domain  = str(g.value(p, RDFS.domain)  or "")
            range_  = str(g.value(p, RDFS.range)   or "")
            datatype_props[str(p)] = {"id": str(p), "local": local, "label": label,
                                       "domain": domain, "range": range_}

    # ---- 8. subClassOf edges (only between known classes) ----
    subclass_edges = []
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        if (isinstance(s, rdflib.URIRef) and isinstance(o, rdflib.URIRef)
                and str(s) in classes and str(o) in classes):
            subclass_edges.append((str(s), str(o)))

    # ---- 9. Property edges ----
    all_nodes  = {**classes, **individuals}
    prop_edges = []
    seen_edges = set()

    # Schema edges: handle multi-value rdfs:range (e.g. :range :A, :B)
    for pid, pd in object_props.items():
        p_uri  = rdflib.URIRef(pid)
        d_node = g.value(p_uri, RDFS.domain)
        d_str  = str(d_node) if d_node else pd["domain"]
        if not d_str or d_str not in all_nodes:
            continue
        for range_val in g.objects(p_uri, RDFS.range):
            if not isinstance(range_val, rdflib.URIRef):
                continue
            r_str = str(range_val)
            if r_str not in all_nodes:
                continue
            key = (d_str, r_str, pd["local"])
            if key not in seen_edges:
                seen_edges.add(key)
                prop_edges.append({"source": d_str, "target": r_str,
                                   "label": pd["label"], "local": pd["local"],
                                   "edge_kind": "schema"})

    # Instance-level edges (actual triples between known nodes)
    _skip = {
        str(RDF.type), str(RDFS.subClassOf), str(RDFS.label), str(RDFS.comment),
        str(RDFS.domain), str(RDFS.range), str(OWL.equivalentClass),
        str(OWL.disjointWith), str(OWL.sameAs), str(OWL.inverseOf),
        str(OWL.onProperty), str(OWL.someValuesFrom), str(OWL.allValuesFrom),
        str(OWL.complementOf), str(OWL.unionOf), str(OWL.intersectionOf),
    }
    for s, p, o in g.triples((None, None, None)):
        if not (isinstance(s, rdflib.URIRef) and isinstance(p, rdflib.URIRef)
                and isinstance(o, rdflib.URIRef)):
            continue
        if str(p) in _skip:
            continue
        ss, ps, os_ = str(s), str(p), str(o)
        if ss in all_nodes and os_ in all_nodes:
            local = _local_name(ps)
            label = str(g.value(p, RDFS.label) or local)
            key   = (ss, os_, local)
            if key not in seen_edges:
                seen_edges.add(key)
                prop_edges.append({"source": ss, "target": os_,
                                   "label": label, "local": local,
                                   "edge_kind": "instance"})

    return {
        "classes":        classes,
        "individuals":    individuals,
        "object_props":   object_props,
        "datatype_props": datatype_props,
        "subclass_edges": subclass_edges,
        "prop_edges":     prop_edges,
        "stats": {
            "n_classes":       len(classes),
            "n_individuals":   len(individuals),
            "n_object_props":  len(object_props),
            "n_datatype_props":len(datatype_props),
            "n_subclass":      len(subclass_edges),
            "n_prop_edges":    len(prop_edges),
        },
        "parser": "rdflib",
    }


def _parse_with_regex(ttl_text: str) -> Dict:
    """Lightweight regex fallback when rdflib is unavailable."""
    classes, individuals, object_props, datatype_props = {}, {}, {}, {}
    subclass_edges, prop_edges = [], []

    base_ns = "http://coha.org/military#"
    for m in re.finditer(r'@prefix\s+:\s+<([^>]+)>', ttl_text):
        base_ns = m.group(1)

    def _make_cls(local):
        uri = base_ns + local
        lm  = re.search(r':' + re.escape(local) + r'[^.]+rdfs:label\s+"([^"]+)"', ttl_text)
        cm  = re.search(r':' + re.escape(local) + r'[^.]+rdfs:comment\s+"([^"]+)"', ttl_text)
        return uri, {"id": uri, "local": local,
                     "label": lm.group(1) if lm else local,
                     "comment": cm.group(1) if cm else "",
                     "node_type": "class"}

    # owl:Class / rdfs:Class
    for m in re.finditer(r':([\w]+)\s+a\s+(?:owl|rdfs):Class', ttl_text):
        uri, entry = _make_cls(m.group(1))
        classes[uri] = entry

    # Infer classes from rdfs:subClassOf  (:A rdfs:subClassOf :B)
    for m in re.finditer(r':([\w]+)\s+[^.]*?rdfs:subClassOf\s+:([\w]+)', ttl_text):
        for local in (m.group(1), m.group(2)):
            uri = base_ns + local
            if uri not in classes:
                _, entry = _make_cls(local)
                classes[uri] = entry

    # owl:NamedIndividual
    for m in re.finditer(r':([\w]+)\s+a\s+owl:NamedIndividual', ttl_text):
        local = m.group(1)
        uri   = base_ns + local
        if uri in classes:
            continue
        lm = re.search(r':' + re.escape(local) + r'[^.]+rdfs:label\s+"([^"]+)"', ttl_text)
        cm = re.search(r':' + re.escape(local) + r'[^.]+rdfs:comment\s+"([^"]+)"', ttl_text)
        individuals[uri] = {"id": uri, "local": local,
                            "label": lm.group(1) if lm else local,
                            "comment": cm.group(1) if cm else "",
                            "types": [], "node_type": "individual"}

    # owl:ObjectProperty
    for m in re.finditer(r':([\w]+)\s+a\s+owl:ObjectProperty', ttl_text):
        local = m.group(1)
        uri   = base_ns + local
        lm    = re.search(r':' + re.escape(local) + r'[^.]+rdfs:label\s+"([^"]+)"', ttl_text)
        dm    = re.search(r':' + re.escape(local) + r'[^.]+rdfs:domain\s+:([\w]+)', ttl_text)
        rm    = re.search(r':' + re.escape(local) + r'[^.]+rdfs:range\s+:([\w]+)',  ttl_text)
        object_props[uri] = {"id": uri, "local": local,
                              "label":  lm.group(1) if lm else local,
                              "domain": base_ns + dm.group(1) if dm else "",
                              "range":  base_ns + rm.group(1) if rm else ""}

    # Infer object properties from rdfs:domain lines (without explicit typing)
    # Pattern: :propName rdfs:domain :ClassName (on one logical statement)
    for m in re.finditer(
        r':([\w]+)\s+rdfs:(?:label\s+"[^"]+"\s*[;,]\s*)?domain\s+:([\w]+)',
        ttl_text, re.MULTILINE
    ):
        local, domain_local = m.group(1), m.group(2)
        uri = base_ns + local
        if uri in object_props:
            continue
        lm = re.search(r':' + re.escape(local) + r'[^.]+rdfs:label\s+"([^"]+)"', ttl_text)
        rm = re.search(r':' + re.escape(local) + r'[^.]+rdfs:range\s+:([\w]+)',  ttl_text)
        object_props[uri] = {"id": uri, "local": local,
                              "label":  lm.group(1) if lm else local,
                              "domain": base_ns + domain_local,
                              "range":  base_ns + rm.group(1) if rm else ""}

    # Add domain/range targets to classes if missing
    for pd in list(object_props.values()):
        for target in (pd["domain"], pd["range"]):
            if target and target not in classes and target.startswith(base_ns):
                local = target[len(base_ns):]
                _, entry = _make_cls(local)
                classes[target] = entry

    # owl:DatatypeProperty
    for m in re.finditer(r':([\w]+)\s+a\s+owl:DatatypeProperty', ttl_text):
        local = m.group(1)
        uri   = base_ns + local
        lm    = re.search(r':' + re.escape(local) + r'[^.]+rdfs:label\s+"([^"]+)"', ttl_text)
        dm    = re.search(r':' + re.escape(local) + r'[^.]+rdfs:domain\s+:([\w]+)',    ttl_text)
        rm    = re.search(r':' + re.escape(local) + r'[^.]+rdfs:range\s+xsd:([\w]+)', ttl_text)
        datatype_props[uri] = {"id": uri, "local": local,
                                "label":  lm.group(1) if lm else local,
                                "domain": base_ns + dm.group(1) if dm else "",
                                "range":  "xsd:" + rm.group(1) if rm else ""}

    # subClassOf edges (only between known classes)
    for m in re.finditer(r':([\w]+)\s+[^.]*?rdfs:subClassOf\s+:([\w]+)', ttl_text):
        su, ou = base_ns + m.group(1), base_ns + m.group(2)
        if su in classes and ou in classes:
            subclass_edges.append((su, ou))

    all_nodes  = {**classes, **individuals}
    seen_edges = set()
    kpl        = {p["local"]: p for p in object_props.values()}

    # Schema-level
    for pid, pd in object_props.items():
        if pd["domain"] and pd["range"]:
            if pd["domain"] in all_nodes and pd["range"] in all_nodes:
                key = (pd["domain"], pd["range"], pd["local"])
                if key not in seen_edges:
                    seen_edges.add(key)
                    prop_edges.append({"source": pd["domain"], "target": pd["range"],
                                       "label": pd["label"], "local": pd["local"],
                                       "edge_kind": "schema"})

    # Instance-level: lines like   :Subject :predicate :Object .
    for m in re.finditer(r'^:([\w]+)\s+:([\w]+)\s+:([\w]+)\s*[;,.]', ttl_text, re.MULTILINE):
        sl, pl, ol = m.group(1), m.group(2), m.group(3)
        su, ou     = base_ns + sl, base_ns + ol
        if su in all_nodes and ou in all_nodes and pl in kpl:
            pd  = kpl[pl]
            key = (su, ou, pl)
            if key not in seen_edges:
                seen_edges.add(key)
                prop_edges.append({"source": su, "target": ou,
                                   "label": pd["label"], "local": pl,
                                   "edge_kind": "instance"})

    return {
        "classes":        classes,
        "individuals":    individuals,
        "object_props":   object_props,
        "datatype_props": datatype_props,
        "subclass_edges": subclass_edges,
        "prop_edges":     prop_edges,
        "stats": {
            "n_classes":        len(classes),
            "n_individuals":    len(individuals),
            "n_object_props":   len(object_props),
            "n_datatype_props": len(datatype_props),
            "n_subclass":       len(subclass_edges),
            "n_prop_edges":     len(prop_edges),
        },
        "parser": "regex",
    }


# ---------------------------------------------------------------------------
# Load TTL from file or JSON result
# ---------------------------------------------------------------------------

def load_ttl(path: str) -> Tuple[str, str]:
    if path.endswith(".json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            data = data[0]
        ttl   = data.get("ontology_ttl", data.get("ttl", ""))
        title = data.get("variant", os.path.basename(path))
        return ttl, title
    with open(path, encoding="utf-8") as f:
        ttl = f.read()
    return ttl, os.path.splitext(os.path.basename(path))[0]


# ---------------------------------------------------------------------------
# Graph data building
# ---------------------------------------------------------------------------

_PALETTE = [
    "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
    "#1abc9c", "#e67e22", "#c0392b", "#2980b9", "#8e44ad",
    "#16a085", "#d35400", "#f1c40f", "#7f8c8d", "#ff5722",
]

_IND_TYPE_COLORS = {
    "Terrain":           "#27ae60",
    "OpenTerrain":       "#27ae60",
    "ForestTerrain":     "#27ae60",
    "UrbanTerrain":      "#27ae60",
    "MountainTerrain":   "#27ae60",
    "DesertTerrain":     "#27ae60",
    "OperationType":     "#e67e22",
    "ManeuverForm":      "#e67e22",
    "FormOfManeuver":    "#e67e22",
    "Unit":              "#9b59b6",
    "ArmorUnit":         "#9b59b6",
    "InfantryUnit":      "#9b59b6",
    "AviationUnit":      "#9b59b6",
    "EngineerUnit":      "#9b59b6",
    "SpecialForcesUnit": "#9b59b6",
    "TacticalUnit":      "#9b59b6",
    "DefensiveOperation":"#e91e63",
    "OffensiveOperation":"#e91e63",
}


def _individual_color(types: List[str]) -> str:
    for t in types:
        if t in _IND_TYPE_COLORS:
            return _IND_TYPE_COLORS[t]
        for k, v in _IND_TYPE_COLORS.items():
            if k.lower() in t.lower():
                return v
    return "#f39c12"


def _build_graph_data(onto: Dict, compare_onto: Optional[Dict] = None) -> Dict:
    nodes, links = [], []
    node_ids = set()

    gold_locals = set()
    if compare_onto:
        gold_locals = {v["local"] for v in compare_onto["classes"].values()}

    # Class nodes
    for uri, cls in onto["classes"].items():
        local    = cls["local"]
        dt_props = [f"{p['label']} ({p['range'].split(':')[-1]})"
                    for p in onto["datatype_props"].values() if p["domain"] == uri]
        in_gold  = (local in gold_locals) if compare_onto else None
        nodes.append({"id": uri, "label": cls["label"], "local": local,
                      "comment": cls["comment"], "dt_props": dt_props,
                      "in_gold": in_gold, "type": "class"})
        node_ids.add(uri)

    # Individual nodes
    for uri, ind in onto.get("individuals", {}).items():
        types = ind.get("types", [])
        nodes.append({"id": uri, "label": ind["label"], "local": ind["local"],
                      "comment": ind["comment"], "dt_props": [],
                      "in_gold": None, "type": "individual",
                      "ind_types": types,
                      "ind_color": _individual_color(types)})
        node_ids.add(uri)

    # subClassOf edges
    for src, tgt in onto["subclass_edges"]:
        if src in node_ids and tgt in node_ids:
            links.append({"source": src, "target": tgt,
                          "label": "subClassOf", "kind": "subclass"})

    # Property edges (schema + instance)
    prop_colors: Dict[str, str] = {}
    for edge in onto["prop_edges"]:
        src, tgt   = edge["source"], edge["target"]
        label, loc = edge["label"],  edge["local"]
        ek         = edge.get("edge_kind", "instance")
        if src not in node_ids or tgt not in node_ids:
            continue
        if loc not in prop_colors:
            prop_colors[loc] = _PALETTE[len(prop_colors) % len(_PALETTE)]
        links.append({"source": src, "target": tgt, "label": label,
                      "kind": ek, "color": prop_colors[loc], "local": loc})

    prop_legend = [{"local": k, "color": v} for k, v in prop_colors.items()]
    return {"nodes": nodes, "links": links, "prop_legend": prop_legend}


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def visualize_to_html(
    ttl_path: str,
    compare_path: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    ttl_text, auto_title = load_ttl(ttl_path)
    display_title        = title or auto_title

    compare_onto = None
    if compare_path:
        cmp_ttl, _ = load_ttl(compare_path)
        compare_onto = parse_ontology(cmp_ttl)

    onto       = parse_ontology(ttl_text)
    graph_data = _build_graph_data(onto, compare_onto)
    stats      = onto["stats"]

    # ---- stats bar ----
    stats_html = f"""
        <div class="stat"><span class="stat-num">{stats['n_classes']}</span><br>Classes</div>
        <div class="stat"><span class="stat-num">{stats['n_individuals']}</span><br>Individuals</div>
        <div class="stat"><span class="stat-num">{stats['n_object_props']}</span><br>Obj Props</div>
        <div class="stat"><span class="stat-num">{stats['n_datatype_props']}</span><br>Data Props</div>
        <div class="stat"><span class="stat-num">{stats['n_subclass']}</span><br>SubClass</div>
        <div class="stat"><span class="stat-num">{stats['n_prop_edges']}</span><br>Prop Edges</div>
    """

    # ---- compare legend ----
    compare_legend = ""
    if compare_path:
        cname = os.path.splitext(os.path.basename(compare_path))[0]
        compare_legend = f"""
        <div class="legend-item"><span class="dot" style="background:#27ae60"></span>In {cname}</div>
        <div class="legend-item"><span class="dot" style="background:#e74c3c"></span>Not in {cname}</div>
        """

    graph_json  = json.dumps(graph_data)
    has_compare = "true" if compare_path else "false"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{display_title} — Ontology Viz</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body,html{{height:100%}}
  #coha-root{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    background:#1a1a2e;color:#eee;height:100%;display:flex;flex-direction:column}}
  #header{{background:#16213e;padding:8px 16px;display:flex;align-items:center;
    gap:16px;border-bottom:1px solid #0f3460;flex-shrink:0;flex-wrap:wrap}}
  #header h1{{font-size:15px;color:#e0e0ff;white-space:nowrap}}
  .stats{{display:flex;gap:10px;flex-wrap:wrap}}
  .stat{{text-align:center;font-size:10px;color:#aaa;line-height:1.3}}
  .stat-num{{font-size:16px;font-weight:bold;color:#7eb8f7}}
  .legend{{display:flex;gap:10px;flex-wrap:wrap;margin-left:auto;align-items:center}}
  .legend-item{{font-size:10px;display:flex;align-items:center;gap:4px;cursor:pointer;
    padding:2px 6px;border-radius:3px;transition:background .2s}}
  .legend-item:hover{{background:#0f3460}}
  .dot{{width:9px;height:9px;border-radius:50%;display:inline-block;flex-shrink:0}}
  .diamond{{width:9px;height:9px;display:inline-block;flex-shrink:0;
    transform:rotate(45deg);border-radius:1px}}
  #controls{{background:#16213e;padding:5px 16px;display:flex;gap:10px;
    align-items:center;border-bottom:1px solid #0f3460;flex-shrink:0;
    font-size:11px;flex-wrap:wrap}}
  #controls label{{color:#aaa;display:flex;align-items:center;gap:4px}}
  #controls input[type=range]{{width:70px}}
  #search{{background:#0f3460;border:1px solid #4a90d9;color:#eee;
    padding:3px 8px;border-radius:4px;font-size:11px;width:160px}}
  #prop-legend{{background:#16213e;padding:4px 16px;display:flex;gap:8px;
    flex-wrap:wrap;border-bottom:1px solid #0f3460;flex-shrink:0;
    font-size:10px;align-items:center;min-height:28px}}
  #prop-legend span{{font-size:10px;color:#888;margin-right:4px}}
  .prop-chip{{display:inline-flex;align-items:center;gap:4px;padding:1px 6px;
    border-radius:10px;cursor:pointer;transition:opacity .2s}}
  .prop-chip.inactive{{opacity:0.35}}
  .prop-chip .swatch{{width:8px;height:3px;border-radius:1px;flex-shrink:0}}
  #main{{display:flex;flex:1;overflow:hidden;min-height:0}}
  #graph{{flex:1;overflow:hidden;min-height:0}}
  svg{{width:100%;height:100%;display:block}}
  #sidebar{{width:270px;background:#16213e;border-left:1px solid #0f3460;
    overflow-y:auto;padding:12px;flex-shrink:0;display:none}}
  #sidebar h3{{color:#7eb8f7;font-size:13px;margin-bottom:8px}}
  .prop-list{{font-size:10px;color:#ccc;margin-top:5px}}
  .prop-list li{{margin:2px 0;list-style:disc;margin-left:14px}}
  .badge{{display:inline-block;padding:2px 6px;border-radius:10px;font-size:9px;margin:2px}}
  .node circle,.node polygon{{stroke-width:1.5px;cursor:pointer}}
  .node.individual circle{{stroke-dasharray:4,2;stroke-width:2px}}
  .node text{{font-size:8px;fill:#ddd;pointer-events:none;text-anchor:middle}}
  .link{{fill:none}}
  .link.subclass{{stroke:#666;stroke-dasharray:5,3;stroke-width:1.2px}}
  .link.schema{{stroke-opacity:0.6;stroke-width:1.2px}}
  .link.instance{{stroke-opacity:0.85;stroke-width:2px}}
  .link-label{{font-size:7px;fill:#999;pointer-events:none}}
  .node.highlighted circle,.node.highlighted polygon{{stroke:#fff!important;stroke-width:2.5px!important}}
  .node.dimmed{{opacity:0.15}}
  .link.dimmed{{opacity:0.04}}
  .link-label.dimmed{{opacity:0.04}}
</style>
</head>
<body>
<div id="coha-root">

<div id="header">
  <h1>{display_title}</h1>
  <div class="stats">{stats_html}</div>
  <div class="legend">
    {compare_legend}
    <div class="legend-item" onclick="toggleNodeType('class')">
      <span class="dot" style="background:#4a90d9"></span>Class
    </div>
    <div class="legend-item" onclick="toggleNodeType('individual','Terrain')">
      <span class="diamond" style="background:#27ae60"></span>Terrain
    </div>
    <div class="legend-item" onclick="toggleNodeType('individual','Operation')">
      <span class="diamond" style="background:#e67e22"></span>Operation
    </div>
    <div class="legend-item" onclick="toggleNodeType('individual','Unit')">
      <span class="diamond" style="background:#9b59b6"></span>Unit Indiv
    </div>
    <div class="legend-item" onclick="toggleEdgeKind('subclass')">
      <span style="display:inline-block;width:20px;border-top:2px dashed #666"></span>subClassOf
    </div>
    <div class="legend-item" onclick="toggleEdgeKind('instance')">
      <span style="display:inline-block;width:20px;border-top:2.5px solid #e74c3c"></span>Instance
    </div>
    <div class="legend-item" onclick="toggleEdgeKind('schema')">
      <span style="display:inline-block;width:20px;border-top:1.5px solid #3498db"></span>Schema
    </div>
  </div>
</div>

<div id="controls">
  <label>Search: <input id="search" type="text" placeholder="class or prop name…"></label>
  <label>Link dist: <input id="link-dist" type="range" min="50" max="500" value="160"></label>
  <label>Charge: <input id="charge" type="range" min="-1000" max="-30" value="-320"></label>
  <label><input id="show-labels" type="checkbox" checked> Edge labels</label>
  <label><input id="show-subclass" type="checkbox" checked> subClassOf</label>
  <label><input id="show-instance" type="checkbox" checked> Instance edges</label>
  <label><input id="show-schema" type="checkbox" checked> Schema edges</label>
  <label><input id="show-individuals" type="checkbox" checked> Individuals</label>
</div>

<div id="prop-legend">
  <span>Properties:</span>
</div>

<div id="main">
  <div id="graph"></div>
  <div id="sidebar">
    <h3 id="sb-title"></h3>
    <div id="sb-body"></div>
  </div>
</div>
</div>

<script>
const GRAPH = {graph_json};
const HAS_COMPARE = {has_compare};

// Build property legend bar
const propLegendEl = document.getElementById("prop-legend");
const activePropLocals = new Set(GRAPH.prop_legend.map(p => p.local));
GRAPH.prop_legend.forEach(p => {{
  const chip = document.createElement("div");
  chip.className = "prop-chip";
  chip.dataset.local = p.local;
  chip.innerHTML = `<span class="swatch" style="background:${{p.color}}"></span>${{p.local}}`;
  chip.style.color = p.color;
  chip.addEventListener("click", () => toggleProp(p.local, chip));
  propLegendEl.appendChild(chip);
}});

const svgEl = d3.select("#graph").append("svg")
  .call(d3.zoom().scaleExtent([0.03, 8]).on("zoom", e => g.attr("transform", e.transform)));

const g = svgEl.append("g");

// Arrow markers for each color
const defs = svgEl.append("defs");
function addMarker(id, color) {{
  defs.append("marker").attr("id", id)
    .attr("viewBox","0 -4 8 8").attr("refX", 20).attr("refY", 0)
    .attr("markerWidth", 5).attr("markerHeight", 5).attr("orient","auto")
    .append("path").attr("d","M0,-4L8,0L0,4").attr("fill", color);
}}
addMarker("arrow-sub","#555");
const allColors = [...new Set(GRAPH.links.filter(l=>l.kind!=="subclass").map(l=>l.color))];
allColors.forEach((c,i) => addMarker("arrow-c"+i, c));
const c2m = {{}};
allColors.forEach((c,i) => c2m[c] = "arrow-c"+i);

// Simulation
const sim = d3.forceSimulation(GRAPH.nodes)
  .force("link",      d3.forceLink(GRAPH.links).id(d=>d.id).distance(160))
  .force("charge",    d3.forceManyBody().strength(-320))
  .force("center",    d3.forceCenter(600, 400))
  .force("collision", d3.forceCollide(20));

// Links
const link = g.append("g").selectAll("line")
  .data(GRAPH.links).join("line")
  .attr("class", d => "link " + d.kind)
  .attr("stroke", d => d.color || "#555")
  .attr("marker-end", d => d.kind==="subclass"
    ? "url(#arrow-sub)"
    : (c2m[d.color] ? "url(#"+c2m[d.color]+")" : ""));

// Link labels
const linkLabel = g.append("g").selectAll("text")
  .data(GRAPH.links).join("text")
  .attr("class","link-label")
  .text(d => d.label);

// Nodes
const node = g.append("g").selectAll("g")
  .data(GRAPH.nodes).join("g")
  .attr("class", d => "node" + (d.type==="individual" ? " individual" : ""))
  .call(d3.drag()
    .on("start",(e,d)=>{{ if(!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }})
    .on("drag", (e,d)=>{{ d.fx=e.x; d.fy=e.y; }})
    .on("end",  (e,d)=>{{ if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }}))
  .on("click", onNodeClick);

function nodeColor(d) {{
  if (d.type === "individual") return d.ind_color || "#f39c12";
  if (HAS_COMPARE && d.in_gold !== null) return d.in_gold ? "#27ae60" : "#e74c3c";
  return "#4a90d9";
}}
function nodeStroke(d) {{
  if (d.type === "individual") return d3.color(d.ind_color || "#f39c12").darker(0.6);
  if (HAS_COMPARE && d.in_gold !== null) return d.in_gold ? "#1e8449" : "#c0392b";
  return "#2471a3";
}}

// Classes = circles, Individuals = diamonds
node.each(function(d) {{
  const n = d3.select(this);
  if (d.type === "individual") {{
    n.append("polygon")
      .attr("points","0,-13 13,0 0,13 -13,0")
      .attr("fill",   nodeColor(d))
      .attr("stroke", nodeStroke(d))
      .attr("stroke-width", 2);
  }} else {{
    n.append("circle")
      .attr("r", 13)
      .attr("fill",   nodeColor(d))
      .attr("stroke", nodeStroke(d));
  }}
}});

node.append("text").attr("dy","0.35em")
  .text(d => d.label.length > 13 ? d.label.slice(0,12)+"…" : d.label);

node.append("title")
  .text(d => d.label + (d.type==="individual" ? " [Individual]" : " [Class]")
    + (d.comment ? "\\n" + d.comment : ""));

sim.on("tick", () => {{
  link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y)
      .attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
  linkLabel.attr("x",d=>(d.source.x+d.target.x)/2)
           .attr("y",d=>(d.source.y+d.target.y)/2);
  node.attr("transform",d=>`translate(${{d.x}},${{d.y}})`);
}});

// ---- Controls ----
document.getElementById("link-dist").addEventListener("input", function() {{
  sim.force("link").distance(+this.value); sim.alpha(0.5).restart();
}});
document.getElementById("charge").addEventListener("input", function() {{
  sim.force("charge").strength(+this.value); sim.alpha(0.5).restart();
}});
document.getElementById("show-labels").addEventListener("change", function() {{
  linkLabel.style("display", this.checked ? null : "none");
}});

function applyEdgeKindVisibility() {{
  const showSub  = document.getElementById("show-subclass").checked;
  const showInst = document.getElementById("show-instance").checked;
  const showSch  = document.getElementById("show-schema").checked;
  link.style("display", d => {{
    if (d.kind==="subclass" && !showSub)  return "none";
    if (d.kind==="instance" && !showInst) return "none";
    if (d.kind==="schema"   && !showSch)  return "none";
    // check prop filter
    if (d.local && !activePropLocals.has(d.local)) return "none";
    return null;
  }});
  linkLabel.style("display", d => {{
    const lv = document.getElementById("show-labels").checked;
    if (!lv) return "none";
    if (d.kind==="subclass" && !showSub)  return "none";
    if (d.kind==="instance" && !showInst) return "none";
    if (d.kind==="schema"   && !showSch)  return "none";
    if (d.local && !activePropLocals.has(d.local)) return "none";
    return null;
  }});
}}
["show-subclass","show-instance","show-schema"].forEach(id =>
  document.getElementById(id).addEventListener("change", applyEdgeKindVisibility));

document.getElementById("show-individuals").addEventListener("change", function() {{
  node.filter(d=>d.type==="individual").style("display", this.checked ? null : "none");
  link.filter(d => {{
    const sn = GRAPH.nodes.find(n=>n.id===(d.source.id||d.source));
    const tn = GRAPH.nodes.find(n=>n.id===(d.target.id||d.target));
    return (sn?.type==="individual" || tn?.type==="individual");
  }}).style("display", this.checked ? null : "none");
}});

// Toggle helpers
const hiddenKinds    = new Set();
const hiddenIndTypes = new Set();

function toggleEdgeKind(kind) {{
  const id = kind==="instance" ? "show-instance" : kind==="schema" ? "show-schema" : "show-subclass";
  const cb = document.getElementById(id);
  cb.checked = !cb.checked;
  applyEdgeKindVisibility();
}}

function toggleNodeType(type, subtype) {{
  if (type==="class") {{
    const cb = document.getElementById("show-individuals");
    // toggle by hiding class nodes — use a flag
    if (!hiddenKinds.has("class")) {{
      hiddenKinds.add("class");
      node.filter(d=>d.type==="class").style("display","none");
    }} else {{
      hiddenKinds.delete("class");
      node.filter(d=>d.type==="class").style("display",null);
    }}
  }} else if (type==="individual" && subtype) {{
    const key = "ind_"+subtype.toLowerCase();
    if (!hiddenKinds.has(key)) {{
      hiddenKinds.add(key);
      node.filter(d => d.type==="individual" &&
        d.ind_types.some(t=>t.toLowerCase().includes(subtype.toLowerCase())))
        .style("display","none");
    }} else {{
      hiddenKinds.delete(key);
      node.filter(d => d.type==="individual" &&
        d.ind_types.some(t=>t.toLowerCase().includes(subtype.toLowerCase())))
        .style("display",null);
    }}
  }}
}}

function toggleProp(local, chipEl) {{
  if (activePropLocals.has(local)) {{
    activePropLocals.delete(local);
    chipEl.classList.add("inactive");
  }} else {{
    activePropLocals.add(local);
    chipEl.classList.remove("inactive");
  }}
  applyEdgeKindVisibility();
}}

// Search
document.getElementById("search").addEventListener("input", function() {{
  const q = this.value.trim().toLowerCase();
  if (!q) {{ unhighlight(); return; }}
  const matched = new Set(GRAPH.nodes
    .filter(d => d.label.toLowerCase().includes(q) || d.local.toLowerCase().includes(q))
    .map(d => d.id));
  node.classed("highlighted", d => matched.has(d.id))
      .classed("dimmed", d => !matched.has(d.id));
  link.classed("dimmed", d => !matched.has(d.source.id||d.source) && !matched.has(d.target.id||d.target));
  linkLabel.classed("dimmed", d => !matched.has(d.source.id||d.source) && !matched.has(d.target.id||d.target));
}});

function unhighlight() {{
  node.classed("highlighted",false).classed("dimmed",false);
  link.classed("dimmed",false);
  linkLabel.classed("dimmed",false);
}}

// Sidebar
function onNodeClick(event, d) {{
  event.stopPropagation();
  const sb = document.getElementById("sidebar");
  sb.style.display = "block";
  document.getElementById("sb-title").textContent = d.label;

  const cl = GRAPH.links.filter(l =>
    (l.source.id||l.source)===d.id || (l.target.id||l.target)===d.id);

  const nn = id => GRAPH.nodes.find(n=>n.id===id)?.label || "?";

  const parents  = cl.filter(l=>l.kind==="subclass"&&(l.source.id||l.source)===d.id)
    .map(l=>nn(l.target.id||l.target));
  const children = cl.filter(l=>l.kind==="subclass"&&(l.target.id||l.target)===d.id)
    .map(l=>nn(l.source.id||l.source));
  const outInst  = cl.filter(l=>l.kind==="instance"&&(l.source.id||l.source)===d.id)
    .map(l=>`<span style="color:${{l.color}}">${{l.label}}</span> → ${{nn(l.target.id||l.target)}}`);
  const inInst   = cl.filter(l=>l.kind==="instance"&&(l.target.id||l.target)===d.id)
    .map(l=>`${{nn(l.source.id||l.source)}} → <span style="color:${{l.color}}">${{l.label}}</span>`);
  const outSch   = cl.filter(l=>l.kind==="schema"&&(l.source.id||l.source)===d.id)
    .map(l=>`<span style="color:${{l.color}}">${{l.label}}</span> → ${{nn(l.target.id||l.target)}}`);
  const inSch    = cl.filter(l=>l.kind==="schema"&&(l.target.id||l.target)===d.id)
    .map(l=>`${{nn(l.source.id||l.source)}} → <span style="color:${{l.color}}">${{l.label}}</span>`);

  const typeBadge = d.type === "individual"
    ? `<span class="badge" style="background:#333;color:#f39c12">◆ Individual</span>`
      + (d.ind_types||[]).map(t=>`<span class="badge" style="background:#1a2a1a;color:#27ae60">${{t}}</span>`).join("")
    : `<span class="badge" style="background:#0f3460;color:#7eb8f7">● Class</span>`;

  let html = `<div style="font-size:10px;color:#7eb8f7;margin-bottom:5px">:<b>${{d.local}}</b></div>`;
  html += typeBadge;
  if (HAS_COMPARE && d.type==="class") {{
    html += d.in_gold
      ? `<span class="badge" style="background:#1e8449">✓ In Gold</span>`
      : `<span class="badge" style="background:#922b21">✗ Not in Gold</span>`;
  }}
  if (d.comment)
    html += `<p style="font-size:9px;color:#aaa;margin:7px 0">${{d.comment}}</p>`;
  if (parents.length)
    html += `<div class="prop-list" style="margin-top:7px"><b>subClassOf:</b><ul>${{parents.map(p=>`<li>${{p}}</li>`).join("")}}</ul></div>`;
  if (children.length)
    html += `<div class="prop-list"><b>Subclasses:</b><ul>${{children.map(p=>`<li>${{p}}</li>`).join("")}}</ul></div>`;
  if (outInst.length)
    html += `<div class="prop-list"><b>Instance props out:</b><ul>${{outInst.map(p=>`<li>${{p}}</li>`).join("")}}</ul></div>`;
  if (inInst.length)
    html += `<div class="prop-list"><b>Instance props in:</b><ul>${{inInst.map(p=>`<li>${{p}}</li>`).join("")}}</ul></div>`;
  if (outSch.length)
    html += `<div class="prop-list"><b>Schema props out:</b><ul>${{outSch.map(p=>`<li>${{p}}</li>`).join("")}}</ul></div>`;
  if (inSch.length)
    html += `<div class="prop-list"><b>Schema props in:</b><ul>${{inSch.map(p=>`<li>${{p}}</li>`).join("")}}</ul></div>`;
  if (d.dt_props?.length)
    html += `<div class="prop-list"><b>Data props:</b><ul>${{d.dt_props.map(p=>`<li>${{p}}</li>`).join("")}}</ul></div>`;

  document.getElementById("sb-body").innerHTML = html;

  const conn = new Set([d.id,
    ...cl.map(l=>l.source.id||l.source),
    ...cl.map(l=>l.target.id||l.target)]);
  node.classed("highlighted", n=>conn.has(n.id)).classed("dimmed", n=>!conn.has(n.id));
  link.classed("dimmed", l=>!conn.has(l.source.id||l.source)||!conn.has(l.target.id||l.target));
  linkLabel.classed("dimmed", l=>!conn.has(l.source.id||l.source)||!conn.has(l.target.id||l.target));
}}

svgEl.on("click", () => {{
  document.getElementById("sidebar").style.display = "none";
  unhighlight();
}});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Colab helper
# ---------------------------------------------------------------------------

def _get_d3_js() -> str:
    cache_path = os.path.join(os.path.dirname(__file__), "_d3v7.min.js")
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return f.read()
    import urllib.request
    try:
        with urllib.request.urlopen("https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js", timeout=30) as r:
            js = r.read().decode("utf-8")
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(js)
        return js
    except Exception:
        return ""


def show_in_colab(html: str, height: int = 800):
    import base64
    from IPython.display import display, HTML
    d3_src = _get_d3_js()
    if d3_src:
        html = html.replace(
            '<script src="https://d3js.org/d3.v7.min.js"></script>',
            f"<script>{d3_src}</script>",
        )
    b64    = base64.b64encode(html.encode("utf-8")).decode("ascii")
    iframe = (f'<iframe src="data:text/html;base64,{b64}" '
              f'width="100%" height="{height}px" frameborder="0" '
              f'style="border:none;display:block"></iframe>')
    display(HTML(iframe))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Interactive ontology visualizer")
    parser.add_argument("input", help=".ttl file or JSON result file")
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument("--compare", "-c", default=None, help="Gold standard TTL")
    parser.add_argument("--title",   "-t", default=None)
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: File not found: {args.input}"); sys.exit(1)

    print(f"Parsing: {args.input}")
    html = visualize_to_html(args.input, compare_path=args.compare, title=args.title)

    out_path = args.output or (os.path.splitext(args.input)[0] + "_viz.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved:  {out_path}")
    print(f"Open:   file://{os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
