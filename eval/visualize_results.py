"""
EduSHIELD — Results Visualizer
================================
Run AFTER all eval scripts complete.
Reads the JSON metrics files and generates publication-quality graphs.

Run:
    cd ~/Desktop/EduSHIELD
    python3 eval/visualize_results.py

Output:
    eval/results/figures/fig1_boundary_f1_per_class.png
    eval/results/figures/fig2_boundary_confusion_matrix.png
    eval/results/figures/fig3_hallucination_metrics.png
    eval/results/figures/fig4_factscore_baseline_comparison.png
    eval/results/figures/fig5_rag_recall_at_k.png
    eval/results/figures/fig6_rag_per_module.png
    eval/results/figures/fig7_llm_judge_quality.png
    eval/results/figures/fig8_system_overview_dashboard.png
    eval/results/figures/fig9_architecture_comparison.png
"""

import os, sys, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import matplotlib.ticker as mticker

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR  = os.path.join(PROJECT_ROOT, "eval", "results")
FIGS_DIR     = os.path.join(RESULTS_DIR, "figures")
os.makedirs(FIGS_DIR, exist_ok=True)

G1_JSON    = os.path.join(RESULTS_DIR, "guard1_boundary_metrics.json")
G2_JSON    = os.path.join(RESULTS_DIR, "guard2_hallucination_metrics.json")
RAG_JSON   = os.path.join(RESULTS_DIR, "rag_metrics.json")
JUDGE_JSON = os.path.join(RESULTS_DIR, "llm_judge_metrics.json")

SYSTEM_NAME = "EduSHIELD"

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY    = "#1A3557"
BLUE    = "#1F4E79"
LBLUE   = "#2E75B6"
LLBLUE  = "#BDD7EE"
TEAL    = "#007C91"
GREEN   = "#375623"
LGREEN  = "#70AD47"
ORANGE  = "#C55A11"
LORANGE = "#F4B942"
GRAY    = "#595959"
LGRAY   = "#D9D9D9"
RED     = "#C00000"
CRIMSON = "#E04040"
WHITE   = "#FFFFFF"
GOLD    = "#D4A017"

plt.rcParams.update({
    "font.family":       "DejaVu Sans",
    "font.size":         11,
    "axes.titlesize":    13,
    "axes.titleweight":  "bold",
    "axes.labelsize":    11,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "figure.dpi":        150,
    "savefig.dpi":       300,
    "savefig.bbox":      "tight",
    "savefig.facecolor": "white",
    "axes.facecolor":    "#FAFAFA",
    "figure.facecolor":  "white",
})


# ── Utilities ─────────────────────────────────────────────────────────────────
def load(path, name):
    if not os.path.exists(path):
        print(f"[!] {name} not found: {path}")
        print(f"    Run the eval script first, then re-run visualizer.")
        return None
    with open(path) as f:
        return json.load(f)


def bar_labels(ax, bars, fmt="{:.3f}", yoff=0.012, fontsize=9.5, color=BLUE):
    """Place value labels above each bar."""
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + yoff,
                fmt.format(h),
                ha="center", va="bottom",
                fontsize=fontsize, color=color, fontweight="bold",
            )


def target_hline(ax, value, label, color=CRIMSON, x_pos=None):
    ax.axhline(value, color=color, linewidth=1.6, linestyle="--", alpha=0.85)
    xlim = ax.get_xlim()
    x = x_pos if x_pos is not None else xlim[1] * 0.97
    ax.text(x, value + 0.013, f"Target: {value}",
            ha="right", va="bottom", color=color, fontsize=8.5, style="italic")


def meet_badge(ax, met, x=0.98, y=0.93):
    """Small PASS/MISS badge in corner."""
    txt   = "PASS" if met else "MISS"
    color = LGREEN if met else CRIMSON
    ax.text(x, y, txt, transform=ax.transAxes,
            ha="right", va="top", fontsize=9, fontweight="bold",
            color=WHITE, bbox=dict(boxstyle="round,pad=0.3",
                                   facecolor=color, alpha=0.85))


# ─────────────────────────────────────────────────────────────────────────────
# FIG 1 — Boundary: F1 / Precision / Recall per class
# ─────────────────────────────────────────────────────────────────────────────
def fig1_boundary_per_class(g1):
    labels = g1["labels"]
    prec   = [g1["precision_per_class"].get(l, 0) for l in labels]
    rec    = [g1["recall_per_class"].get(l, 0)    for l in labels]
    f1     = [g1["f1_per_class"].get(l, 0)        for l in labels]

    x, w = np.arange(len(labels)), 0.24
    fig, ax = plt.subplots(figsize=(9, 5.2))

    p = [v*100 for v in prec]
    r = [v*100 for v in rec]
    f = [v*100 for v in f1]
    b1 = ax.bar(x - w, p, w, label="Precision", color=NAVY,   alpha=0.90, zorder=3)
    b2 = ax.bar(x,     r, w, label="Recall",    color=LBLUE,  alpha=0.90, zorder=3)
    b3 = ax.bar(x + w, f, w, label="F1-Score",  color=LLBLUE, alpha=0.90,
                edgecolor=LBLUE, linewidth=0.8, zorder=3)

    for brs in [b1, b2, b3]:
        bar_labels(ax, brs, fmt="{:.1f}%", yoff=0.8, fontsize=8.5, color=GRAY)

    # NOTE: Target line removed from Fig 1 per paper revision.
    # BOUNDARY class is inherently hard due to junk KG concept labels.
    # Showing target creates misleading visual — results are discussed
    # in limitations section instead.

    ci = g1.get("confidence_intervals_95", {})
    macro_ci = ci.get("f1_macro", {})
    ci_txt = ""
    if macro_ci:
        ci_txt = f"  95% CI [{macro_ci.get('lower', 0)*100:.1f}%–{macro_ci.get('upper', 0)*100:.1f}%]"

    ax.set_xticks(x)
    ax.set_xticklabels(["IN-DOMAIN", "BOUNDARY", "OUT-OF-DOMAIN"], fontsize=10)
    ax.set_ylim(0, 114)
    ax.set_ylabel("Score (%)")
    ax.set_title(f"Figure 1 — {SYSTEM_NAME} Guard A (Boundary Classifier):\n"
                 "Precision, Recall & F1 per Class  (n=140)")
    ax.legend(loc="upper right", framealpha=0.85)
    ax.grid(axis="y", alpha=0.25, zorder=0)

    ax.text(0.02, 0.97,
            f"Macro F1 = {g1['f1_macro']*100:.1f}%{ci_txt}   "
            f"Accuracy = {g1['accuracy']*100:.1f}%   n = {g1['n_questions']}",
            transform=ax.transAxes, fontsize=8.5, color=GRAY,
            bbox=dict(boxstyle="round,pad=0.3", facecolor=LGRAY, alpha=0.55))

    # Badge removed — no target to compare against in this figure
    path = os.path.join(FIGS_DIR, "fig1_boundary_f1_per_class.png")
    plt.savefig(path); plt.close()
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# FIG 2 — Boundary: Confusion Matrix
# ─────────────────────────────────────────────────────────────────────────────
def fig2_confusion_matrix(g1):
    cm     = np.array(g1["confusion_matrix"])
    labels = ["IN-DOMAIN", "BOUNDARY", "OOD"]
    n      = cm.sum()

    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues", vmin=0)
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=9)

    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            pct = f"\n({cm[i,j]/n*100:.1f}%)"
            ax.text(j, i, f"{cm[i, j]}{pct}", ha="center", va="center",
                    color=WHITE if cm[i, j] > thresh else BLUE,
                    fontsize=11, fontweight="bold")

    ax.set_xticks(range(len(labels))); ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Predicted Label", fontweight="bold")
    ax.set_ylabel("True Label",      fontweight="bold")
    ax.set_title(f"Figure 2 — {SYSTEM_NAME} Guard A (Boundary):\nConfusion Matrix  (n={n})")

    path = os.path.join(FIGS_DIR, "fig2_boundary_confusion_matrix.png")
    plt.savefig(path); plt.close()
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# FIG 3 — Hallucination: Core Metrics vs Targets
# ─────────────────────────────────────────────────────────────────────────────
def fig3_hallucination_metrics(g2):
    # Robust key access — guard2 JSON uses n_correct_tested / n_wrong_tested
    n_total = g2.get(
        "n_test_cases",
        g2.get("n_correct_tested", 0) + g2.get("n_wrong_tested", 0)
    )
    # with_stored_negation may not be saved in v3 JSON
    n_stored = g2.get(
        "with_stored_negation",
        g2.get("verdict_breakdown", {}).get("wrong_responses", {}).get("total", "—")
    )
    n_sampled = g2.get("n_facts_sampled", g2.get("n_correct_tested", "—"))

    metrics = ["Catch Rate", "FActScore", "1 − False\nContradiction Rate"]
    values  = [
        g2["catch_rate"] * 100,
        g2["factscore"] * 100,
        (1.0 - g2["false_contradiction_rate"]) * 100,
    ]
    targets = [90, 85, 95]
    colors  = [BLUE, TEAL, LBLUE]
    labels  = ["Catch Rate", "FActScore", "False-Pos (inv.)"]

    x, w = np.arange(len(metrics)), 0.33
    fig, ax = plt.subplots(figsize=(9, 5.2))

    bars_sys = ax.bar(x - w/2, values,  w, color=colors,  alpha=0.92, zorder=3,
                      label=SYSTEM_NAME)
    bars_tgt = ax.bar(x + w/2, targets, w, color=LGRAY,   alpha=0.75, zorder=3,
                      label="Target", edgecolor=GRAY, linewidth=0.8)

    bar_labels(ax, bars_sys, fmt="{:.1f}%", yoff=0.8, fontsize=10, color=BLUE)

    for xi, tgt in zip(x + w/2, targets):
        ax.text(xi, tgt + 0.8, f"{tgt}%", ha="center", va="bottom",
                fontsize=9, color=GRAY)

    # Colour-coded met/miss markers
    for xi, val, tgt in zip(x - w/2, values, targets):
        met = (val >= tgt)  # both now in %
        clr = LGREEN if met else CRIMSON
        ax.text(xi, 2, "✓" if met else "✗", ha="center", va="bottom",
                fontsize=14, color=clr)

    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=10)
    ax.set_ylim(0, 117)
    ax.set_ylabel("Score % (higher = better)")
    ax.set_title(f"Figure 3 — {SYSTEM_NAME} Guard B (Hallucination):\nFActScore, Catch Rate & False Contradiction Rate")
    ax.legend(loc="upper right", framealpha=0.85)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))
    ax.grid(axis="y", alpha=0.25, zorder=0)

    annotation = (
        f"n = {n_total} test cases  |  "
        f"Correct responses: {g2.get('n_correct_tested', '—')}  |  "
        f"Wrong injections: {g2.get('n_wrong_tested', '—')}"
    )
    ax.text(0.02, 0.97, annotation,
            transform=ax.transAxes, fontsize=8.5, color=GRAY,
            bbox=dict(boxstyle="round,pad=0.3", facecolor=LGRAY, alpha=0.55))

    path = os.path.join(FIGS_DIR, "fig3_hallucination_metrics.png")
    plt.savefig(path); plt.close()
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# FIG 4 — FActScore: EduSHIELD vs Literature Baselines
# ─────────────────────────────────────────────────────────────────────────────
def fig4_factscore_comparison(g2):
    systems = [
        "ChatGPT\n(Min et al. 2023)",
        "GPT-4\n(Min et al. 2023)",
        f"{SYSTEM_NAME}\n(This Work)",
    ]
    scores  = [
        g2["baselines"]["ChatGPT_FActScore_Min2023"] * 100,
        g2["baselines"]["GPT4_FActScore_Min2023"]    * 100,
        g2["factscore"]                              * 100,
    ]
    colors = [LGRAY, LGRAY, BLUE]
    edges  = [GRAY,  GRAY,  NAVY]

    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    bars = ax.bar(systems, scores, color=colors, edgecolor=edges,
                  linewidth=1.6, width=0.5, zorder=3)

    for bar, score, clr in zip(bars, scores, [GRAY, GRAY, BLUE]):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.8,
                f"{score:.1f}%", ha="center", va="bottom",
                fontsize=13, fontweight="bold", color=clr)

    target_hline(ax, 85, "Target: 85%", x_pos=2.55)

    ax.set_ylim(0, 110)
    ax.set_ylabel("FActScore (%)")
    ax.set_title(f"Figure 4 — FActScore Comparison:\n{SYSTEM_NAME} vs Literature Baselines")
    ax.grid(axis="y", alpha=0.25, zorder=0)

    # Improvement arrow from GPT-4 → EduSHIELD
    improvement = (g2["factscore"] - g2["baselines"]["GPT4_FActScore_Min2023"]) * 100
    ax.annotate("", xy=(2, scores[2]), xytext=(1, scores[1]),
                arrowprops=dict(arrowstyle="->", color=LGREEN, lw=2.2))
    ax.text(1.5, (scores[2] + scores[1]) / 2 + 2,
            f"+{improvement:.1f}pp", color=LGREEN, fontsize=11, fontweight="bold",
            ha="center")

    met = g2["factscore"] >= 0.85
    meet_badge(ax, met)

    # Domain caveat footnote — different datasets, same metric methodology
    ax.text(0.02, 0.02,
            "Note: Baselines evaluated on general-domain biographical facts (Min et al. 2023).\n"
            "EduSHIELD evaluated on course-grounded educational content (same metric, different domain).",
            transform=ax.transAxes, fontsize=7.5, color=GRAY, style="italic",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=LGRAY, alpha=0.45))

    path = os.path.join(FIGS_DIR, "fig4_factscore_baseline_comparison.png")
    plt.savefig(path); plt.close()
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# FIG 5 — RAG: Recall@1/3/5 + MRR
# ─────────────────────────────────────────────────────────────────────────────
def fig5_rag_recall(rag):
    ci = rag.get("confidence_intervals_95", {})

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5.2))

    # Left — Recall@k
    ks      = ["Recall@1", "Recall@3", "Recall@5"]
    recalls = [rag["recall_at_1"]*100, rag["recall_at_3"]*100, rag["recall_at_5"]*100]
    colors  = [LLBLUE, LBLUE, BLUE]

    bars = ax1.bar(ks, recalls, color=colors, width=0.45, zorder=3)
    bar_labels(ax1, bars, fmt="{:.1f}%", yoff=0.8, fontsize=11, color=BLUE)

    # Error bars for Recall@5
    r5_ci = ci.get("recall_at_5", {})
    if r5_ci:
        lo = r5_ci.get("lower", recalls[2]/100)*100
        hi = r5_ci.get("upper", recalls[2]/100)*100
        ax1.errorbar(2, recalls[2], yerr=[[recalls[2]-lo], [hi-recalls[2]]],
                     fmt="none", ecolor=NAVY, elinewidth=2, capsize=5)

    ax1.axhline(80, color=CRIMSON, linewidth=1.6, linestyle="--", alpha=0.85)
    ax1.text(2.4, 81, "Target\n@5: 80%", color=CRIMSON, fontsize=8.5,
             style="italic", ha="right")
    ax1.set_ylim(0, 110)
    ax1.set_ylabel("Recall (%)")
    ax1.set_title("RAG Recall@k")
    ax1.grid(axis="y", alpha=0.25, zorder=0)

    met_r5 = recalls[2] >= 80
    meet_badge(ax1, met_r5)

    # Right — MRR standalone (LPITutor comparison removed — different domain/dataset)
    mrr        = rag["mrr"]
    target_mrr = rag["targets"]["mrr"]
    mrr_ci     = ci.get("mrr", {})

    mrr_pct = mrr * 100
    target_mrr_pct = target_mrr * 100
    bars2 = ax2.bar([f"{SYSTEM_NAME}\nRAG (This Work)"], [mrr_pct],
                    color=[LBLUE], width=0.35, zorder=3, edgecolor=[BLUE])
    ax2.text(bars2[0].get_x() + bars2[0].get_width() / 2,
             mrr_pct + 1, f"{mrr_pct:.1f}%",
             ha="center", va="bottom", fontsize=13, fontweight="bold", color=BLUE)

    # Error bar on EduSHIELD MRR
    if mrr_ci:
        lo_m = mrr_ci.get("lower", mrr)*100
        hi_m = mrr_ci.get("upper", mrr)*100
        ax2.errorbar(0, mrr_pct, yerr=[[mrr_pct-lo_m], [hi_m-mrr_pct]],
                     fmt="none", ecolor=NAVY, elinewidth=2, capsize=5)

    ax2.axhline(target_mrr_pct, color=CRIMSON, linewidth=1.6, linestyle="--", alpha=0.85)
    ax2.text(0.45, target_mrr_pct + 1.5, f"Target: {target_mrr_pct:.0f}%",
             color=CRIMSON, fontsize=8.5, style="italic", ha="right")
    ax2.set_ylim(0, 110)
    ax2.set_ylabel("MRR (%)")
    ax2.set_title("Mean Reciprocal Rank (MRR)")
    ax2.grid(axis="y", alpha=0.25, zorder=0)
    ax2.set_xlim(-0.5, 0.5)

    # Domain note — LPITutor removed as direct comparison is not valid
    ax2.text(0.5, 0.04,
             "Cross-system comparison omitted:\ndifferent domains & datasets",
             transform=ax2.transAxes, fontsize=7.5, color=GRAY, style="italic",
             ha="center", bbox=dict(boxstyle="round,pad=0.25", facecolor=LGRAY, alpha=0.4))

    met_mrr = mrr >= target_mrr
    meet_badge(ax2, met_mrr)

    fig.suptitle(f"Figure 5 — {SYSTEM_NAME} RAG System: Retrieval Performance",
                 fontweight="bold", fontsize=13, y=1.01)
    plt.tight_layout()
    path = os.path.join(FIGS_DIR, "fig5_rag_recall_at_k.png")
    plt.savefig(path); plt.close()
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# FIG 6 — RAG: Per-Module Recall@5 Horizontal Bars
# ─────────────────────────────────────────────────────────────────────────────
def fig6_rag_per_module(rag):
    per_mod = rag["per_module"]
    modules = list(per_mod.keys())
    recalls = [per_mod[m]["recall"] for m in modules]
    totals  = [per_mod[m]["total"]  for m in modules]

    # Shorten module names
    short = []
    for m in modules:
        if "CSE1300" in m:
            short.append(m.replace("CSE1300 - ", "CSE1300/"))
        elif "Module" in m:
            short.append(m.replace("Module ", "CSE1321 M"))
        else:
            short.append(m)

    colors = [
        BLUE    if r >= 0.80 else
        LORANGE if r >= 0.60 else
        CRIMSON
        for r in recalls
    ]

    fig, ax = plt.subplots(figsize=(10, max(4.5, len(modules) * 0.55)))
    bars = ax.barh(short, recalls, color=colors, height=0.55, zorder=3)

    for bar, val, tot in zip(bars, recalls, totals):
        ax.text(val + 0.015, bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}  (n={tot})",
                va="center", fontsize=9, color=GRAY)

    ax.axvline(0.80, color=CRIMSON, linewidth=1.6, linestyle="--", alpha=0.85)
    ax.text(0.81, len(modules) - 0.6, "Target: 0.80",
            color=CRIMSON, fontsize=8.5, style="italic")

    ax.set_xlim(0, 1.20)
    ax.set_xlabel("Recall@5")
    ax.set_title(f"Figure 6 — {SYSTEM_NAME} RAG Recall@5 per Module / Course")
    ax.grid(axis="x", alpha=0.25, zorder=0)

    patches = [
        mpatches.Patch(color=BLUE,    label="≥ 0.80  (meets target)"),
        mpatches.Patch(color=LORANGE, label="0.60–0.79  (below target)"),
        mpatches.Patch(color=CRIMSON, label="< 0.60  (poor)"),
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=9, framealpha=0.85)

    plt.tight_layout()
    path = os.path.join(FIGS_DIR, "fig6_rag_per_module.png")
    plt.savefig(path); plt.close()
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# FIG 7 — NEW: LLM-as-Judge Response Quality
# ─────────────────────────────────────────────────────────────────────────────
def fig7_llm_judge(judge):
    fig = plt.figure(figsize=(13, 5.5))
    gs  = GridSpec(1, 3, figure=fig, wspace=0.40)

    # ── Panel A: Criterion bar chart ──────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    criteria = ["Factual\nAccuracy", "Pedagogical\nQuality", "Course\nGrounding"]
    scores   = [
        judge["avg_factual_accuracy"],
        judge["avg_pedagogical_quality"],
        judge["avg_course_grounding"],
    ]
    targets_j = [4.5, 4.0, 4.0]
    colors_j  = [BLUE, LBLUE, TEAL]

    bars = ax1.bar(criteria, scores, color=colors_j, width=0.45, zorder=3, alpha=0.92)
    bar_labels(ax1, bars, fmt="{:.2f}", yoff=0.04, fontsize=10, color=BLUE)

    for xi, tgt in enumerate(targets_j):
        ax1.axhline(tgt, color=CRIMSON, linewidth=1, linestyle=":", alpha=0.7)

    ax1.set_ylim(0, 5.5)
    ax1.set_ylabel("Mean Score (out of 5)")
    ax1.set_title(f"LLM Judge Scores\nby Criterion  (n={judge['n_valid']})")
    ax1.grid(axis="y", alpha=0.25, zorder=0)

    composite = judge["avg_composite_score"]
    ax1.text(0.5, 0.96, f"Composite: {composite:.3f}/5",
             transform=ax1.transAxes, ha="center", va="top",
             fontsize=10, fontweight="bold", color=BLUE,
             bbox=dict(boxstyle="round,pad=0.3", facecolor=LLBLUE, alpha=0.6))

    # ── Panel B: Response quality distribution ────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    dist = judge["distribution"]
    cats = ["Excellent\n(≥4)", "Good\n(3–4)", "Poor\n(<3)"]
    cnts = [dist["excellent_gte_4"], dist["good_3_to_4"], dist["poor_lt_3"]]
    pcts = [100 * c / judge["n_valid"] for c in cnts]
    cols = [LGREEN, LORANGE, CRIMSON]

    bars2 = ax2.bar(cats, pcts, color=cols, width=0.45, zorder=3, alpha=0.92)
    for bar, pct, cnt in zip(bars2, pcts, cnts):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.7,
                 f"{pct:.1f}%\n(n={cnt})", ha="center", va="bottom",
                 fontsize=9.5, fontweight="bold", color=GRAY)

    poor_rate    = dist["poor_lt_3"] / judge["n_valid"]
    target_poor  = judge["targets"].get("poor_rate", 0.10)
    # Guideline line kept but labelled as "guideline" not "target"
    ax2.axhline(target_poor * 100, color=GRAY, linewidth=1.2,
                linestyle=":", alpha=0.6)
    ax2.text(2.4, target_poor * 100 + 0.7,
             f"Guideline:\n≤{target_poor*100:.0f}% poor",
             ha="right", color=GRAY, fontsize=8, style="italic")

    ax2.set_ylim(0, 100)
    ax2.set_ylabel("Percentage of Responses (%)")
    ax2.set_title("Response Quality\nDistribution")
    ax2.grid(axis="y", alpha=0.25, zorder=0)

    met_poor = poor_rate <= target_poor
    meet_badge(ax2, met_poor)

    # ── Panel C: Per-question-type scores ─────────────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    per_type = judge.get("per_type", {})
    types    = list(per_type.keys())
    vals_t   = [per_type[t] for t in types]
    yt       = np.arange(len(types))
    cols_t   = [BLUE if v >= 4.0 else LORANGE if v >= 3.5 else CRIMSON for v in vals_t]

    bars3 = ax3.barh(types, vals_t, color=cols_t, height=0.5, zorder=3, alpha=0.92)
    for bar, val in zip(bars3, vals_t):
        ax3.text(val + 0.04, bar.get_y() + bar.get_height()/2,
                 f"{val:.2f}", va="center", fontsize=9.5,
                 fontweight="bold", color=GRAY)

    ax3.axvline(3.5, color=CRIMSON, linewidth=1.5, linestyle="--", alpha=0.85)
    ax3.set_xlim(0, 5.5)
    ax3.set_xlabel("Mean Composite Score")
    ax3.set_title("Score by\nQuestion Type")
    ax3.grid(axis="x", alpha=0.25, zorder=0)

    fig.suptitle(
        f"Figure 7 — {SYSTEM_NAME} LLM-as-Judge Response Quality Evaluation",
        fontweight="bold", fontsize=13, y=1.02,
    )
    path = os.path.join(FIGS_DIR, "fig7_llm_judge_quality.png")
    plt.savefig(path); plt.close()
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# FIG 8 — System Overview Dashboard (all metrics)
# ─────────────────────────────────────────────────────────────────────────────
def fig8_dashboard(g1, g2, rag, judge):
    fig = plt.figure(figsize=(15, 10))
    fig.suptitle(f"{SYSTEM_NAME} — Evaluation Results Dashboard",
                 fontsize=17, fontweight="bold", y=0.99, color=NAVY)
    gs = GridSpec(2, 3, figure=fig, hspace=0.52, wspace=0.38)

    # ── P1: Guard A F1 per class ──────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    labels_g1 = ["IN", "BOUND", "OOD"]
    f1_vals   = [g1["f1_per_class"].get(l, 0)*100 for l in g1["labels"]]
    bars1 = ax1.bar(labels_g1, f1_vals,
                    color=[NAVY, LBLUE, LLBLUE], width=0.5, zorder=3)
    bar_labels(ax1, bars1, fmt="{:.1f}%", yoff=0.8, fontsize=9, color=GRAY)
    # Target line removed from dashboard Guard A panel (see limitations)
    ax1.set_ylim(0, 117)
    ax1.set_ylabel("F1 (%)")
    ax1.grid(axis="y", alpha=0.25)
    ax1.set_title(f"Guard A (Boundary)\nMacro F1 = {g1['f1_macro']*100:.1f}%")
    # No badge — BOUNDARY class performance discussed in limitations section

    # ── P2: Guard B hallucination ─────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    g2_names = ["Catch\nRate", "FActScore", "1−FPR"]
    g2_vals  = [g2["catch_rate"]*100, g2["factscore"]*100, (1-g2["false_contradiction_rate"])*100]
    g2_tgts  = [90, 85, 95]
    x2 = np.arange(len(g2_names))
    ax2.bar(x2 - 0.18, g2_vals,  0.32, color=BLUE,  alpha=0.92, zorder=3, label=SYSTEM_NAME)
    ax2.bar(x2 + 0.18, g2_tgts,  0.32, color=LGRAY, alpha=0.80, zorder=3, label="Target",
            edgecolor=GRAY, lw=0.8)
    for xi, val in zip(x2 - 0.18, g2_vals):
        ax2.text(xi, val + 0.8, f"{val:.1f}%", ha="center", va="bottom",
                 fontsize=8.5, color=BLUE, fontweight="bold")
    ax2.set_xticks(x2); ax2.set_xticklabels(g2_names, fontsize=9)
    ax2.set_ylim(0, 117); ax2.set_ylabel("Score (%)"); ax2.grid(axis="y", alpha=0.25)
    ax2.legend(fontsize=8, loc="lower right", framealpha=0.8)
    ax2.set_title(f"Guard B (Hallucination)\nFActScore = {g2['factscore']:.3f}")

    # ── P3: RAG Recall@k ──────────────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    ks_labels = ["@1", "@3", "@5"]
    ks_vals   = [rag["recall_at_1"]*100, rag["recall_at_3"]*100, rag["recall_at_5"]*100]
    bars3 = ax3.bar(ks_labels, ks_vals,
                    color=[LLBLUE, LBLUE, BLUE], width=0.42, zorder=3)
    bar_labels(ax3, bars3, fmt="{:.1f}%", yoff=0.8, fontsize=9, color=GRAY)
    ax3.axhline(80, color=CRIMSON, lw=1.3, ls="--", alpha=0.8)
    ax3.set_ylim(0, 117); ax3.set_ylabel("Recall (%)"); ax3.grid(axis="y", alpha=0.25)
    ax3.set_title(f"RAG Retrieval Recall@k\nMRR = {rag['mrr']*100:.1f}%")
    met3 = ks_vals[2] >= 80
    meet_badge(ax3, met3)

    # ── P4: FActScore baseline comparison ─────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 0])
    sys4  = ["ChatGPT", "GPT-4", SYSTEM_NAME]
    val4  = [58, 80, g2["factscore"]*100]
    col4  = [LGRAY, LGRAY, BLUE]
    bars4 = ax4.bar(sys4, val4, color=col4, width=0.5, zorder=3,
                    edgecolor=[GRAY, GRAY, BLUE])
    for bar, val, clr in zip(bars4, val4, [GRAY, GRAY, BLUE]):
        ax4.text(bar.get_x() + bar.get_width()/2, val + 0.8,
                 f"{val:.1f}%", ha="center", va="bottom",
                 fontsize=9, fontweight="bold", color=clr)
    ax4.axhline(85, color=CRIMSON, lw=1.3, ls="--", alpha=0.8)
    ax4.set_ylim(0, 110); ax4.set_ylabel("FActScore (%)"); ax4.grid(axis="y", alpha=0.25)
    ax4.set_title("FActScore vs Baselines\n(Min et al. 2023)")

    # ── P5: LLM Judge scores ──────────────────────────────────────────────────
    ax5 = fig.add_subplot(gs[1, 1])
    if judge:
        j_criteria = ["Factual\nAccuracy", "Pedagogical\nQuality", "Course\nGrounding",
                      "Composite"]
        j_scores   = [
            judge["avg_factual_accuracy"],
            judge["avg_pedagogical_quality"],
            judge["avg_course_grounding"],
            judge["avg_composite_score"],
        ]
        bars5 = ax5.bar(j_criteria, j_scores,
                        color=[BLUE, LBLUE, TEAL, NAVY], width=0.5, zorder=3, alpha=0.92)
        for bar, val in zip(bars5, j_scores):
            ax5.text(bar.get_x() + bar.get_width()/2, val + 0.06,
                     f"{val:.2f}", ha="center", va="bottom",
                     fontsize=8.5, fontweight="bold", color=GRAY)
        ax5.axhline(3.5, color=CRIMSON, lw=1.3, ls="--", alpha=0.8)
        ax5.set_ylim(0, 5.8); ax5.set_ylabel("Score (out of 5)")
        ax5.set_title(f"LLM-as-Judge Quality\nn = {judge['n_valid']} responses")
        ax5.grid(axis="y", alpha=0.25)
        met5 = judge["avg_composite_score"] >= judge["targets"].get("composite_score", 3.5)
        meet_badge(ax5, met5)
    else:
        ax5.axis("off")
        ax5.text(0.5, 0.5, "LLM Judge data\nnot available",
                 ha="center", va="center", transform=ax5.transAxes, color=GRAY)

    # ── P6: Summary table ─────────────────────────────────────────────────────
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis("off")

    def fmt_met(val, tgt, op=">="):
        s = f"{val:.4f}"
        return s + (" ✓" if (val >= tgt if op == ">=" else val <= tgt) else " ✗")

    rows = [
        ["Guard A Accuracy",    f"{g1['accuracy']:.4f}"],
        ["Guard A Macro-F1",    fmt_met(g1["f1_macro"], 0.87)],
        ["Guard B FActScore",   fmt_met(g2["factscore"], 0.85)],
        ["Guard B Catch Rate",  fmt_met(g2["catch_rate"], 0.90)],
        ["Guard B False-Pos",   fmt_met(g2["false_contradiction_rate"], 0.05, "<=")],
        ["RAG Recall@5",        fmt_met(rag["recall_at_5"], 0.80)],
        ["RAG MRR",             fmt_met(rag["mrr"], 0.75)],
    ]
    if judge:
        rows.append(["LLM Judge Score",
                     fmt_met(judge["avg_composite_score"], 3.5)])

    rows += [
        ["Test Questions",   str(g1.get("n_questions", 140))],
        ["RAG Gold Pairs",   str(rag.get("n_pairs", 52))],
        ["Halluc. Cases",    str(g2.get("n_correct_tested", 0) + g2.get("n_wrong_tested", 0))],
    ]

    tbl = ax6.table(cellText=rows,
                    colLabels=["Metric", "Value"],
                    cellLoc="left", loc="center",
                    bbox=[0, 0, 1, 1])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.5)
    for (row, col), cell in tbl.get_celld().items():
        if row == 0:
            cell.set_facecolor(NAVY)
            cell.set_text_props(color=WHITE, fontweight="bold")
        elif row % 2 == 0:
            cell.set_facecolor(LLBLUE)
        cell.set_edgecolor(LGRAY)
        txt = cell.get_text().get_text()
        if "✓" in txt:
            cell.set_text_props(color=GREEN, fontweight="bold")
        elif "✗" in txt:
            cell.set_text_props(color=CRIMSON)
    ax6.set_title("Summary Scorecard", pad=12, fontweight="bold")

    path = os.path.join(FIGS_DIR, "fig8_system_overview_dashboard.png")
    plt.savefig(path); plt.close()
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# FIG 9 — Architectural Comparison Table (journal-style)
# ─────────────────────────────────────────────────────────────────────────────
def fig9_architecture_comparison():
    fig, ax = plt.subplots(figsize=(14, 5.2))
    ax.axis("off")

    systems = [
        "AutoTutor\n(Graesser 2001)",
        "KG-CQ\n(Zhong 2025)",
        "Wang et al.\n(WWW 2025)",
        "LPITutor\n(P13)",
        "EON Brainy\n2.0",
        f"{SYSTEM_NAME}\n(This Work)",
    ]

    features = [
        "Socratic\nDialogue",
        "KG\nGrounding",
        "Hallucination\nGuard",
        "Boundary\nGuard",
        "Student\nProfile",
    ]

    data = [
        ["✓", "✗", "✗", "✗", "✗"],
        ["✗", "✓", "✗", "✗", "✗"],
        ["✓", "✓", "✗", "✗", "✗"],
        ["✗", "✗", "Partial", "✗", "✗"],
        ["✓", "✗", "Prompt", "Prompt", "✓"],
        ["✓", "✓", "✓", "✓", "✓"],
    ]

    col_labels = ["System"] + features
    tbl_data   = [[sys] + row for sys, row in zip(systems, data)]

    tbl = ax.table(cellText=tbl_data,
                   colLabels=col_labels,
                   cellLoc="center", loc="center",
                   bbox=[0, 0, 1, 1])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9.5)

    n_sys = len(systems)
    for (row, col), cell in tbl.get_celld().items():
        txt = cell.get_text().get_text()
        if row == 0:
            cell.set_facecolor(NAVY)
            cell.set_text_props(color=WHITE, fontweight="bold", fontsize=9.5)
        elif row == n_sys:  # EduSHIELD row (last)
            cell.set_facecolor("#D0EED0")
            cell.set_text_props(fontweight="bold")
        elif row % 2 == 0:
            cell.set_facecolor(LGRAY)

        if txt == "✓":
            cell.set_text_props(color=GREEN, fontweight="bold")
        elif txt == "✗":
            cell.set_text_props(color=CRIMSON)
        elif txt in ("Partial", "Prompt"):
            cell.set_text_props(color=ORANGE)
        cell.set_edgecolor("#C0C0C0")

    ax.set_title(
        f"Figure 9 — Architectural Feature Comparison: {SYSTEM_NAME} vs Existing ITS Systems",
        fontsize=12, fontweight="bold", pad=16,
    )

    path = os.path.join(FIGS_DIR, "fig9_architecture_comparison.png")
    plt.savefig(path); plt.close()
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 62)
    print(f"  {SYSTEM_NAME} — Results Visualizer")
    print("=" * 62)

    g1    = load(G1_JSON,    "Guard A (Boundary) metrics")
    g2    = load(G2_JSON,    "Guard B (Hallucination) metrics")
    rag   = load(RAG_JSON,   "RAG metrics")
    judge = load(JUDGE_JSON, "LLM Judge metrics")   # optional

    core_missing = [name for data, name in [(g1,"Guard A"),(g2,"Guard B"),(rag,"RAG")]
                    if data is None]
    if core_missing:
        print(f"\n[!] Missing core results for: {', '.join(core_missing)}")
        print("    Run the missing eval scripts first.")
        if g1  is None: print("    → python3 eval/eval_guard1_boundary.py")
        if g2  is None: print("    → python3 eval/eval_guard2_hallucination.py")
        if rag is None: print("    → python3 eval/eval_rag.py")
        print("\n  Generating architecture comparison (no results needed)...")
        fig9_architecture_comparison()
        return

    if judge is None:
        print("[i] LLM Judge metrics not found — fig7 will be skipped / dashboard partial.")

    print(f"\n  Output dir: {FIGS_DIR}\n")

    fig1_boundary_per_class(g1)
    fig2_confusion_matrix(g1)
    fig3_hallucination_metrics(g2)
    fig4_factscore_comparison(g2)
    fig5_rag_recall(rag)
    fig6_rag_per_module(rag)
    if judge:
        fig7_llm_judge(judge)
    fig8_dashboard(g1, g2, rag, judge)
    fig9_architecture_comparison()

    n_figs = 9 if judge else 8
    print(f"\n{'='*62}")
    print(f"  {n_figs} figures saved to:")
    print(f"  {FIGS_DIR}")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
