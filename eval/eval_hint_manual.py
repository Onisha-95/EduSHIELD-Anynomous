"""
EduSHIELD v2 — Manual Hint Error Rate Review
=============================================
This script generates 30 responses from EduSHIELD then saves them
to a review file so YOU can rate each one.

This gives you the most important comparison in your paper:
  EduSHIELD hint error rate vs Stamper 2024 (35% unguarded GPT)

Step 1: python3 eval/eval_hint_manual.py --generate
Step 2: Open eval/results/hint_review_manual.csv
        Rate each response: A=Appropriate, G=Too Generic, F=Factually Wrong
Step 3: python3 eval/eval_hint_manual.py --score

Copy to: ~/Desktop/EduSHIELD/eval/eval_hint_manual.py
"""
import sys, os, csv, json, random, argparse
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))

from config import (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
                    NEO4J_DATABASE, CHROMA_PATH,
                    PARLEY_API_KEY, PARLEY_BASE_URL, LLM_MODEL)

HINTS_CSV   = os.path.join(PROJECT_ROOT, "hint_review_prompts.csv")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "eval", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
REVIEW_CSV  = os.path.join(RESULTS_DIR, "hint_review_manual.csv")
OUT_JSON    = os.path.join(RESULTS_DIR, "hint_manual_metrics.json")

SAMPLE_SIZE = 30
random.seed(42)


def get_response(question, rag):
    retrieved = rag.retrieve_context(question, top_k=5)
    facts_text = "\n".join(
        f"- {r.get('concept','')}: {r.get('claim','')}"
        for r in retrieved[:5] if r.get("claim","")
    )
    from openai import OpenAI
    from config import OPENAI_API_KEY
    prompt = (
        f"You are a CS tutor for CSE1321 (Programming & Problem Solving I) "
        f"and CSE1300 (Computing & Society).\n"
        f"IMPORTANT: CSE1321 uses C# as its programming language. "
        f"Always use C# syntax in all code examples. Never use Python or Java.\n\n"
        f"Course facts:\n{facts_text}\n\n"
        f"Student question: {question}\n\nAnswer in 2-3 sentences using C# syntax where relevant:"
    )
    try:
        client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else \
                 OpenAI(api_key=PARLEY_API_KEY, base_url=PARLEY_BASE_URL)
        resp = client.chat.completions.create(
            model=LLM_MODEL, messages=[{"role":"user","content":prompt}],
            max_tokens=200, temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"ERROR: {e}"


def generate():
    if not os.path.exists(HINTS_CSV):
        print(f"[x] Not found: {HINTS_CSV}"); return

    all_qs = list(csv.DictReader(open(HINTS_CSV, encoding="utf-8")))
    sampled = random.sample(all_qs, min(SAMPLE_SIZE, len(all_qs)))

    print(f"\n   Generating {len(sampled)} responses from EduSHIELD...")
    from core.neo4j_client import Neo4jKGClient
    from core.rag_system    import RAGSystem
    kg  = Neo4jKGClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)
    rag = RAGSystem(kg, CHROMA_PATH)

    rows = []
    for i, q in enumerate(sampled):
        resp = get_response(q["question"], rag)
        rows.append({
            "id":           i+1,
            "question":     q["question"],
            "module":       q.get("module",""),
            "type":         q.get("question_type",""),
            "response":     resp,
            "your_rating":  "",   # YOU fill this in: A / G / F
            "notes":        "",   # optional comment
        })
        if (i+1) % 5 == 0:
            print(f"   {i+1}/{len(sampled)} done...")

    with open(REVIEW_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    kg.close()
    print(f"\n[ok] Saved to: {REVIEW_CSV}")
    print(f"""
Instructions:
  1. Open {REVIEW_CSV}
  2. For each row, fill in the 'your_rating' column:
       A = Appropriate — factually correct and helpful
       G = Too Generic — vague, not grounded in course content
       F = Factually Wrong — contains incorrect information
  3. Save the file
  4. Run: python3 eval/eval_hint_manual.py --score

This comparison is critical:
  Stamper 2024 found 35% of unguarded GPT hints were G or F.
  Our target: < 10% G+F with EduSHIELD active.
""")


def score():
    if not os.path.exists(REVIEW_CSV):
        print(f"[x] Not found. Run --generate first."); return

    rows = list(csv.DictReader(open(REVIEW_CSV, encoding="utf-8")))
    rated = [r for r in rows if r.get("your_rating","").strip().upper() in ("A","G","F")]

    if len(rated) < 10:
        print(f"[x] Only {len(rated)} rated rows. Rate at least 10 before scoring.")
        return

    n = len(rated)
    appropriate = sum(1 for r in rated if r["your_rating"].upper() == "A")
    generic     = sum(1 for r in rated if r["your_rating"].upper() == "G")
    wrong       = sum(1 for r in rated if r["your_rating"].upper() == "F")
    error_rate  = (generic + wrong) / n

    # By question type
    type_errors = {}
    for r in rated:
        t = r.get("type","")
        if t not in type_errors:
            type_errors[t] = {"total":0,"errors":0}
        type_errors[t]["total"] += 1
        if r["your_rating"].upper() in ("G","F"):
            type_errors[t]["errors"] += 1

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("\n" + "="*60)
    print("  Manual Hint Review — Results")
    print("="*60)
    print(f"\n  Responses rated:    {n}")
    print(f"  Appropriate (A):    {appropriate}  ({appropriate/n*100:.1f}%)")
    print(f"  Too Generic (G):    {generic}       ({generic/n*100:.1f}%)")
    print(f"  Factually Wrong (F):{wrong}          ({wrong/n*100:.1f}%)")
    print(f"\n  Error rate (G+F):   {error_rate*100:.1f}%  "
          f"{'✅ <10%' if error_rate<0.10 else '❌ >10%'}")
    print(f"\n  Baseline: Stamper 2024 — 35% error rate (unguarded GPT)")
    print(f"  EduSHIELD:             {error_rate*100:.1f}%")
    if error_rate < 0.35:
        improvement = (0.35 - error_rate) / 0.35 * 100
        print(f"  Improvement vs baseline: {improvement:.1f}% reduction")

    print(f"\n  By question type:")
    for t, d in type_errors.items():
        er = d["errors"]/max(d["total"],1)*100
        print(f"    {t:20} {er:.0f}% errors  (n={d['total']})")

    metrics = {
        "component": "Manual Hint Error Rate Review",
        "timestamp": ts,
        "n_rated": n,
        "appropriate": appropriate,
        "too_generic": generic,
        "factually_wrong": wrong,
        "error_rate": round(error_rate, 4),
        "baselines": {"Stamper_2024_unguarded_GPT": 0.35,
                      "Liu_ACL_2024": 0.35},
        "per_type": {t: round(d["errors"]/max(d["total"],1),4)
                     for t,d in type_errors.items()},
        "paper_statement": (
            f"Manual expert review of {n} EduSHIELD responses by a domain expert "
            f"(the first author) rated {appropriate} ({appropriate/n*100:.1f}%) as appropriate, "
            f"{generic} ({generic/n*100:.1f}%) as too generic, and {wrong} ({wrong/n*100:.1f}%) "
            f"as factually incorrect, yielding an error rate of {error_rate*100:.1f}%. "
            f"This compares favourably to Stamper et al. (2024) who reported 35% problematic "
            f"hints from unguarded GPT."
        )
    }
    with open(OUT_JSON,"w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n  Paper statement saved to: {OUT_JSON}")
    print(f"\n  In your paper write:")
    print(f"  \"{metrics['paper_statement']}\"")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--generate", action="store_true")
    p.add_argument("--score",    action="store_true")
    args = p.parse_args()
    if args.generate: generate()
    elif args.score:  score()
    else: p.print_help()
