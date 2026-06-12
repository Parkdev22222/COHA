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


def write_fq_guide(patterns: List[str], iteration: int, output_dir: str, variant: str = "") -> str:
    """Write FQ OWL generation guide. Returns path written."""
    os.makedirs(output_dir, exist_ok=True)
    fname = f"fq_guide_{_safe(variant)}.md" if variant else "fq_guide.md"
    path = os.path.join(output_dir, fname)
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
