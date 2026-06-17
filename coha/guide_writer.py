"""
Guide Writer: writes FQ and DK self-improving guides as Markdown files.
Called by COHAHarness after each CQ whenever a guide is updated.

FQ guide  — lessons learned from gate failures (patterns to avoid)
DK guide  — doctrine-grounded success cases (patterns to reuse)
"""
import os
import re
from typing import List


def _safe(name: str) -> str:
    """Convert variant name to a filesystem-safe string (alphanumeric + underscore only)."""
    return re.sub(r"[^a-zA-Z0-9]", "_", name).lower()


# ---------------------------------------------------------------------------
# FQ rule metadata used for guide rendering
# (mirrors FQ_VIOLATION_GUIDANCE in phase_gate.py — kept local to avoid circular import)
# ---------------------------------------------------------------------------

_FQ_STATIC_GUIDANCE: dict = {
    "FQ-OBJPROP-DOMRANGE": (
        "Always declare both rdfs:domain and rdfs:range for every owl:ObjectProperty"
    ),
    "FQ-DATPROP-XSD-RANGE": (
        "Use only xsd: datatypes (xsd:string, xsd:integer, xsd:boolean, xsd:float) "
        "for owl:DatatypeProperty range"
    ),
    "FQ-CLASS-LABEL": (
        "Every owl:Class declaration must include rdfs:label with a human-readable name"
    ),
    "FQ-PROP-LABEL": (
        "Every owl:ObjectProperty and owl:DatatypeProperty must include rdfs:label"
    ),
    "FQ-SUBCLASS-RESOURCE": (
        "rdfs:subClassOf target must be a class URI — never a string literal"
    ),
    "FQ-NO-PROP-TYPE-CONFLICT": (
        "Declare each property as owl:ObjectProperty OR owl:DatatypeProperty — never both"
    ),
    "FQ-NO-CLASS-PROP-CONFLICT": (
        "An entity must not be declared as both owl:Class and a property type"
    ),
    "FQ-PARSE": (
        "Output must be valid Turtle syntax — no markdown fences, no prose, only RDF triples. "
        "Every @prefix line MUST end with a period: '@prefix owl: <...> .' (dot required). "
        "Every triple MUST end with '.' or ';' as appropriate."
    ),
}

# Reverse map: static guidance string → rule ID
_GUIDANCE_TO_RULE: dict = {v: k for k, v in _FQ_STATIC_GUIDANCE.items()}

_FQ_RULE_TITLE: dict = {
    "FQ-OBJPROP-DOMRANGE":      "ObjectProperty missing rdfs:domain / rdfs:range",
    "FQ-DATPROP-XSD-RANGE":     "DatatypeProperty range must be an xsd: type",
    "FQ-CLASS-LABEL":           "owl:Class missing rdfs:label",
    "FQ-PROP-LABEL":            "Property missing rdfs:label",
    "FQ-SUBCLASS-RESOURCE":     "rdfs:subClassOf target must be a URI, not a literal",
    "FQ-NO-PROP-TYPE-CONFLICT": "Property declared as both ObjectProperty and DatatypeProperty",
    "FQ-NO-CLASS-PROP-CONFLICT":"Entity declared as both owl:Class and a property",
    "FQ-PARSE":                 "Invalid Turtle syntax (parse error)",
}

# Wrong → correct code examples for each rule
_FQ_CODE_EXAMPLES: dict = {
    "FQ-OBJPROP-DOMRANGE": {
        "wrong": ":suitedForTerrain a owl:ObjectProperty ;\n    rdfs:label \"suited for terrain\" .",
        "correct": ":suitedForTerrain a owl:ObjectProperty ;\n    rdfs:label \"suited for terrain\" ;\n    rdfs:domain :Unit ;\n    rdfs:range :TerrainType .",
    },
    "FQ-DATPROP-XSD-RANGE": {
        "wrong": ":threatScore a owl:DatatypeProperty ;\n    rdfs:label \"threat score\" ;\n    rdfs:domain :ThreatLevel ;\n    rdfs:range :Score .   # ❌ :Score is not an xsd: type",
        "correct": ":threatScore a owl:DatatypeProperty ;\n    rdfs:label \"threat score\" ;\n    rdfs:domain :ThreatLevel ;\n    rdfs:range xsd:float .  # ✓ use xsd:string / xsd:integer / xsd:boolean / xsd:float",
    },
    "FQ-CLASS-LABEL": {
        "wrong": ":TerrainType a owl:Class .   # ❌ no rdfs:label",
        "correct": ":TerrainType a owl:Class ;\n    rdfs:label \"Terrain Type\" .  # ✓ human-readable label required",
    },
    "FQ-PROP-LABEL": {
        "wrong": ":operatesIn a owl:ObjectProperty ;\n    rdfs:domain :Unit ;\n    rdfs:range :TerrainType .   # ❌ no rdfs:label",
        "correct": ":operatesIn a owl:ObjectProperty ;\n    rdfs:label \"operates in\" ;  # ✓ label required\n    rdfs:domain :Unit ;\n    rdfs:range :TerrainType .",
    },
    "FQ-SUBCLASS-RESOURCE": {
        "wrong": ':ArmorUnit rdfs:subClassOf "Unit" .   # ❌ string literal, not a URI',
        "correct": ":ArmorUnit rdfs:subClassOf :Unit .  # ✓ URI reference",
    },
    "FQ-NO-PROP-TYPE-CONFLICT": {
        "wrong": ":operatesIn a owl:ObjectProperty, owl:DatatypeProperty ;\n    rdfs:label \"operates in\" .   # ❌ declared as both",
        "correct": ":operatesIn a owl:ObjectProperty ;  # ✓ pick exactly one\n    rdfs:label \"operates in\" ;\n    rdfs:domain :Unit ;\n    rdfs:range :TerrainType .",
    },
    "FQ-NO-CLASS-PROP-CONFLICT": {
        "wrong": ":TerrainType a owl:Class, owl:ObjectProperty .   # ❌ same URI is both",
        "correct": "# ✓ use separate URIs for the class and the property\n:TerrainType a owl:Class ;\n    rdfs:label \"Terrain Type\" .\n\n:operatesIn a owl:ObjectProperty ;\n    rdfs:label \"operates in\" ;\n    rdfs:domain :Unit ;\n    rdfs:range :TerrainType .",
    },
    "FQ-PARSE": {
        "wrong": "```turtle\n:Unit a owl:Class ;\n    rdfs:label \"Unit\"   # ❌ no trailing dot, wrapped in markdown fence",
        "correct": "# ✓ plain Turtle only — no ``` fences, no trailing prose\n:Unit a owl:Class ;\n    rdfs:label \"Unit\" .\n\n:operatesIn a owl:ObjectProperty ;\n    rdfs:label \"operates in\" ;\n    rdfs:domain :Unit ;\n    rdfs:range :TerrainType .",
    },
}


def _infer_rule_from_message(msg: str) -> str:
    """Guess a rule ID from the text of a specific violation message."""
    m = msg.lower()
    if "objectproperty" in m and ("domain" in m or "range" in m):
        return "FQ-OBJPROP-DOMRANGE"
    if "datatypeproperty" in m:
        return "FQ-DATPROP-XSD-RANGE"
    if "class" in m and "label" in m:
        return "FQ-CLASS-LABEL"
    if "property" in m and "label" in m:
        return "FQ-PROP-LABEL"
    if "subclassof" in m and "literal" in m:
        return "FQ-SUBCLASS-RESOURCE"
    if "both objectproperty and datatypeproperty" in m:
        return "FQ-NO-PROP-TYPE-CONFLICT"
    if "class and a property" in m or "class and property" in m:
        return "FQ-NO-CLASS-PROP-CONFLICT"
    if "turtle" in m or "syntax" in m or "parse" in m or "@prefix" in m:
        return "FQ-PARSE"
    return ""


# ---------------------------------------------------------------------------
# FQ guide writer
# ---------------------------------------------------------------------------

def write_fq_guide(patterns: List[str], iteration: int, output_dir: str, variant: str = "") -> str:
    """Write FQ OWL generation guide grouped by rule, with error messages and code fixes.

    Each section shows:
      - The rule that fired
      - The exact gate error message(s) the model triggered
      - A collapsible wrong-vs-correct Turtle code block

    Returns path written.
    """
    os.makedirs(output_dir, exist_ok=True)
    fname = f"fq_guide_{_safe(variant)}.md" if variant else "fq_guide.md"
    path = os.path.join(output_dir, fname)

    # ---- Group patterns back to rule IDs ----
    # patterns alternates: [static_guidance_for_rule, specific_error_msg, ...]
    # static strings are identifiable via _GUIDANCE_TO_RULE; the rest are specifics.
    rule_specifics: dict = {}   # rule_id → [specific error message, ...]
    ungrouped: List[str] = []

    i = 0
    while i < len(patterns):
        p = patterns[i]
        rule_id = _GUIDANCE_TO_RULE.get(p)
        if rule_id:
            # Static guidance string found — the next item (if any) is the specific msg
            rule_specifics.setdefault(rule_id, [])
            if i + 1 < len(patterns) and patterns[i + 1] not in _GUIDANCE_TO_RULE:
                msg = patterns[i + 1]
                if msg not in rule_specifics[rule_id]:
                    rule_specifics[rule_id].append(msg)
                i += 2
            else:
                i += 1
        else:
            # Specific error message without a preceding static string
            inferred = _infer_rule_from_message(p)
            if inferred:
                lst = rule_specifics.setdefault(inferred, [])
                if p not in lst:
                    lst.append(p)
            else:
                ungrouped.append(p)
            i += 1

    n_rules = len(rule_specifics)
    n_errors = sum(len(v) for v in rule_specifics.values()) + len(ungrouped)

    lines = [
        "# FQ OWL Generation Guide",
        f"*Last updated: CQ {iteration} — {n_rules} rule(s) triggered, {n_errors} specific error(s) observed*",
        "",
        "> **How to use:** Each section shows the rule that fired, the exact error message",
        "> the gate returned, and a before/after code fix. Apply these before submitting",
        "> the next CQ to avoid the same gate failure.",
        "",
    ]

    if not rule_specifics and not ungrouped:
        lines += ["*No FQ violations observed yet.*", ""]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return path

    # ---- Quick-reference cheatsheet ----
    lines += [
        "## Quick Reference",
        "",
        "| Rule ID | What to fix |",
        "|---------|-------------|",
    ]
    for rule_id in rule_specifics:
        fix = _FQ_STATIC_GUIDANCE.get(rule_id, "See section below")
        # Trim to first sentence for table brevity
        fix_short = fix.split(" — ")[0].split(". ")[0]
        lines.append(f"| `{rule_id}` | {fix_short} |")
    lines += ["", "---", ""]

    # ---- Per-rule sections ----
    lines += ["## Violations Observed", ""]

    for rule_id, specifics in rule_specifics.items():
        title   = _FQ_RULE_TITLE.get(rule_id, rule_id)
        static  = _FQ_STATIC_GUIDANCE.get(rule_id, "")
        example = _FQ_CODE_EXAMPLES.get(rule_id)

        lines.append(f"### ❌ `{rule_id}` — {title}")
        lines.append("")

        if static:
            lines.append(f"**Fix:** {static}")
            lines.append("")

        if specifics:
            lines.append("**Gate error message(s) seen:**")
            lines.append("")
            for s in specifics[:4]:   # cap to keep guide readable
                lines.append("```")
                lines.append(s)
                lines.append("```")
            lines.append("")

        if example:
            lines.append("<details>")
            lines.append("<summary>Show wrong vs. correct code</summary>")
            lines.append("")
            lines.append("**❌ Wrong**")
            lines.append("```turtle")
            lines.append(example["wrong"])
            lines.append("```")
            lines.append("")
            lines.append("**✓ Correct**")
            lines.append("```turtle")
            lines.append(example["correct"])
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        lines.append("---")
        lines.append("")

    # ---- Catch-all for unmatched patterns ----
    if ungrouped:
        lines += ["## Other Patterns", ""]
        for p in ungrouped:
            lines.append(f"- {p}")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


# ---------------------------------------------------------------------------
# DK guide writer (unchanged)
# ---------------------------------------------------------------------------

def write_dk_guide(
    patterns: List[dict], iteration: int, output_dir: str, variant: str = "",
    failures: List[dict] = None,
) -> str:
    """Write DK guide: doctrine-grounded successes to FOLLOW and rejected
    candidates to AVOID. Returns path written."""
    os.makedirs(output_dir, exist_ok=True)
    fname = f"dk_guide_{_safe(variant)}.md" if variant else "dk_guide.md"
    path = os.path.join(output_dir, fname)
    failures = failures or []
    sorted_pats = sorted(patterns, key=lambda p: p.get("similarity", 0.0), reverse=True)
    lines = [
        "# DK Doctrine-Grounded Patterns Guide",
        f"*Last updated: CQ {iteration} — {len(patterns)} success case(s), {len(failures)} failure case(s)*",
        "",
        "Success cases were accepted by the DK gate and grounded in published doctrine —",
        "follow these patterns when generating axioms for similar competency questions.",
        "Failure cases were REJECTED by doctrine grounding — avoid repeating these mistakes.",
        "",
        "## ✅ Success Cases — follow these (sorted by doctrine similarity)",
        "",
    ]
    if sorted_pats:
        for i, p in enumerate(sorted_pats, 1):
            cq_label = f"CQ {p['cq_index']}" if p.get("cq_index") else "CQ ?"
            lines.append(f"### Case {i} ({cq_label})")
            lines.append(f"**CQ:** {p.get('cq_summary', 'N/A')}")
            lines.append(f"**OWL Pattern:** `{p.get('owl_pattern', 'N/A')}`")
            sim = p.get("similarity", 0.0)
            lines.append(f"**Doctrine:** {p.get('citation', 'N/A')} *(similarity: {sim:.3f})*")
            lines.append(f"**DK Rule:** {p.get('rule', 'N/A')}")
            lines.append("")
    else:
        lines.append("*No doctrine-grounded patterns recorded yet.*")
        lines.append("")
    lines.append("## ❌ Failure Cases — do NOT repeat these (most recent)")
    lines.append("")
    if failures:
        for i, p in enumerate(failures, 1):
            cq_label = f"CQ {p['cq_index']}" if p.get("cq_index") else "CQ ?"
            lines.append(f"### Mistake {i} ({cq_label})")
            lines.append(f"**CQ:** {p.get('cq_summary', 'N/A')}")
            if p.get("owl_pattern"):
                lines.append(f"**OWL Pattern that led to this:** `{p['owl_pattern']}`")
            lines.append(f"**Rejected Rule:** {p.get('rule', 'N/A')}")
            lines.append(f"**Why rejected:** {p.get('reason', 'no doctrine support')}")
            lines.append("")
    else:
        lines.append("*No rejected candidates recorded yet.*")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path
