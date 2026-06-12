"""
Guide Writer: writes FQ and DK self-improving guides as Markdown files.
Called by COHAHarness after each CQ whenever a guide is updated.

FQ guide  — lessons learned from gate failures (patterns to avoid)
DK guide  — doctrine-grounded success cases (patterns to reuse)
"""
import os
from typing import List


def write_fq_guide(patterns: List[str], iteration: int, output_dir: str) -> str:
    """Write FQ OWL generation guide. Returns path written."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "fq_guide.md")
    lines = [
        "# FQ OWL Generation Guide",
        f"*Last updated: CQ {iteration} — {len(patterns)} pattern(s) learned from gate failures*",
        "",
        "Apply these guidelines when generating OWL axioms to pass the FQ gate on the first attempt.",
        "",
        "## Patterns to Follow",
        "",
    ]
    if patterns:
        for p in patterns:
            lines.append(f"- {p}")
    else:
        lines.append("*No FQ violations observed yet.*")
    lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def write_dk_guide(patterns: List[dict], iteration: int, output_dir: str) -> str:
    """Write DK doctrine-grounded success patterns guide. Returns path written."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "dk_guide.md")
    sorted_pats = sorted(patterns, key=lambda p: p.get("similarity", 0.0), reverse=True)
    lines = [
        "# DK Doctrine-Grounded Success Patterns",
        f"*Last updated: CQ {iteration} — top {len(patterns)} case(s) by doctrine similarity*",
        "",
        "These OWL patterns were accepted by the DK gate and grounded in published doctrine.",
        "Use as reference when generating axioms for similar competency questions.",
        "",
        "## Success Cases (sorted by doctrine similarity)",
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
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path
