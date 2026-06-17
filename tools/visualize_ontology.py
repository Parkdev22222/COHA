"""
Ontology visualizer: reads a TTL file and generates an interactive HTML graph.

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
import textwrap
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ---------------------------------------------------------------------------
# TTL parsing (rdflib-based, with lightweight fallback)
# ---------------------------------------------------------------------------

def _local_name(uri: str) -> str:
    """Extract local name from a URI."""
    for sep in ("#", "/"):
        if sep in uri:
            return uri.rsplit(sep, 1)[-1]
    return uri


def parse_ontology(ttl_text: str) -> Dict:
    """
    Parse Turtle ontology text.
    Returns dict with keys: classes, object_props, datatype_props, subclass_edges, prop_edges, stats
    """
    try:
        return _parse_with_rdflib(ttl_text)
    except Exception:
        return _parse_with_regex(ttl_text)


def _parse_with_rdflib(ttl_text: str) -> Dict:
    import rdflib
    OWL = rdflib.OWL
    RDFS = rdflib.RDFS
    RDF = rdflib.RDF
    XSD = rdflib.XSD

    g = rdflib.Graph()
    g.parse(data=ttl_text, format="turtle")

    classes = {}
    for s in g.subjects(RDF.type, OWL.Class):
        if isinstance(s, rdflib.URIRef):
            local = _local_name(str(s))
            label = str(g.value(s, RDFS.label) or local)
            comment = str(g.value(s, RDFS.comment) or "")
            classes[str(s)] = {"id": str(s), "local": local, "label": label, "comment": comment}

    object_props = {}
    for p in g.subjects(RDF.type, OWL.ObjectProperty):
        if isinstance(p, rdflib.URIRef):
            local = _local_name(str(p))
            label = str(g.value(p, RDFS.label) or local)
            domain = str(g.value(p, RDFS.domain) or "")
            range_ = str(g.value(p, RDFS.range) or "")
            object_props[str(p)] = {"id": str(p), "local": local, "label": label,
                                     "domain": domain, "range": range_}

    datatype_props = {}
    for p in g.subjects(RDF.type, OWL.DatatypeProperty):
        if isinstance(p, rdflib.URIRef):
            local = _local_name(str(p))
            label = str(g.value(p, RDFS.label) or local)
            domain = str(g.value(p, RDFS.domain) or "")
            range_ = str(g.value(p, RDFS.range) or "")
            datatype_props[str(p)] = {"id": str(p), "local": local, "label": label,
                                       "domain": domain, "range": range_}

    subclass_edges = []
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        if isinstance(s, rdflib.URIRef) and isinstance(o, rdflib.URIRef):
            subclass_edges.append((str(s), str(o)))

    prop_edges = []
    for pid, pdata in object_props.items():
        if pdata["domain"] and pdata["range"]:
            if pdata["domain"] in classes and pdata["range"] in classes:
                prop_edges.append((pdata["domain"], pdata["range"], pdata["label"], pdata["local"]))

    return {
        "classes": classes,
        "object_props": object_props,
        "datatype_props": datatype_props,
        "subclass_edges": subclass_edges,
        "prop_edges": prop_edges,
        "stats": {
            "n_classes": len(classes),
            "n_object_props": len(object_props),
            "n_datatype_props": len(datatype_props),
            "n_subclass": len(subclass_edges),
            "n_prop_edges": len(prop_edges),
        },
        "parser": "rdflib",
    }


def _parse_with_regex(ttl_text: str) -> Dict:
    """Lightweight regex fallback when rdflib is unavailable."""
    classes = {}
    object_props = {}
    datatype_props = {}
    subclass_edges = []
    prop_edges = []

    # Extract prefix
    base_ns = "http://coha.org/military#"
    for m in re.finditer(r'@prefix\s+:\s+<([^>]+)>', ttl_text):
        base_ns = m.group(1)

    def expand(local: str) -> str:
        if local.startswith(":"):
            return base_ns + local[1:]
        return local

    # Find owl:Class declarations
    for m in re.finditer(r':([\w]+)\s+a\s+owl:Class', ttl_text):
        local = m.group(1)
        uri = base_ns + local
        # Try to find rdfs:label
        label_m = re.search(
            r':' + re.escape(local) + r'[^.]+rdfs:label\s+"([^"]+)"', ttl_text)
        label = label_m.group(1) if label_m else local
        classes[uri] = {"id": uri, "local": local, "label": label, "comment": ""}

    # Find owl:ObjectProperty
    for m in re.finditer(r':([\w]+)\s+a\s+owl:ObjectProperty', ttl_text):
        local = m.group(1)
        uri = base_ns + local
        label_m = re.search(
            r':' + re.escape(local) + r'[^.]+rdfs:label\s+"([^"]+)"', ttl_text)
        label = label_m.group(1) if label_m else local
        domain_m = re.search(
            r':' + re.escape(local) + r'[^.]+rdfs:domain\s+:([\w]+)', ttl_text)
        range_m = re.search(
            r':' + re.escape(local) + r'[^.]+rdfs:range\s+:([\w]+)', ttl_text)
        domain = base_ns + domain_m.group(1) if domain_m else ""
        range_ = base_ns + range_m.group(1) if range_m else ""
        object_props[uri] = {"id": uri, "local": local, "label": label,
                              "domain": domain, "range": range_}

    # Find owl:DatatypeProperty
    for m in re.finditer(r':([\w]+)\s+a\s+owl:DatatypeProperty', ttl_text):
        local = m.group(1)
        uri = base_ns + local
        label_m = re.search(
            r':' + re.escape(local) + r'[^.]+rdfs:label\s+"([^"]+)"', ttl_text)
        label = label_m.group(1) if label_m else local
        domain_m = re.search(
            r':' + re.escape(local) + r'[^.]+rdfs:domain\s+:([\w]+)', ttl_text)
        range_m = re.search(
            r':' + re.escape(local) + r'[^.]+rdfs:range\s+xsd:([\w]+)', ttl_text)
        domain = base_ns + domain_m.group(1) if domain_m else ""
        range_ = "xsd:" + range_m.group(1) if range_m else ""
        datatype_props[uri] = {"id": uri, "local": local, "label": label,
                                "domain": domain, "range": range_}

    # subClassOf
    for m in re.finditer(r':([\w]+)\s+[^.]*rdfs:subClassOf\s+:([\w]+)', ttl_text):
        subclass_edges.append((base_ns + m.group(1), base_ns + m.group(2)))

    # prop edges
    for pid, pdata in object_props.items():
        if pdata["domain"] and pdata["range"]:
            if pdata["domain"] in classes and pdata["range"] in classes:
                prop_edges.append((pdata["domain"], pdata["range"], pdata["label"], pdata["local"]))

    return {
        "classes": classes,
        "object_props": object_props,
        "datatype_props": datatype_props,
        "subclass_edges": subclass_edges,
        "prop_edges": prop_edges,
        "stats": {
            "n_classes": len(classes),
            "n_object_props": len(object_props),
            "n_datatype_props": len(datatype_props),
            "n_subclass": len(subclass_edges),
            "n_prop_edges": len(prop_edges),
        },
        "parser": "regex",
    }


# ---------------------------------------------------------------------------
# Load TTL from TTL file or JSON result file
# ---------------------------------------------------------------------------

def load_ttl(path: str) -> Tuple[str, str]:
    """Load TTL text from a .ttl file or a JSON result file. Returns (ttl_text, title)."""
    if path.endswith(".json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # Support both single result and list of results
        if isinstance(data, list):
            data = data[0]
        ttl = data.get("ontology_ttl", data.get("ttl", ""))
        title = data.get("variant", os.path.basename(path))
        return ttl, title
    else:
        with open(path, encoding="utf-8") as f:
            ttl = f.read()
        title = os.path.splitext(os.path.basename(path))[0]
        return ttl, title


# ---------------------------------------------------------------------------
# HTML generation (self-contained, D3.js v7 from CDN)
# ---------------------------------------------------------------------------

_PALETTE = [
    "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
    "#1abc9c", "#e67e22", "#34495e", "#e91e63", "#00bcd4",
]

def _build_graph_data(onto: Dict, compare_onto: Optional[Dict] = None) -> Dict:
    """Convert parsed ontology to D3 force graph nodes/links."""
    nodes = []
    links = []
    node_ids = set()

    gold_locals = set()
    if compare_onto:
        gold_locals = {v["local"] for v in compare_onto["classes"].values()}

    for uri, cls in onto["classes"].items():
        local = cls["local"]
        # Datatype props belonging to this class
        dt_props = [
            f"{p['label']} ({p['range'].split(':')[-1]})"
            for p in onto["datatype_props"].values()
            if p["domain"] == uri
        ]
        in_gold = local in gold_locals if compare_onto else None
        nodes.append({
            "id": uri,
            "label": cls["label"],
            "local": local,
            "comment": cls["comment"],
            "dt_props": dt_props,
            "in_gold": in_gold,
            "type": "class",
        })
        node_ids.add(uri)

    # subClassOf edges
    for src, tgt in onto["subclass_edges"]:
        if src in node_ids and tgt in node_ids:
            links.append({"source": src, "target": tgt, "label": "subClassOf", "kind": "subclass"})

    # Object property edges
    prop_colors = {}
    for i, (src, tgt, label, local) in enumerate(onto["prop_edges"]):
        if src not in node_ids or tgt not in node_ids:
            continue
        if local not in prop_colors:
            prop_colors[local] = _PALETTE[len(prop_colors) % len(_PALETTE)]
        links.append({
            "source": src, "target": tgt,
            "label": label, "kind": "objprop",
            "color": prop_colors[local],
        })

    return {"nodes": nodes, "links": links}


def visualize_to_html(
    ttl_path: str,
    compare_path: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """
    Generate a self-contained interactive HTML visualization.

    Args:
        ttl_path: Path to .ttl file or JSON result file.
        compare_path: Optional path to gold standard TTL for coverage coloring.
        title: Display title override.

    Returns:
        HTML string (self-contained, can be saved to file or shown in Colab).
    """
    ttl_text, auto_title = load_ttl(ttl_path)
    display_title = title or auto_title

    compare_onto = None
    if compare_path:
        cmp_ttl, _ = load_ttl(compare_path)
        compare_onto = parse_ontology(cmp_ttl)

    onto = parse_ontology(ttl_text)
    graph_data = _build_graph_data(onto, compare_onto)
    stats = onto["stats"]

    compare_legend = ""
    if compare_path:
        compare_name = os.path.splitext(os.path.basename(compare_path))[0]
        compare_legend = f"""
        <div class="legend-item"><span class="dot" style="background:#27ae60"></span>In {compare_name}</div>
        <div class="legend-item"><span class="dot" style="background:#e74c3c"></span>Not in {compare_name}</div>
        """

    stats_html = f"""
        <div class="stat"><span class="stat-num">{stats['n_classes']}</span><br>Classes</div>
        <div class="stat"><span class="stat-num">{stats['n_object_props']}</span><br>Obj Props</div>
        <div class="stat"><span class="stat-num">{stats['n_datatype_props']}</span><br>Data Props</div>
        <div class="stat"><span class="stat-num">{stats['n_subclass']}</span><br>SubClass</div>
        <div class="stat"><span class="stat-num">{stats['n_prop_edges']}</span><br>Prop Edges</div>
    """

    graph_json = json.dumps(graph_data)
    has_compare = "true" if compare_path else "false"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{display_title} — Ontology Viz</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background: #1a1a2e; color: #eee; height: 100vh; display: flex; flex-direction: column; }}
  #header {{ background: #16213e; padding: 10px 20px; display: flex; align-items: center;
             gap: 20px; border-bottom: 1px solid #0f3460; flex-shrink: 0; }}
  #header h1 {{ font-size: 16px; color: #e0e0ff; white-space: nowrap; }}
  .stats {{ display: flex; gap: 12px; flex-wrap: wrap; }}
  .stat {{ text-align: center; font-size: 11px; color: #aaa; line-height: 1.3; }}
  .stat-num {{ font-size: 18px; font-weight: bold; color: #7eb8f7; }}
  .legend {{ display: flex; gap: 12px; flex-wrap: wrap; margin-left: auto; }}
  .legend-item {{ font-size: 11px; display: flex; align-items: center; gap: 4px; }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
  .line-subclass {{ width: 20px; height: 2px; background: #888; display: inline-block;
                    border-top: 2px dashed #888; }}
  .line-prop {{ width: 20px; height: 2px; background: #e74c3c; display: inline-block; }}
  #controls {{ background: #16213e; padding: 6px 20px; display: flex; gap: 12px;
               align-items: center; border-bottom: 1px solid #0f3460; flex-shrink: 0; font-size: 12px; }}
  #controls label {{ color: #aaa; }}
  #controls input[type=range] {{ width: 80px; }}
  #search {{ background: #0f3460; border: 1px solid #4a90d9; color: #eee;
             padding: 3px 8px; border-radius: 4px; font-size: 12px; width: 180px; }}
  #main {{ display: flex; flex: 1; overflow: hidden; }}
  #graph {{ flex: 1; overflow: hidden; }}
  svg {{ width: 100%; height: 100%; }}
  #sidebar {{ width: 260px; background: #16213e; border-left: 1px solid #0f3460;
              overflow-y: auto; padding: 12px; flex-shrink: 0; display: none; }}
  #sidebar h3 {{ color: #7eb8f7; font-size: 14px; margin-bottom: 8px; }}
  #sidebar .prop-list {{ font-size: 11px; color: #ccc; margin-top: 6px; }}
  #sidebar .prop-list li {{ margin: 3px 0; list-style: disc; margin-left: 14px; }}
  #sidebar .badge {{ display: inline-block; padding: 2px 6px; border-radius: 10px;
                     font-size: 10px; margin: 2px; }}
  .node circle {{ stroke-width: 1.5px; cursor: pointer; }}
  .node text {{ font-size: 9px; fill: #ddd; pointer-events: none; text-anchor: middle; }}
  .link {{ fill: none; stroke-width: 1.5px; }}
  .link.subclass {{ stroke: #666; stroke-dasharray: 4,3; }}
  .link.objprop {{ stroke-opacity: 0.8; }}
  .link-label {{ font-size: 8px; fill: #aaa; pointer-events: none; }}
  .node.highlighted circle {{ stroke: #fff; stroke-width: 2.5px; }}
  .node.dimmed {{ opacity: 0.2; }}
  .link.dimmed {{ opacity: 0.05; }}
  .link-label.dimmed {{ opacity: 0.05; }}
  marker path {{ }}
</style>
</head>
<body>
<div id="header">
  <h1>{display_title}</h1>
  <div class="stats">{stats_html}</div>
  <div class="legend">
    {compare_legend}
    <div class="legend-item"><span class="line-subclass"></span>subClassOf</div>
    <div class="legend-item"><span class="line-prop"></span>Object Property</div>
  </div>
</div>
<div id="controls">
  <label>Search: <input id="search" type="text" placeholder="class or property name…"></label>
  <label>Link dist: <input id="link-dist" type="range" min="60" max="400" value="150"></label>
  <label>Charge: <input id="charge" type="range" min="-800" max="-50" value="-300"></label>
  <label><input id="show-labels" type="checkbox" checked> Edge labels</label>
  <label><input id="show-subclass" type="checkbox" checked> subClassOf</label>
</div>
<div id="main">
  <div id="graph"></div>
  <div id="sidebar">
    <h3 id="sb-title"></h3>
    <div id="sb-body"></div>
  </div>
</div>

<script>
const GRAPH = {graph_json};
const HAS_COMPARE = {has_compare};

const width = document.getElementById("graph").clientWidth || 900;
const height = document.getElementById("graph").clientHeight || 700;

const svg = d3.select("#graph").append("svg")
  .call(d3.zoom().scaleExtent([0.05, 5]).on("zoom", e => g.attr("transform", e.transform)));

const g = svg.append("g");

// Arrowhead markers
const defs = svg.append("defs");
function addMarker(id, color) {{
  defs.append("marker")
    .attr("id", id)
    .attr("viewBox", "0 -4 8 8")
    .attr("refX", 18).attr("refY", 0)
    .attr("markerWidth", 6).attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-4L8,0L0,4")
    .attr("fill", color);
}}
addMarker("arrow-sub", "#666");
const propColors = [...new Set(GRAPH.links.filter(l=>l.kind==="objprop").map(l=>l.color))];
propColors.forEach((c,i) => addMarker("arrow-prop-"+i, c));
const colorToMarker = {{}};
propColors.forEach((c,i) => colorToMarker[c] = "arrow-prop-"+i);

// Force simulation
const sim = d3.forceSimulation(GRAPH.nodes)
  .force("link", d3.forceLink(GRAPH.links).id(d=>d.id).distance(150))
  .force("charge", d3.forceManyBody().strength(-300))
  .force("center", d3.forceCenter(width/2, height/2))
  .force("collision", d3.forceCollide(22));

// Links
const link = g.append("g").selectAll("line")
  .data(GRAPH.links).join("line")
  .attr("class", d => "link " + d.kind)
  .attr("stroke", d => d.color || "#666")
  .attr("marker-end", d => d.kind==="subclass" ? "url(#arrow-sub)"
    : "url(#" + colorToMarker[d.color] + ")");

// Link labels
const linkLabel = g.append("g").selectAll("text")
  .data(GRAPH.links).join("text")
  .attr("class", "link-label")
  .text(d => d.label);

// Nodes
const node = g.append("g").selectAll("g")
  .data(GRAPH.nodes).join("g")
  .attr("class", "node")
  .call(d3.drag()
    .on("start", (e,d) => {{ if (!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }})
    .on("drag", (e,d) => {{ d.fx=e.x; d.fy=e.y; }})
    .on("end", (e,d) => {{ if (!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }}))
  .on("click", onNodeClick);

function nodeColor(d) {{
  if (HAS_COMPARE && d.in_gold !== null) return d.in_gold ? "#27ae60" : "#e74c3c";
  return "#4a90d9";
}}
function nodeStroke(d) {{
  if (HAS_COMPARE && d.in_gold !== null) return d.in_gold ? "#1e8449" : "#c0392b";
  return "#2471a3";
}}

node.append("circle")
  .attr("r", 14)
  .attr("fill", nodeColor)
  .attr("stroke", nodeStroke);

node.append("text")
  .attr("dy", "0.35em")
  .text(d => d.label.length > 14 ? d.label.slice(0,13)+"…" : d.label);

node.append("title").text(d => d.label + (d.comment ? "\\n" + d.comment : ""));

sim.on("tick", () => {{
  link
    .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  linkLabel
    .attr("x", d => (d.source.x + d.target.x) / 2)
    .attr("y", d => (d.source.y + d.target.y) / 2);
  node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
}});

// Controls
document.getElementById("link-dist").addEventListener("input", function() {{
  sim.force("link").distance(+this.value);
  sim.alpha(0.5).restart();
}});
document.getElementById("charge").addEventListener("input", function() {{
  sim.force("charge").strength(+this.value);
  sim.alpha(0.5).restart();
}});
document.getElementById("show-labels").addEventListener("change", function() {{
  linkLabel.style("display", this.checked ? null : "none");
}});
document.getElementById("show-subclass").addEventListener("change", function() {{
  link.filter(d=>d.kind==="subclass").style("display", this.checked ? null : "none");
  linkLabel.filter(d=>d.kind==="subclass").style("display", this.checked ? null : "none");
}});

// Search
document.getElementById("search").addEventListener("input", function() {{
  const q = this.value.trim().toLowerCase();
  if (!q) {{ unhighlight(); return; }}
  const matched = new Set(GRAPH.nodes
    .filter(d => d.label.toLowerCase().includes(q) || d.local.toLowerCase().includes(q))
    .map(d => d.id));
  node.classed("highlighted", d => matched.has(d.id))
      .classed("dimmed", d => !matched.has(d.id));
  link.classed("dimmed", d => !matched.has(d.source.id) && !matched.has(d.target.id));
  linkLabel.classed("dimmed", d => !matched.has(d.source.id) && !matched.has(d.target.id));
}});

function unhighlight() {{
  node.classed("highlighted", false).classed("dimmed", false);
  link.classed("dimmed", false);
  linkLabel.classed("dimmed", false);
}}

// Sidebar
function onNodeClick(event, d) {{
  event.stopPropagation();
  const sb = document.getElementById("sidebar");
  sb.style.display = "block";
  document.getElementById("sb-title").textContent = d.label;

  const connLinks = GRAPH.links.filter(l =>
    (l.source.id || l.source) === d.id || (l.target.id || l.target) === d.id);
  const parents = connLinks.filter(l=>l.kind==="subclass" && (l.source.id||l.source)===d.id)
    .map(l => GRAPH.nodes.find(n=>n.id===(l.target.id||l.target))?.label || "?");
  const children = connLinks.filter(l=>l.kind==="subclass" && (l.target.id||l.target)===d.id)
    .map(l => GRAPH.nodes.find(n=>n.id===(l.source.id||l.source))?.label || "?");
  const outProps = connLinks.filter(l=>l.kind==="objprop" && (l.source.id||l.source)===d.id)
    .map(l => `${{l.label}} → ${{GRAPH.nodes.find(n=>n.id===(l.target.id||l.target))?.label||"?"}}`);
  const inProps = connLinks.filter(l=>l.kind==="objprop" && (l.target.id||l.target)===d.id)
    .map(l => `${{GRAPH.nodes.find(n=>n.id===(l.source.id||l.source))?.label||"?"}} → ${{l.label}}`);

  let html = `<div style="font-size:11px;color:#7eb8f7;margin-bottom:6px;">:<b>${{d.local}}</b></div>`;
  if (d.comment) html += `<p style="font-size:10px;color:#aaa;margin-bottom:8px;">${{d.comment}}</p>`;

  if (HAS_COMPARE) {{
    const badge = d.in_gold
      ? `<span class="badge" style="background:#1e8449">✓ In Gold</span>`
      : `<span class="badge" style="background:#922b21">✗ Not in Gold</span>`;
    html += badge;
  }}

  if (parents.length) html += `<div class="prop-list" style="margin-top:8px"><b>subClassOf:</b><ul>${{parents.map(p=>`<li>${{p}}</li>`).join("")}}</ul></div>`;
  if (children.length) html += `<div class="prop-list"><b>Subclasses:</b><ul>${{children.map(p=>`<li>${{p}}</li>`).join("")}}</ul></div>`;
  if (outProps.length) html += `<div class="prop-list"><b>Out properties:</b><ul>${{outProps.map(p=>`<li>${{p}}</li>`).join("")}}</ul></div>`;
  if (inProps.length) html += `<div class="prop-list"><b>In properties:</b><ul>${{inProps.map(p=>`<li>${{p}}</li>`).join("")}}</ul></div>`;
  if (d.dt_props.length) html += `<div class="prop-list"><b>Data properties:</b><ul>${{d.dt_props.map(p=>`<li>${{p}}</li>`).join("")}}</ul></div>`;

  document.getElementById("sb-body").innerHTML = html;

  // Highlight connected nodes
  const connIds = new Set([d.id, ...connLinks.map(l=>(l.source.id||l.source)), ...connLinks.map(l=>(l.target.id||l.target))]);
  node.classed("highlighted", n => connIds.has(n.id)).classed("dimmed", n => !connIds.has(n.id));
  link.classed("dimmed", l => !connIds.has(l.source.id||l.source) || !connIds.has(l.target.id||l.target));
  linkLabel.classed("dimmed", l => !connIds.has(l.source.id||l.source) || !connIds.has(l.target.id||l.target));
}}

svg.on("click", () => {{
  document.getElementById("sidebar").style.display = "none";
  unhighlight();
}});
</script>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# Colab helper
# ---------------------------------------------------------------------------

def show_in_colab(html: str, height: int = 800):
    """Display HTML visualization inline in a Colab notebook."""
    from IPython.display import display, HTML
    display(HTML(f'<div style="height:{height}px">{html}</div>'))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Interactive ontology visualizer")
    parser.add_argument("input", help=".ttl file or JSON result file")
    parser.add_argument("--output", "-o", default=None,
                        help="Output HTML path (default: <input_stem>_viz.html)")
    parser.add_argument("--compare", "-c", default=None,
                        help="Gold standard TTL for coverage coloring")
    parser.add_argument("--title", "-t", default=None, help="Display title")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: File not found: {args.input}")
        sys.exit(1)

    print(f"Parsing: {args.input}")
    html = visualize_to_html(args.input, compare_path=args.compare, title=args.title)

    if args.output:
        out_path = args.output
    else:
        stem = os.path.splitext(args.input)[0]
        out_path = stem + "_viz.html"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Saved: {out_path}")
    print(f"Open in browser: file://{os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
