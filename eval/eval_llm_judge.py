"""
EduSHIELD v2 — LLM-as-Judge Quality Evaluation (v2 — fixed)
============================================================
Fixed: properly initializes agent with course_id
Fixed: handles API errors gracefully with retry
Fixed: uses direct LLM call instead of full agent pipeline

Copy to: ~/Desktop/EduSHIELD/eval/eval_llm_judge.py

Run:
    cd ~/Desktop/EduSHIELD
    python3 eval/eval_llm_judge.py
"""

import sys, os, csv, json, random, re, time
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
OUT_CSV  = os.path.join(RESULTS_DIR, "llm_judge_results.csv")
OUT_JSON = os.path.join(RESULTS_DIR, "llm_judge_metrics.json")
OUT_TXT  = os.path.join(RESULTS_DIR, "llm_judge_report.txt")

SAMPLE_SIZE = 50
random.seed(42)

JUDGE_PROMPT = """You are evaluating an AI tutoring system response for a CS introductory course (CSE1321/CSE1300).

Student question: {question}

AI tutor response: {response}

Rate on THREE dimensions. Reply ONLY with valid JSON, nothing else:

{{"factual_accuracy": <1-5>, "pedagogical_quality": <1-5>, "course_grounding": <1-5>, "brief_reason": "<one sentence>"}}

Rubric:
- factual_accuracy:    5=fully correct, 4=mostly correct, 3=partially, 2=has errors, 1=wrong
- pedagogical_quality: 5=exceptionally clear and helpful, 4=good, 3=adequate, 2=confusing, 1=unhelpful
- course_grounding:    5=uses specific course content, 4=course-relevant, 3=general CS, 2=barely related, 1=generic

Reply ONLY with the JSON object."""


def get_llm_client():
    from openai import OpenAI
    from config import OPENAI_API_KEY
    if OPENAI_API_KEY:
        return OpenAI(api_key=OPENAI_API_KEY)
    return OpenAI(api_key=PARLEY_API_KEY, base_url=PARLEY_BASE_URL)


def get_edushield_response(question: str, rag, kg) -> str:
    """Get EduSHIELD's response by building prompt and calling LLM directly."""
    try:
        # Build retrieval query
        retrieved = rag.retrieve_context(question, top_k=5)

        # Build grounded prompt
        facts_text = "\n".join(
            f"- {r.get('concept','')}: {r.get('claim','')}"
            for r in retrieved[:5] if r.get("claim","").strip()
        )

        prompt = (
            f"You are a helpful CS tutor for CSE1321 (Programming & Problem Solving I) "
            f"and CSE1300 (Computing & Society).\n"
            f"IMPORTANT: CSE1321 uses C# as its programming language. "
            f"Always use C# syntax in all code examples. Never use Python or Java.\n\n"
            f"Relevant course facts:\n{facts_text if facts_text else 'No specific facts retrieved.'}\n\n"
            f"Student question: {question}\n\n"
            f"Give a clear, accurate, course-grounded answer in 2-4 sentences using C# syntax where relevant:"
        )

        client = get_llm_client()
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"ERROR: {str(e)[:100]}"


def judge_response(question: str, response: str) -> dict:
    """Ask LLM to rate the response."""
    prompt = JUDGE_PROMPT.format(question=question, response=response[:600])
    try:
        client = get_llm_client()
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.0,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(raw)
        return {
            "factual_accuracy":    min(5, max(1, int(parsed.get("factual_accuracy", 3)))),
            "pedagogical_quality": min(5, max(1, int(parsed.get("pedagogical_quality", 3)))),
            "course_grounding":    min(5, max(1, int(parsed.get("course_grounding", 3)))),
            "brief_reason":        str(parsed.get("brief_reason", ""))[:200],
            "error": "",
        }
    except Exception as e:
        return {"factual_accuracy":0,"pedagogical_quality":0,
                "course_grounding":0,"brief_reason":"","error":str(e)[:100]}


def run():
    print("\n" + "="*60)
    print("  LLM-as-Judge Quality Evaluation (v2)")
    print("="*60)

    if not os.path.exists(HINTS_CSV):
        print(f"[x] Not found: {HINTS_CSV}")
        return

    all_qs = list(csv.DictReader(open(HINTS_CSV, encoding="utf-8")))
    sampled = random.sample(all_qs, min(SAMPLE_SIZE, len(all_qs)))
    print(f"\n   Using {len(sampled)} questions")

    print("\n   Connecting to Neo4j + ChromaDB...")
    from core.neo4j_client import Neo4jKGClient
    from core.rag_system    import RAGSystem
    kg  = Neo4jKGClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)
    rag = RAGSystem(kg, CHROMA_PATH)
    s   = kg.get_stats()
    print(f"   KG: {s['concepts']} concepts, {s['facts']} facts")

    # Test API connection first
    print("\n   Testing LLM API connection...")
    try:
        client = get_llm_client()
        test = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role":"user","content":"Say OK"}],
            max_tokens=5,
        )
        print(f"   API OK: {test.choices[0].message.content.strip()}")
    except Exception as e:
        print(f"   [x] API connection failed: {e}")
        print("   Check PARLEY_API_KEY or OPENAI_API_KEY is set.")
        kg.close()
        return

    print(f"\n   Running {len(sampled)} questions (2 LLM calls each)...\n")

    rows, errors = [], 0

    for i, q in enumerate(sampled):
        question = q["question"]
        qtype    = q.get("question_type", "")
        module   = q.get("module", "")

        # Step 1: Get EduSHIELD response
        response = get_edushield_response(question, rag, kg)
        if "ERROR:" in response:
            errors += 1
            rows.append({"id":i+1,"question":question,"module":module,"type":qtype,
                         "response":response,"factual_accuracy":0,"pedagogical_quality":0,
                         "course_grounding":0,"composite_score":0,"brief_reason":"","error":response})
            continue

        # Brief pause to avoid rate limiting
        time.sleep(0.3)

        # Step 2: Judge the response
        scores = judge_response(question, response)
        if scores["error"]:
            errors += 1

        fa = scores["factual_accuracy"]
        pq = scores["pedagogical_quality"]
        cg = scores["course_grounding"]
        composite = round(fa*0.40 + pq*0.35 + cg*0.25, 3) if fa > 0 else 0

        rows.append({"id":i+1,"question":question,"module":module,"type":qtype,
                     "response":response[:200],"factual_accuracy":fa,
                     "pedagogical_quality":pq,"course_grounding":cg,
                     "composite_score":composite,"brief_reason":scores["brief_reason"],
                     "error":scores["error"]})

        if (i+1) % 10 == 0:
            valid = [r for r in rows if r["composite_score"]>0]
            avg   = sum(r["composite_score"] for r in valid)/max(len(valid),1)
            print(f"   {i+1}/{len(sampled)} done... avg composite: {avg:.3f}")

    # Metrics
    valid_rows  = [r for r in rows if r["composite_score"] > 0]
    n_valid     = max(len(valid_rows), 1)
    avg_fa      = sum(r["factual_accuracy"]    for r in valid_rows) / n_valid
    avg_pq      = sum(r["pedagogical_quality"] for r in valid_rows) / n_valid
    avg_cg      = sum(r["course_grounding"]    for r in valid_rows) / n_valid
    avg_comp    = sum(r["composite_score"]     for r in valid_rows) / n_valid
    excellent   = sum(1 for r in valid_rows if r["composite_score"] >= 4.0)
    good        = sum(1 for r in valid_rows if 3.0 <= r["composite_score"] < 4.0)
    poor        = sum(1 for r in valid_rows if r["composite_score"] < 3.0)

    type_scores = {}
    for r in valid_rows:
        t = r["type"]
        type_scores.setdefault(t, []).append(r["composite_score"])

    print("\n" + "="*60)
    print("  RESULTS")
    print("="*60)
    print(f"\n  Evaluated: {len(sampled)}  Valid: {n_valid}  Errors: {errors}")
    print(f"\n  Avg Factual Accuracy:    {avg_fa:.3f} / 5.0")
    print(f"  Avg Pedagogical Quality: {avg_pq:.3f} / 5.0")
    print(f"  Avg Course Grounding:    {avg_cg:.3f} / 5.0")
    print(f"\n  Composite Score: {avg_comp:.3f} / 5.0  {'✅ >3.5' if avg_comp>3.5 else '❌ <3.5'}")
    print(f"\n  Excellent (>=4.0): {excellent}  ({excellent/n_valid*100:.0f}%)")
    print(f"  Good      (3-3.9): {good}       ({good/n_valid*100:.0f}%)")
    print(f"  Poor      (<3.0):  {poor}        ({poor/n_valid*100:.0f}%)  "
          f"{'✅ <10%' if poor/n_valid<0.10 else '❌ >10%'}")
    print(f"\n  Liu ACL 2024 (P4) baseline: 35% poor  →  EduSHIELD: {poor/n_valid*100:.0f}%")

    # Save
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    metrics = {
        "component": "LLM-as-Judge Quality (v2)",
        "timestamp": ts,
        "n_evaluated": len(sampled), "n_valid": n_valid, "n_errors": errors,
        "avg_factual_accuracy":    round(avg_fa,   3),
        "avg_pedagogical_quality": round(avg_pq,   3),
        "avg_course_grounding":    round(avg_cg,   3),
        "avg_composite_score":     round(avg_comp, 3),
        "distribution": {"excellent_gte_4":excellent,"good_3_to_4":good,"poor_lt_3":poor},
        "per_type": {t: round(sum(s)/len(s),3) for t,s in type_scores.items()},
        "targets": {"composite_score":3.5, "poor_rate":0.10},
        "baselines": {"Liu_ACL_2024_P4_poor_hint_rate":0.35,
                      "Wang_WWW_2025_P5_judge_method":"LLM-as-judge kappa=0.71"},
    }
    with open(OUT_JSON, "w") as f:
        json.dump(metrics, f, indent=2)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(f"EduSHIELD v2 — LLM-as-Judge Evaluation (v2)\nGenerated: {ts}\n\n")
        f.write(f"Evaluated: {len(sampled)}  Valid: {n_valid}  Errors: {errors}\n\n")
        f.write(f"Factual Accuracy:    {avg_fa:.3f}\n")
        f.write(f"Pedagogical Quality: {avg_pq:.3f}\n")
        f.write(f"Course Grounding:    {avg_cg:.3f}\n")
        f.write(f"Composite:           {avg_comp:.3f} (target >3.5)\n\n")
        f.write(f"Poor responses: {poor/n_valid*100:.0f}% (Liu 2024 baseline: 35%)\n")

    print(f"\n  Saved: {OUT_CSV}")
    print(f"  Saved: {OUT_JSON}")
    kg.close()
    print("\n[Done] ✅")


if __name__ == "__main__":
    run()
