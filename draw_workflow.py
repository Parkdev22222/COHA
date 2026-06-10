"""Draw the COHA full workflow diagram."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe

fig, ax = plt.subplots(figsize=(16, 22))
ax.set_xlim(0, 16)
ax.set_ylim(0, 22)
ax.axis("off")
fig.patch.set_facecolor("#F8F9FA")


# ── helpers ──────────────────────────────────────────────────────────────────
def box(x, y, w, h, label, color="#FFFFFF", textcolor="#1A1A2E",
        fontsize=9, bold=False, radius=0.25, border="#555555",
        sublabel=None):
    b = FancyBboxPatch((x - w/2, y - h/2), w, h,
                       boxstyle=f"round,pad=0.05,rounding_size={radius}",
                       linewidth=1.2, edgecolor=border, facecolor=color, zorder=3)
    ax.add_patch(b)
    weight = "bold" if bold else "normal"
    y_text = y + (0.18 if sublabel else 0)
    ax.text(x, y_text, label, ha="center", va="center",
            fontsize=fontsize, color=textcolor, fontweight=weight, zorder=4,
            wrap=True)
    if sublabel:
        ax.text(x, y - 0.28, sublabel, ha="center", va="center",
                fontsize=7.5, color="#555555", zorder=4, style="italic")

def diamond(x, y, w, h, label, color="#FFF3CD", border="#E67E22"):
    dx, dy = w/2, h/2
    xs = [x,      x+dx,  x,      x-dx,  x]
    ys = [y+dy,   y,     y-dy,   y,     y+dy]
    ax.fill(xs, ys, color=color, zorder=3)
    ax.plot(xs, ys, color=border, linewidth=1.2, zorder=4)
    ax.text(x, y, label, ha="center", va="center",
            fontsize=8.5, fontweight="bold", color="#7D3C00", zorder=5)

def arr(x1, y1, x2, y2, label="", color="#444444", lw=1.4,
        style="-|>", shrink=3):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color,
                                lw=lw, shrinkA=shrink, shrinkB=shrink),
                zorder=2)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx+0.12, my, label, fontsize=7.5, color=color,
                va="center", zorder=5)

def hline(y, x1, x2, color="#BBBBBB", lw=1, ls="--"):
    ax.plot([x1, x2], [y, y], color=color, lw=lw, ls=ls, zorder=1)

def rect_bg(x, y, w, h, color, label="", alpha=0.18, radius=0.3, border="#999999"):
    b = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0.05,rounding_size={radius}",
                       linewidth=1.0, edgecolor=border,
                       facecolor=color, alpha=alpha, zorder=1)
    ax.add_patch(b)
    if label:
        ax.text(x + 0.18, y + h - 0.22, label, fontsize=7.5,
                color="#333333", fontweight="bold", va="top", zorder=2)


# ═══════════════════════════════════════════════════════════════════════════
# TITLE
# ═══════════════════════════════════════════════════════════════════════════
ax.text(8, 21.5, "COHA Full Workflow", ha="center", va="center",
        fontsize=16, fontweight="bold", color="#1A1A2E")
ax.text(8, 21.05, "CQ-Driven Ontology Harness with Self-Improving Phase Gate",
        ha="center", va="center", fontsize=10, color="#555555")

# ═══════════════════════════════════════════════════════════════════════════
# INPUTS  (y ≈ 20)
# ═══════════════════════════════════════════════════════════════════════════
box(4.5, 20.2, 3.8, 0.7, "CQ List  [CQ₁, CQ₂, …, CQₙ]",
    color="#D6EAF8", border="#2471A3", bold=True, fontsize=9)
box(11.5, 20.2, 3.8, 0.7, "User Story",
    color="#D6EAF8", border="#2471A3", bold=True, fontsize=9)

arr(4.5, 19.85, 7.0, 19.35)
arr(11.5, 19.85, 9.0, 19.35)

# ═══════════════════════════════════════════════════════════════════════════
# INIT  (y ≈ 19)
# ═══════════════════════════════════════════════════════════════════════════
box(8, 19.05, 5.2, 0.65, "Initialize  HandoffArtifact  (empty)",
    color="#EBF5FB", border="#2471A3", fontsize=9)

arr(8, 18.72, 8, 18.25)

# ═══════════════════════════════════════════════════════════════════════════
# LOOP BG  (y 3.3 … 18.2)
# ═══════════════════════════════════════════════════════════════════════════
rect_bg(0.4, 3.3, 15.2, 14.85, "#E8F8F5", label="For each CQ  (i = 1 … n)",
        alpha=0.22, border="#1ABC9C")

# FOR EACH CQ label
box(8, 18.0, 4.2, 0.55, "For each  CQ_i",
    color="#1ABC9C", textcolor="white", border="#117A65",
    bold=True, fontsize=10)

arr(8, 17.72, 8, 17.2)

# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT RESET + HANDOFF INJECTION  (y ≈ 16.9)
# ═══════════════════════════════════════════════════════════════════════════
rect_bg(1.0, 15.55, 14.0, 1.75, "#FEF9E7", label="Context Reset  (fresh LLM context per CQ)",
        alpha=0.35, border="#F39C12")

b2 = FancyBboxPatch((5.2 - 5.8/2, 16.65 - 1.1/2), 5.8, 1.1,
                    boxstyle="round,pad=0.05,rounding_size=0.25",
                    lw=1.2, edgecolor="#E67E22", facecolor="#FEF9E7", zorder=3)
ax.add_patch(b2)
ax.text(5.2, 17.05, "Handoff Artifact  →  System Prompt", ha="center",
        va="center", fontsize=8.5, fontweight="bold", color="#784212", zorder=4)
ax.text(5.2, 16.6, "• Ontology summary (classes / properties)\n• FQ Rules  •  DK Rules  •  completed_cqs",
        ha="center", va="center", fontsize=7.8, color="#555555", zorder=4)

b3 = FancyBboxPatch((11.5 - 4.5/2, 16.65 - 1.1/2), 4.5, 1.1,
                    boxstyle="round,pad=0.05,rounding_size=0.25",
                    lw=1.2, edgecolor="#E67E22", facecolor="#FEF9E7", zorder=3)
ax.add_patch(b3)
ax.text(11.5, 17.05, "User Prompt", ha="center",
        va="center", fontsize=8.5, fontweight="bold", color="#784212", zorder=4)
ax.text(11.5, 16.6, "• User Story  •  CQ_i text\n• key_entities  •  violation hints (retry)",
        ha="center", va="center", fontsize=7.8, color="#555555", zorder=4)

arr(5.2, 16.1, 7.2, 15.45)
arr(11.5, 16.1, 9.3, 15.45)

# ═══════════════════════════════════════════════════════════════════════════
# AXIOM GENERATOR  (y ≈ 15.1)
# ═══════════════════════════════════════════════════════════════════════════
box(8, 15.1, 6.0, 0.75,
    "Axiom Generator  →  delta-Oi",
    color="#D5F5E3", border="#1E8449", bold=True, fontsize=9.5,
    sublabel="generate_with_reset()  /  generate_with_metacognition_reset()")

arr(8, 14.72, 8, 14.2)

# ═══════════════════════════════════════════════════════════════════════════
# PHASE GATE BG  (y 8.1 … 14.15)
# ═══════════════════════════════════════════════════════════════════════════
rect_bg(1.0, 8.1, 14.0, 6.05, "#F4ECF7",
        label="Self-Improving Phase Gate", alpha=0.3, border="#8E44AD")

# Step 1: FQ Validation  (y ≈ 13.7)
box(6.0, 13.7, 5.8, 0.8,
    "Step 1 · FQ Validation",
    color="#E8DAEF", border="#6C3483", bold=True, fontsize=9,
    sublabel="_validate_formal(delta_oi, FQ_rules)")

# Step 2: DK Validation  (y ≈ 12.6)
box(6.0, 12.6, 5.8, 0.8,
    "Step 2 · DK Validation",
    color="#E8DAEF", border="#6C3483", bold=True, fontsize=9,
    sublabel="_validate_domain(delta_oi, DK_rules)")

arr(6.0, 13.3, 6.0, 13.0)

# Step 3: Rule Extraction  (y ≈ 11.2)
rect_bg(1.2, 10.45, 13.6, 1.55, "#EDE7F6", alpha=0.4, border="#7B1FA2")
ax.text(1.5, 11.88, "Step 3 · Rule Extraction", fontsize=8,
        color="#4A235A", fontweight="bold", zorder=2)

box(5.0, 11.1, 5.0, 0.8,
    "Extract new FQ Rules",
    color="#E8DAEF", border="#6C3483", fontsize=8.5,
    sublabel="_extract_fq_rules(delta_oi)")

box(11.0, 11.1, 5.0, 0.8,
    "Extract new DK Rules",
    color="#E8DAEF", border="#6C3483", fontsize=8.5,
    sublabel="_extract_dk_rules(delta_oi)")

arr(6.0, 12.2, 6.0, 11.5)
arr(6.0, 12.2, 11.0, 11.5)

# DK Conflict Resolution  (y ≈ 9.5)
box(8, 9.5, 6.4, 0.75,
    "DK Conflict Resolution",
    color="#D7BDE2", border="#76448A", fontsize=9,
    sublabel="resolve_dk_conflicts(existing, new)  — LLM adjudicates contradictions")

arr(5.0, 10.7, 7.0, 9.88)
arr(11.0, 10.7, 9.0, 9.88)

arr(8, 9.12, 8, 8.75)
box(8, 8.48, 6.0, 0.55, "updated  FQ_{k+1}  and  DK_{k+1}  rule sets",
    color="#D7BDE2", border="#76448A", fontsize=8.5)

# Gate decision diamond  (y ≈ 7.2)
arr(8, 8.2, 8, 7.62)
diamond(8, 7.1, 3.2, 0.95, "Gate Passed?")

# ═══════════════════════════════════════════════════════════════════════════
# PASS path  (right → y 6.1)
# ═══════════════════════════════════════════════════════════════════════════
arr(9.6, 7.1, 12.5, 7.1, label="YES", color="#1E8449")
box(13.2, 7.1, 2.0, 0.65, "Accept\ndelta-Oi", color="#D5F5E3", border="#1E8449",
    fontsize=8.5, bold=True)
arr(13.2, 6.77, 13.2, 6.2)
box(13.2, 5.9, 2.5, 0.55, "Merge into\nOntology TTL",
    color="#D5F5E3", border="#1E8449", fontsize=8)

# ═══════════════════════════════════════════════════════════════════════════
# FAIL path  (left → retry)
# ═══════════════════════════════════════════════════════════════════════════
arr(6.4, 7.1, 3.5, 7.1, label="NO", color="#C0392B")
box(2.8, 7.1, 2.4, 0.65, "Gate\nRejected", color="#FADBD8", border="#C0392B",
    fontsize=8.5, bold=True)

arr(2.8, 6.77, 2.8, 6.2)
diamond(2.8, 5.7, 2.8, 0.85, "retry < max?")

# retry YES
arr(1.4, 5.7, 1.4, 15.1, label="YES\n(+ violations)", color="#E67E22")
ax.annotate("", xy=(5.0, 15.1), xytext=(1.4, 15.1),
            arrowprops=dict(arrowstyle="-|>", color="#E67E22", lw=1.4,
                            shrinkA=0, shrinkB=3), zorder=2)

# retry NO
arr(2.8, 5.27, 2.8, 4.65, label="NO", color="#C0392B")
box(2.8, 4.35, 2.8, 0.55, "Discard delta-Oi\n(rules still updated)",
    color="#FADBD8", border="#C0392B", fontsize=7.8)

# ═══════════════════════════════════════════════════════════════════════════
# UPDATE HANDOFF  (y ≈ 4.9)  – merge both paths
# ═══════════════════════════════════════════════════════════════════════════
arr(13.2, 5.62, 13.2, 4.1)
ax.plot([13.2, 8.5], [4.1, 4.1], color="#444444", lw=1.4, zorder=2)
ax.annotate("", xy=(8.5, 4.1), xytext=(8.5, 3.9),
            arrowprops=dict(arrowstyle="-|>", color="#444444", lw=1.4), zorder=2)

arr(2.8, 4.08, 2.8, 3.95)
ax.plot([2.8, 7.5], [3.95, 3.95], color="#444444", lw=1.4, zorder=2)
ax.annotate("", xy=(7.5, 3.95), xytext=(7.5, 3.9),
            arrowprops=dict(arrowstyle="-|>", color="#444444", lw=1.4), zorder=2)

box(8, 3.7, 8.0, 0.65,
    "Update HandoffArtifact  (iteration k+1)",
    color="#EBF5FB", border="#2471A3", bold=True, fontsize=9,
    sublabel="classes, properties, consistency, FQ_rules, DK_rules, next_cq, completed_cqs")

# ── back-edge to loop ──────────────────────────────────────────────────────
arr(8, 3.37, 8, 3.1)
box(8, 2.85, 3.5, 0.45, "i < n  →  next CQ",
    color="#1ABC9C", textcolor="white", border="#117A65", fontsize=8.5)

ax.annotate("", xy=(0.55, 17.95), xytext=(0.55, 2.85),
            arrowprops=dict(arrowstyle="-|>", color="#117A65", lw=1.5,
                            connectionstyle="arc3,rad=0"), zorder=2)
ax.plot([0.55, 5.85], [17.95, 17.95], color="#117A65", lw=1.5, zorder=2)

ax.text(0.2, 10.4, "next CQ", fontsize=7.5, color="#117A65",
        rotation=90, va="center", fontweight="bold")

# ═══════════════════════════════════════════════════════════════════════════
# OUTPUT  (y ≈ 1.6)
# ═══════════════════════════════════════════════════════════════════════════
arr(8, 2.62, 8, 2.1)
ax.plot([4.25, 11.75], [1.85, 1.85], color="#2471A3", lw=1.2, zorder=2)

boxes_out = [
    (3.0, 1.2, 3.5, "Final Ontology TTL\n(merged)", "#D6EAF8", "#2471A3"),
    (7.0, 1.2, 3.2, "Metrics\n(SC · CCR · ODP · CE)", "#D5F5E3", "#1E8449"),
    (11.0, 1.2, 3.5, "FQ / DK Rules\n+ Usage Stats", "#E8DAEF", "#6C3483"),
]
for bx, by, bw, bl, bc, bb in boxes_out:
    ax.plot([bx, bx], [1.85, by + 0.42], color="#444444", lw=1.2, zorder=2)
    ax.annotate("", xy=(bx, by + 0.42), xytext=(bx, by + 0.42),
                arrowprops=dict(arrowstyle="-|>", color="#444444", lw=1.2), zorder=2)
    b = FancyBboxPatch((bx - bw/2, by - 0.42), bw, 0.84,
                       boxstyle="round,pad=0.05,rounding_size=0.2",
                       lw=1.2, edgecolor=bb, facecolor=bc, zorder=3)
    ax.add_patch(b)
    ax.text(bx, by, bl, ha="center", va="center",
            fontsize=8, fontweight="bold", color="#1A1A2E", zorder=4)

# arrows from horizontal line to each output box
for bx, by, bw, bl, bc, bb in boxes_out:
    ax.annotate("", xy=(bx, by + 0.42), xytext=(bx, 1.85),
                arrowprops=dict(arrowstyle="-|>", color="#444444", lw=1.2,
                                shrinkA=0, shrinkB=2), zorder=2)

# ═══════════════════════════════════════════════════════════════════════════
# LEGEND
# ═══════════════════════════════════════════════════════════════════════════
legend_items = [
    mpatches.Patch(color="#D6EAF8", label="I/O"),
    mpatches.Patch(color="#1ABC9C", label="Loop control"),
    mpatches.Patch(color="#D5F5E3", label="Axiom generation"),
    mpatches.Patch(color="#E8DAEF", label="Phase Gate"),
    mpatches.Patch(color="#FEF9E7", label="Context reset"),
    mpatches.Patch(color="#FADBD8", label="Rejection / retry"),
]
ax.legend(handles=legend_items, loc="lower right",
          fontsize=8, framealpha=0.85, edgecolor="#AAAAAA",
          bbox_to_anchor=(0.99, 0.002))

plt.tight_layout(pad=0.3)
plt.savefig("/home/user/COHA/coha_workflow.png", dpi=150,
            bbox_inches="tight", facecolor=fig.get_facecolor())
print("Saved coha_workflow.png")
