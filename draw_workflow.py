"""Draw the COHA full workflow diagram — paper version with LLM call badges."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Circle
from matplotlib.lines import Line2D

fig, ax = plt.subplots(figsize=(16, 24))
ax.set_xlim(0, 16)
ax.set_ylim(0, 24)
ax.axis("off")
fig.patch.set_facecolor("#FFFFFF")


# ── palette ──────────────────────────────────────────────────────────────────
C_IO       = "#D6EAF8"   # input / output
C_IO_B     = "#2471A3"
C_LOOP     = "#1ABC9C"
C_LOOP_B   = "#0E8A70"
C_GEN      = "#D5F5E3"   # generation
C_GEN_B    = "#1E8449"
C_GATE     = "#EDE7F6"   # phase gate interior
C_GATE_B   = "#6C3483"
C_GATE_H   = "#D7BDE2"   # gate header
C_CTX      = "#FEF9E7"   # context reset zone
C_CTX_B    = "#E67E22"
C_HAND     = "#EBF5FB"   # handoff
C_HAND_B   = "#2471A3"
C_REJ      = "#FADBD8"   # rejection
C_REJ_B    = "#C0392B"
C_LLM      = "#FF6B35"   # LLM badge
C_LLM_T    = "#FFFFFF"
C_OUT      = "#F0F3F4"


# ── helpers ───────────────────────────────────────────────────────────────────
def rbox(x, y, w, h, fc, ec, lw=1.2, radius=0.22, zorder=3):
    """Draw a rounded rectangle patch and return it."""
    p = FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle=f"round,pad=0.04,rounding_size={radius}",
        linewidth=lw, edgecolor=ec, facecolor=fc, zorder=zorder,
    )
    ax.add_patch(p)
    return p

def box(x, y, w, h, title, subtitle=None,
        fc="#FFFFFF", ec="#555", fontsize=9, bold=False, zorder=3):
    rbox(x, y, w, h, fc, ec, zorder=zorder)
    weight = "bold" if bold else "normal"
    ty = y + (0.16 if subtitle else 0)
    ax.text(x, ty, title, ha="center", va="center",
            fontsize=fontsize, color="#1A1A2E", fontweight=weight, zorder=zorder+1)
    if subtitle:
        ax.text(x, y - 0.22, subtitle, ha="center", va="center",
                fontsize=7.2, color="#666", style="italic", zorder=zorder+1)

def diamond(x, y, w, h, label, fc="#FFF3CD", ec="#E67E22"):
    dx, dy = w/2, h/2
    xs = [x, x+dx, x,    x-dx, x]
    ys = [y+dy, y, y-dy, y,    y+dy]
    ax.fill(xs, ys, color=fc, zorder=3)
    ax.plot(xs, ys, color=ec, lw=1.3, zorder=4)
    ax.text(x, y, label, ha="center", va="center",
            fontsize=8.5, fontweight="bold", color="#7D3C00", zorder=5)

def arr(x1, y1, x2, y2, label="", color="#444", lw=1.4,
        style="-|>", shrinkA=3, shrinkB=3, label_offset=(0.12, 0)):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color,
                                lw=lw, shrinkA=shrinkA, shrinkB=shrinkB),
                zorder=2)
    if label:
        mx = (x1+x2)/2 + label_offset[0]
        my = (y1+y2)/2 + label_offset[1]
        ax.text(mx, my, label, fontsize=7.8, color=color, va="center",
                fontweight="bold", zorder=5)

def hline(x1, x2, y, color="#444", lw=1.4):
    ax.plot([x1, x2], [y, y], color=color, lw=lw, zorder=2)

def vline(x, y1, y2, color="#444", lw=1.4):
    ax.plot([x, x], [y1, y2], color=color, lw=lw, zorder=2)

def bg_rect(x, y, w, h, fc, ec="#AAA", alpha=0.25, lw=1.0, label="", zorder=0):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle="round,pad=0.04,rounding_size=0.3",
                       linewidth=lw, edgecolor=ec,
                       facecolor=fc, alpha=alpha, zorder=zorder)
    ax.add_patch(p)
    if label:
        ax.text(x + 0.2, y + h - 0.18, label, fontsize=8,
                color="#333", fontweight="bold", va="top", zorder=zorder+1)

def llm_badge(x, y, number, size=0.38):
    """Draw an LLM call badge: orange circle with number."""
    circ = Circle((x, y), size/2, color=C_LLM, zorder=8)
    ax.add_patch(circ)
    ax.text(x, y, f"LLM\n{number}", ha="center", va="center",
            fontsize=6.5, color=C_LLM_T, fontweight="bold", zorder=9,
            linespacing=1.1)


C_DET = "#2E86C1"  # deterministic (rdflib) badge

def det_badge(x, y, size=0.38):
    """Draw a deterministic (rdflib, no LLM) badge: blue circle."""
    circ = Circle((x, y), size/2, color=C_DET, zorder=8)
    ax.add_patch(circ)
    ax.text(x, y, "rdf\nlib", ha="center", va="center",
            fontsize=6.0, color="white", fontweight="bold", zorder=9,
            linespacing=1.1)


# ═══════════════════════════════════════════════════════════════════════════════
# TITLE
# ═══════════════════════════════════════════════════════════════════════════════
ax.text(8, 23.45, "COHA: CQ-Driven Ontology Harness",
        ha="center", va="center", fontsize=15, fontweight="bold", color="#1A1A2E")
ax.text(8, 22.95, "with Self-Improving Phase Gate",
        ha="center", va="center", fontsize=11, color="#555")

# ═══════════════════════════════════════════════════════════════════════════════
# INPUTS
# ═══════════════════════════════════════════════════════════════════════════════
box(4.3, 22.15, 4.2, 0.65, "Competency Questions  [CQ₁ … CQₙ]",
    fc=C_IO, ec=C_IO_B, fontsize=9, bold=True)
box(11.7, 22.15, 3.8, 0.65, "User Story",
    fc=C_IO, ec=C_IO_B, fontsize=9, bold=True)

arr(4.3, 21.82, 6.8, 21.35)
arr(11.7, 21.82, 9.2, 21.35)

# ═══════════════════════════════════════════════════════════════════════════════
# INIT HANDOFF
# ═══════════════════════════════════════════════════════════════════════════════
box(8, 21.1, 5.4, 0.6, "Initialize  HandoffArtifact  (empty)",
    fc=C_HAND, ec=C_HAND_B, fontsize=9)
arr(8, 20.8, 8, 20.35)

# ═══════════════════════════════════════════════════════════════════════════════
# LOOP BACKGROUND  (y: 3.5 → 20.3)
# ═══════════════════════════════════════════════════════════════════════════════
bg_rect(0.35, 3.5, 15.3, 16.8, "#E8F8F5", ec="#1ABC9C", alpha=0.18, lw=1.2,
        label="For each CQ  (i = 1, 2, … , n)", zorder=0)

# LOOP HEADER
box(8, 20.1, 4.4, 0.5, "For each  CQ_i",
    fc=C_LOOP, ec=C_LOOP_B, bold=True, fontsize=10)
ax.text(8, 20.1, "For each  CQ_i", ha="center", va="center",
        fontsize=10, color="white", fontweight="bold", zorder=5)
# clear duplicate text from box() — redraw text in white
ax.texts[-2].set_visible(False)

arr(8, 19.85, 8, 19.3)

# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT RESET ZONE
# ═══════════════════════════════════════════════════════════════════════════════
bg_rect(0.9, 17.55, 14.2, 1.85, "#FEF9E7", ec=C_CTX_B, alpha=0.4, lw=1.2,
        label="Context Reset  —  fresh LLM context per CQ", zorder=1)

# Handoff Artifact box
rbox(5.1, 18.6, 6.0, 1.1, C_CTX, C_CTX_B, zorder=3)
ax.text(5.1, 18.98, "Handoff Artifact  →  System Prompt",
        ha="center", va="center", fontsize=8.8, fontweight="bold",
        color="#784212", zorder=4)
ax.text(5.1, 18.55, "• Ontology summary  (classes / properties / consistency)",
        ha="center", va="center", fontsize=7.6, color="#555", zorder=4)
ax.text(5.1, 18.2, "• FQ Rules  •  DK Rules  •  completed_cqs  •  next_cq",
        ha="center", va="center", fontsize=7.6, color="#555", zorder=4)

# User Prompt box
rbox(11.8, 18.6, 4.1, 1.1, C_CTX, C_CTX_B, zorder=3)
ax.text(11.8, 18.98, "User Prompt",
        ha="center", va="center", fontsize=8.8, fontweight="bold",
        color="#784212", zorder=4)
ax.text(11.8, 18.55, "• User Story  •  CQ_i  •  key_entities",
        ha="center", va="center", fontsize=7.6, color="#555", zorder=4)
ax.text(11.8, 18.2, "• ⚠ violation hints  (on retry)",
        ha="center", va="center", fontsize=7.6, color="#C0392B", zorder=4)

arr(5.1, 18.05, 6.8, 17.45)
arr(11.8, 18.05, 9.2, 17.45)

# ═══════════════════════════════════════════════════════════════════════════════
# AXIOM GENERATOR  — LLM ①
# ═══════════════════════════════════════════════════════════════════════════════
box(8, 17.1, 6.4, 0.75,
    "Axiom Generator  →  delta-Oi",
    subtitle="generate_with_reset()  /  generate_with_metacognition_reset()",
    fc=C_GEN, ec=C_GEN_B, bold=True, fontsize=9.5)
llm_badge(11.42, 17.38, "①")

arr(8, 16.72, 8, 16.2)

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE GATE BACKGROUND  (y: 8.2 → 16.15)
# ═══════════════════════════════════════════════════════════════════════════════
bg_rect(0.9, 8.2, 14.2, 8.0, "#F4ECF7", ec="#8E44AD", alpha=0.28, lw=1.3,
        label="Self-Improving Phase Gate", zorder=1)

# ── Step 1: FQ Validation  — deterministic (rdflib)
box(6.0, 15.75, 6.2, 0.8,
    "Step 1 · Formal Quality (FQ) Validation",
    subtitle="deterministic rdflib checks (FQ_checker)  →  fq_violations",
    fc=C_GATE, ec=C_GATE_B, bold=True, fontsize=9)
det_badge(9.28, 16.03)

arr(6.0, 15.35, 6.0, 14.8)

# ── Step 2: DK Validation  — LLM ②  ([STRUCT] rules only)
box(6.0, 14.45, 6.2, 0.8,
    "Step 2 · Domain Knowledge (DK) Validation",
    subtitle="_validate_domain  →  [STRUCT] rules only  →  dk_violations",
    fc=C_GATE, ec=C_GATE_B, bold=True, fontsize=9)
llm_badge(9.28, 14.73, "②")

arr(6.0, 14.05, 6.0, 13.55)

# ── Step 3: Rule Extraction background
bg_rect(1.1, 12.15, 13.8, 1.5, "#EDE7F6", ec="#7B1FA2", alpha=0.4, lw=1.0,
        label="Step 3 · Rule Extraction", zorder=2)

# FQ Extraction  — deterministic (check activation)
box(5.0, 12.9, 5.6, 0.75,
    "Activate new FQ checks",
    subtitle="first-seen violation → activate (rdflib)",
    fc=C_GATE, ec=C_GATE_B, fontsize=8.8)
det_badge(7.97, 13.16)

# DK Extraction + doctrine grounding  — LLM ③
box(11.0, 12.9, 5.6, 0.75,
    "Extract + ground DK Rules",
    subtitle="_extract_dk_rules → doctrine grounding",
    fc=C_GATE, ec=C_GATE_B, fontsize=8.8)
llm_badge(13.97, 13.16, "③")

arr(4.8, 14.05, 4.8, 13.28)
arr(7.2, 14.05, 10.5, 13.28)

# ── DK Conflict Resolution  — LLM ④
box(8, 11.35, 7.0, 0.8,
    "DK Conflict Resolution",
    subtitle="resolve_dk_conflicts(existing, new)  —  LLM adjudicates contradictions",
    fc=C_GATE_H, ec="#76448A", fontsize=9)
llm_badge(11.72, 11.63, "④")

arr(5.0, 12.52, 6.5, 11.75)
arr(11.0, 12.52, 9.5, 11.75)

arr(8, 10.95, 8, 10.45)

# ── Updated rule sets
box(8, 10.15, 7.0, 0.6,
    "FQ_{k+1} = FQ_k ∪ new_fq     DK_{k+1} = resolve(DK_k, new_dk)",
    fc=C_GATE_H, ec="#76448A", fontsize=8.5)

# ── Gate decision
arr(8, 9.85, 8, 9.35)
diamond(8, 8.8, 3.4, 1.0, "Gate Passed?")

# ═══════════════════════════════════════════════════════════════════════════════
# PASS PATH  →  right
# ═══════════════════════════════════════════════════════════════════════════════
arr(9.7, 8.8, 12.6, 8.8, label=" YES", color=C_GEN_B, label_offset=(0, 0.15))
box(13.3, 8.8, 2.0, 0.65, "Accept\ndelta-Oi", fc=C_GEN, ec=C_GEN_B, bold=True, fontsize=8.5)
arr(13.3, 8.47, 13.3, 7.85)
box(13.3, 7.55, 2.5, 0.6, "Merge into\nOntology TTL", fc=C_GEN, ec=C_GEN_B, fontsize=8)

# ═══════════════════════════════════════════════════════════════════════════════
# FAIL PATH  →  left
# ═══════════════════════════════════════════════════════════════════════════════
arr(6.3, 8.8, 3.5, 8.8, label="NO ", color=C_REJ_B, label_offset=(-0.05, 0.15))
box(2.7, 8.8, 2.2, 0.65, "Gate\nRejected", fc=C_REJ, ec=C_REJ_B, bold=True, fontsize=8.5)

arr(2.7, 8.47, 2.7, 7.85)
diamond(2.7, 7.3, 2.9, 0.95, "retry < max?", fc="#FEF9E7", ec=C_CTX_B)

# retry YES  →  back to axiom generator
arr(1.25, 7.3, 1.25, 17.1, label="", color=C_CTX_B, lw=1.5, shrinkA=0, shrinkB=0)
hline(1.25, 4.8, 17.1, color=C_CTX_B, lw=1.5)
ax.annotate("", xy=(4.8, 17.1), xytext=(4.8, 17.1),
            arrowprops=dict(arrowstyle="-|>", color=C_CTX_B, lw=1.5,
                            shrinkA=0, shrinkB=3), zorder=2)
ax.text(0.75, 12.0, "YES\n(+violations)", fontsize=7.5, color=C_CTX_B,
        rotation=90, va="center", ha="center", fontweight="bold", zorder=5)

# retry NO  →  discard
arr(2.7, 6.82, 2.7, 6.25, color=C_REJ_B, label="NO ", label_offset=(-0.55, 0))
box(2.7, 5.95, 2.8, 0.6, "Discard delta-Oi\n(rules still updated)",
    fc=C_REJ, ec=C_REJ_B, fontsize=7.8)

# ═══════════════════════════════════════════════════════════════════════════════
# UPDATE HANDOFF  — merge both pass & discard paths
# ═══════════════════════════════════════════════════════════════════════════════
# pass path down
arr(13.3, 7.25, 13.3, 5.1)
hline(13.3, 9.0, 5.1, color="#444", lw=1.4)
ax.annotate("", xy=(9.0, 5.1), xytext=(9.0, 4.9),
            arrowprops=dict(arrowstyle="-|>", color="#444", lw=1.4), zorder=2)

# discard path across
arr(2.7, 5.65, 2.7, 5.1)
hline(2.7, 7.1, 5.1, color="#444", lw=1.4)
ax.annotate("", xy=(7.1, 5.1), xytext=(7.1, 4.9),
            arrowprops=dict(arrowstyle="-|>", color="#444", lw=1.4), zorder=2)

box(8, 4.7, 8.5, 0.7,
    "Update HandoffArtifact  (iteration k+1)",
    subtitle="classes · properties · consistency · FQ_rules · DK_rules · next_cq · completed_cqs",
    fc=C_HAND, ec=C_HAND_B, bold=True, fontsize=9)

# ── back-edge to loop
arr(8, 4.35, 8, 3.95)
box(8, 3.7, 3.8, 0.45, "i < n  →  next CQ",
    fc=C_LOOP, ec=C_LOOP_B, fontsize=9)
ax.text(8, 3.7, "i < n  →  next CQ", ha="center", va="center",
        fontsize=9, color="white", fontweight="bold", zorder=5)
ax.texts[-1]   # keep

# loop back arrow along left edge
vline(0.55, 3.7, 20.1, color=C_LOOP_B, lw=1.6)
hline(0.55, 5.65, 20.1, color=C_LOOP_B, lw=1.6)
ax.annotate("", xy=(5.65, 20.1), xytext=(5.65, 20.1),
            arrowprops=dict(arrowstyle="-|>", color=C_LOOP_B, lw=1.6,
                            shrinkA=0, shrinkB=3), zorder=2)
arr(3.9, 3.7, 0.55, 3.7, color=C_LOOP_B, lw=1.6, shrinkA=3, shrinkB=0)
ax.text(0.2, 12.0, "next CQ", fontsize=7.5, color=C_LOOP_B,
        rotation=90, va="center", ha="center", fontweight="bold", zorder=5)

# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUTS
# ═══════════════════════════════════════════════════════════════════════════════
arr(8, 3.47, 8, 2.95)
hline(3.2, 12.8, 2.7, color=C_IO_B, lw=1.3)

out_items = [
    (3.2,  2.1, 3.5, "Final Ontology TTL\n(merged)",        C_IO,  C_IO_B),
    (8.0,  2.1, 3.5, "Metrics\n(SC · CCR · ODP · CE)",      C_GEN, C_GEN_B),
    (12.8, 2.1, 3.5, "FQ/DK Rules\n+ Token Usage Stats",    C_GATE, C_GATE_B),
]
for ox, oy, ow, ol, oc, ob in out_items:
    vline(ox, 2.7, oy+0.45, color=ob, lw=1.2)
    ax.annotate("", xy=(ox, oy+0.45), xytext=(ox, oy+0.45),
                arrowprops=dict(arrowstyle="-|>", color=ob, lw=1.2,
                                shrinkA=0, shrinkB=2), zorder=2)
    rbox(ox, oy, ow, 0.88, oc, ob, lw=1.3, zorder=4)
    ax.text(ox, oy, ol, ha="center", va="center",
            fontsize=8.2, fontweight="bold", color="#1A1A2E", zorder=5)

# ═══════════════════════════════════════════════════════════════════════════════
# LEGEND
# ═══════════════════════════════════════════════════════════════════════════════
legend_patches = [
    mpatches.Patch(fc=C_IO,   ec=C_IO_B,   label="Input / Output",      lw=1.2),
    mpatches.Patch(fc=C_GEN,  ec=C_GEN_B,  label="Axiom Generation",    lw=1.2),
    mpatches.Patch(fc=C_CTX,  ec=C_CTX_B,  label="Context Reset zone",  lw=1.2),
    mpatches.Patch(fc=C_GATE, ec=C_GATE_B, label="Phase Gate step",     lw=1.2),
    mpatches.Patch(fc=C_HAND, ec=C_HAND_B, label="Handoff Artifact",    lw=1.2),
    mpatches.Patch(fc=C_REJ,  ec=C_REJ_B,  label="Rejection / Retry",   lw=1.2),
    mpatches.Patch(fc=C_LLM,  ec=C_LLM,    label="LLM call  ①–④",      lw=0),
    mpatches.Patch(fc=C_DET,  ec=C_DET,    label="Deterministic (rdflib)", lw=0),
]
ax.legend(handles=legend_patches, loc="lower right",
          fontsize=8.2, framealpha=0.92, edgecolor="#CCCCCC",
          bbox_to_anchor=(0.995, 0.0), ncol=1)

plt.tight_layout(pad=0.3)
plt.savefig("/home/user/COHA/coha_workflow.png", dpi=160,
            bbox_inches="tight", facecolor="white")
print("Saved coha_workflow.png")
