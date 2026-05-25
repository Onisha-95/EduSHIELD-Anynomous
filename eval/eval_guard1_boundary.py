"""
EduSHIELD — Guard 1: Boundary Classification Evaluation (v3 — final)

FIXES:
  BUG 6: Fallback domain config had only 3 boundary_terms → BOUNDARY F1=0%.
         Now reads from COURSE_REGISTRY via _build_domain_from_registry(),
         which has the full 37 boundary_terms for CSE1321. No hardcoding.
  BUG 7: score column was saving 0.0 for all items (path not logged).
         Now saves actual score and classification_path per row.
"""
import sys, os, csv, json, re
import numpy as np
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))

from config import (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
                    NEO4J_DATABASE, CHROMA_PATH)
from core.neo4j_client    import Neo4jKGClient
from core.rag_system      import RAGSystem
from core.guard2_boundary import KnowledgeBoundaryAgent
from core.session_manager import init_session

TEST_CSV    = os.path.join(PROJECT_ROOT, "guard2_test_set.csv")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "eval", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
OUT_CSV  = os.path.join(RESULTS_DIR, "guard1_boundary_results.csv")
OUT_JSON = os.path.join(RESULTS_DIR, "guard1_boundary_metrics.json")
OUT_TXT  = os.path.join(RESULTS_DIR, "guard1_boundary_report.txt")

N_BOOTSTRAP = 1000
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)


def bootstrap_ci(y_true, y_pred, metric_fn, n=N_BOOTSTRAP, ci=95):
    scores, indices = [], np.arange(len(y_true))
    for _ in range(n):
        idx = np.random.choice(indices, size=len(indices), replace=True)
        yt  = [y_true[i] for i in idx]
        yp  = [y_pred[i]  for i in idx]
        try:
            scores.append(metric_fn(yt, yp))
        except Exception:
            pass
    if not scores:
        return 0.0, 0.0
    return (round(float(np.percentile(scores, (100-ci)/2)),  4),
            round(float(np.percentile(scores, 100-(100-ci)/2)), 4))


def _build_domain_from_registry(course_id: str) -> dict:
    """
    FIX (BUG 6): Auto-build domain config from COURSE_REGISTRY.
    boundary_terms comes from registry entry (now populated in updated config.py).
    in_domain_keywords = module-name words + in_domain_extras.
    No hardcoded lists anywhere.
    """
    from config import COURSE_REGISTRY

    course  = COURSE_REGISTRY.get(course_id, {})
    prereqs = course.get("prerequisites", [])

    module_words = set()
    for m in course.get("modules", []):
        clean = re.sub(r'^M\d+\s*[-—]\s*', '', m)
        for w in clean.lower().split():
            if len(w) > 3 and w not in {"with", "and", "for", "the", "review"}:
                module_words.add(w)

    extras = set(course.get("in_domain_extras", []))
    in_domain_keywords = list(set([course_id.lower()]) | module_words | extras)
    boundary_terms     = course.get("boundary_terms", [])
    excluded_terms     = [
        cid.lower() for cid in COURSE_REGISTRY
        if cid != course_id and cid not in prereqs
    ]

    print(f"   [fallback] Built domain from COURSE_REGISTRY for {course_id}:")
    print(f"              {len(in_domain_keywords)} in-domain kw, "
          f"{len(boundary_terms)} boundary terms")
    return {
        "in_domain_keywords":   in_domain_keywords,
        "boundary_terms":       boundary_terms,
        "excluded_terms":       excluded_terms,
        "prerequisite_courses": prereqs,
    }


def run():
    print("\n" + "="*60)
    print("  Guard 1 — Boundary Classification (v3 — final)")
    print("="*60)

    if not os.path.exists(TEST_CSV):
        print(f"[x] Not found: {TEST_CSV}")
        return

    questions = list(csv.DictReader(open(TEST_CSV, encoding="utf-8")))
    print(f"\n   Loaded {len(questions)} questions")
    for lbl in ["IN_DOMAIN", "BOUNDARY", "OUT_OF_DOMAIN"]:
        n = sum(1 for q in questions if q["label"] == lbl)
        print(f"     {lbl}: {n}")

    print("\n   Connecting to Neo4j...")
    kg  = Neo4jKGClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)
    rag = RAGSystem(kg, CHROMA_PATH)
    s   = kg.get_stats()
    print(f"   KG: {s['concepts']} concepts, {s['facts']} facts")

    # FIX (BUG 6): use _build_domain_from_registry instead of 3-term hardcoded fallback
    domain = kg.get_domain_config("CSE1321") or kg.get_domain_config() or \
             _build_domain_from_registry("CSE1321")
    guard  = KnowledgeBoundaryAgent(kg, rag, domain)

    print(f"\n   Running {len(questions)} questions...\n")
    rows, y_true, y_pred = [], [], []

    for i, q in enumerate(questions):
        if i % 25 == 0:
            print(f"   {i}/{len(questions)}...")
        session = init_session(f"eval_{i}")
        try:
            r         = guard.classify(q["question"], session)
            predicted = r["classification"]
            score     = r.get("domain_match_score", 0.0)
            concept   = r.get("matched_concept", "") or ""
            reasoning = r.get("reasoning", "")
            # FIX (BUG 7): determine classification path from reasoning string
            if score > 0.55:
                path = "semantic"
            elif "in_kw=True" in reasoning:
                path = "in_keyword"
            elif "boundary_kw=True" in reasoning:
                path = "boundary_keyword"
            else:
                path = "score_only"
        except Exception as e:
            predicted, score, concept, path = "ERROR", 0.0, "", "error"

        y_true.append(q["label"])
        y_pred.append(predicted)
        rows.append({
            "id": i+1, "question": q["question"],
            "true_label": q["label"], "predicted": predicted,
            "correct": predicted == q["label"],
            "score": round(score, 4), "concept": concept,
            "classification_path": path,     # FIX (BUG 7)
            "source": q.get("source", ""),
        })

    from sklearn.metrics import (classification_report, confusion_matrix,
                                  f1_score, precision_score, recall_score)

    labels   = ["IN_DOMAIN", "BOUNDARY", "OUT_OF_DOMAIN"]
    report   = classification_report(y_true, y_pred, labels=labels,
                                      zero_division=0, output_dict=True)
    cm       = confusion_matrix(y_true, y_pred, labels=labels).tolist()
    accuracy = sum(t==p for t,p in zip(y_true,y_pred)) / len(y_true)
    f1_macro = f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0)
    f1_micro = f1_score(y_true, y_pred, average="micro", labels=labels, zero_division=0)

    prec_each = {l: round(report[l]["precision"], 4) for l in labels if l in report}
    rec_each  = {l: round(report[l]["recall"],    4) for l in labels if l in report}
    f1_each   = {l: round(report[l]["f1-score"],  4) for l in labels if l in report}

    print("\n   Computing bootstrap CIs...")

    def macro_f1(yt,yp):    return f1_score(yt,yp,average="macro",labels=labels,zero_division=0)
    def accuracy_fn(yt,yp): return sum(t==p for t,p in zip(yt,yp))/len(yt)
    def in_f1(yt,yp):       return f1_score(yt,yp,labels=["IN_DOMAIN"],average="micro",zero_division=0)
    def in_rec(yt,yp):      return recall_score(yt,yp,labels=["IN_DOMAIN"],average="micro",zero_division=0)
    def ood_rec(yt,yp):     return recall_score(yt,yp,labels=["OUT_OF_DOMAIN"],average="micro",zero_division=0)

    ci_macro  = bootstrap_ci(y_true, y_pred, macro_f1)
    ci_acc    = bootstrap_ci(y_true, y_pred, accuracy_fn)
    ci_in_f1  = bootstrap_ci(y_true, y_pred, in_f1)
    ci_in_rec = bootstrap_ci(y_true, y_pred, in_rec)
    ci_ood    = bootstrap_ci(y_true, y_pred, ood_rec)

    print("\n" + "="*60)
    print("  RESULTS")
    print("="*60)
    print(f"\n  Accuracy:         {accuracy:.4f}  95% CI [{ci_acc[0]:.4f}, {ci_acc[1]:.4f}]")
    print(f"  F1 macro:         {f1_macro:.4f}  95% CI [{ci_macro[0]:.4f}, {ci_macro[1]:.4f}]  "
          f"{'✅ >0.87' if f1_macro>0.87 else '❌ <0.87'}")
    print(f"\n  IN_DOMAIN F1:     {f1_each.get('IN_DOMAIN',0):.4f}  95% CI [{ci_in_f1[0]:.4f}, {ci_in_f1[1]:.4f}]")
    print(f"  IN_DOMAIN Recall: {rec_each.get('IN_DOMAIN',0):.4f}  95% CI [{ci_in_rec[0]:.4f}, {ci_in_rec[1]:.4f}]  "
          f"{'✅ >0.85' if rec_each.get('IN_DOMAIN',0)>0.85 else '❌ <0.85'}")
    print(f"  OOD Recall:       {rec_each.get('OUT_OF_DOMAIN',0):.4f}  95% CI [{ci_ood[0]:.4f}, {ci_ood[1]:.4f}]  "
          f"{'✅ >0.90' if rec_each.get('OUT_OF_DOMAIN',0)>0.90 else '❌ <0.90'}")
    print(f"\n  Per-class:")
    for l in labels:
        print(f"    {l:20}  P={prec_each.get(l,0):.3f}  R={rec_each.get(l,0):.3f}  F1={f1_each.get(l,0):.3f}")

    # Save
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    metrics = {
        "component": "Guard 1 — Boundary Classification",
        "timestamp": datetime.now().isoformat(),
        "n_questions": len(questions),
        "accuracy": round(accuracy, 4),
        "f1_macro": round(f1_macro, 4),
        "f1_micro": round(f1_micro, 4),
        "labels": labels,
        "precision_per_class": prec_each,
        "recall_per_class": rec_each,
        "f1_per_class": f1_each,
        "confusion_matrix": cm,
        "label_counts": {l: sum(1 for q in questions if q["label"]==l) for l in labels},
        "confidence_intervals_95": {
            "f1_macro":         {"lower": ci_macro[0],  "upper": ci_macro[1]},
            "accuracy":         {"lower": ci_acc[0],    "upper": ci_acc[1]},
            "in_domain_f1":     {"lower": ci_in_f1[0],  "upper": ci_in_f1[1]},
            "in_domain_recall": {"lower": ci_in_rec[0], "upper": ci_in_rec[1]},
            "ood_recall":       {"lower": ci_ood[0],    "upper": ci_ood[1]},
        },
        "targets":   {"f1_macro": 0.87, "in_domain_recall": 0.85},
        "baselines": {"EON_Brainy_boundary_accuracy": 0.82, "prompt_only_systems": 0.75},
    }
    with open(OUT_JSON, "w") as f:
        json.dump(metrics, f, indent=2)

    report_str = classification_report(y_true, y_pred, labels=labels, zero_division=0)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(f"EduSHIELD — Guard 1 Boundary Evaluation (v3)\nGenerated: {ts}\n\n")
        f.write(f"n={len(questions)}  Accuracy={accuracy:.4f}  Macro-F1={f1_macro:.4f}\n\n")
        f.write(report_str)

    print(f"\n  Saved: {OUT_CSV}")
    print(f"  Saved: {OUT_JSON}")
    kg.close()
    print("\n[Done] ✅")


if __name__ == "__main__":
    run()
