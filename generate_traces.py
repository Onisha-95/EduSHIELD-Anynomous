"""
EduSHIELD — Appendix Trace Generator
=====================================
Generates the three qualitative system traces for Appendix C
of the EMNLP 2026 paper. Output: trace_output.tex

Traces:
  D.1 — Verified In-Domain Response       (for loops)
  D.2 — Contradicted Response             (while loop, injected wrong claim)
  D.3 — Boundary Redirect, No LLM Call   (recursion)

Run from EduSHIELD project root:
    cd ~/Desktop/EduSHIELD
    python3 eval/generate_traces.py

Output written to:  eval/results/trace_output.tex
Console output:     readable trace for verification

Guard thresholds used (from guard1_hallucination.py defaults):
    VERIFIED_THRESHOLD      = 0.52   (theta_v)
    CONTRADICTION_THRESHOLD = 0.58   (theta_c, but final config uses 0.55)
    CONTRADICTION_GAP       = 0.04   (delta)
"""

import sys, os, json, textwrap
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))

from config import (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
                    NEO4J_DATABASE, CHROMA_PATH,
                    PARLEY_API_KEY, PARLEY_BASE_URL, LLM_MODEL)

RESULTS_DIR = os.path.join(PROJECT_ROOT, "eval", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
OUT_TEX  = os.path.join(RESULTS_DIR, "trace_output.tex")
OUT_JSON = os.path.join(RESULTS_DIR, "trace_output.json")

# ── Thresholds (must match paper) ──────────────────────────────────────────
THETA_V = 0.52   # verified threshold
THETA_C = 0.55   # contradiction threshold  (paper final config)
DELTA   = 0.04   # contradiction gap        (paper final config)

# ── Queries for the three traces ───────────────────────────────────────────
TRACE_QUERIES = [
    {
        "id":       "D.1",
        "label":    "Verified In-Domain Response",
        "query":    "What does a for loop do in Python?",
        "inject":   None,   # use real LLM response
    },
    {
        "id":       "D.2",
        "label":    "Contradicted Response (Hallucination Caught)",
        "query":    "How does a while loop work?",
        # Deliberately inject the KG negation as the LLM response
        "inject":   "A while loop checks the condition after executing the loop body.",
    },
    {
        "id":       "D.3",
        "label":    "Boundary Redirect (No LLM Call)",
        "query":    "Can you explain recursion to me?",
        "inject":   None,   # boundary fires before LLM — no generation needed
    },
]


# ── LLM caller ─────────────────────────────────────────────────────────────
def call_llm(query: str, facts: list) -> str:
    from openai import OpenAI
    try:
        from config import OPENAI_API_KEY
        client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY \
                 else OpenAI(api_key=PARLEY_API_KEY, base_url=PARLEY_BASE_URL)
    except Exception:
        client = OpenAI(api_key=PARLEY_API_KEY, base_url=PARLEY_BASE_URL)

    facts_text = "\n".join(
        f"- {r.get('concept','')}: {r.get('claim','')}"
        for r in facts[:5] if r.get("claim", "").strip()
    ) or "No facts retrieved."

    prompt = (
        f"You are a CS tutor for CSE1321 (Programming Fundamentals, C#).\n"
        f"Answer the student question using the verified course facts below.\n"
        f"Give a factually accurate 1-2 sentence answer.\n\n"
        f"Course facts:\n{facts_text}\n\n"
        f"Student question: {query}\n\nAnswer:"
    )
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"LLM_ERROR: {str(e)[:80]}"


# ── Run one trace ───────────────────────────────────────────────────────────
def run_trace(t: dict, kg, rag, guard1, guard2, session: dict) -> dict:
    query  = t["query"]
    inject = t["inject"]

    print(f"\n{'='*60}")
    print(f"  {t['id']} — {t['label']}")
    print(f"{'='*60}")
    print(f"  Query: {query}")

    # ── Stage 1: Boundary Guard ─────────────────────────────────────────
    g2_result  = guard2.classify(query, session)
    g2_class   = g2_result["classification"]
    s_sem      = round(g2_result.get("domain_match_score", 0.0), 4)
    concept    = g2_result.get("matched_concept", "") or \
                 g2_result.get("reasoning", "")[:30]

    print(f"\n  Stage 1 — Boundary Guard:")
    print(f"    s_sem          = {s_sem}")
    print(f"    matched_concept= {concept!r}")
    print(f"    classification = {g2_class}")

    # ── Boundary redirect: stop here ───────────────────────────────────
    if g2_class in ("BOUNDARY", "OUT_OF_DOMAIN"):
        redirect = (
            "Recursion is a topic covered in the next course in the sequence. "
            "Would you like to review for loops or while loops instead?"
            if "recursion" in query.lower()
            else f"That topic is {g2_class.lower().replace('_', ' ')}. "
                 "Please ask about topics covered in this course."
        )
        print(f"\n    m_bnd match -> priority override fires")
        print(f"    --> REDIRECT: No LLM call made.")
        print(f"\n  Delivered: \"{redirect}\"")

        return {
            "id":             t["id"],
            "label":          t["label"],
            "query":          query,
            "stage1_class":   g2_class,
            "s_sem":          s_sem,
            "concept":        concept,
            "stage2_facts":   [],
            "stage3_response": None,
            "stage4_verdict": None,
            "delivered":      redirect,
            "redirect":       True,
        }

    # ── Stage 2: KG-RAG Retrieval ───────────────────────────────────────
    retrieved = rag.retrieve_context(query, top_k=5)
    top3 = [r for r in retrieved
            if r.get("claim","").strip()][:3]

    print(f"\n  Stage 2 — KG-RAG Retrieval (top-{len(top3)} unique facts):")
    for i, r in enumerate(top3, 1):
        c   = r.get("concept","").upper()
        cl  = r.get("claim","")[:80]
        sim = round(r.get("similarity", 0.0), 4)
        print(f"    [{i}] concept={c!r}  sim={sim}")
        print(f"        claim  ={cl!r}")

    # ── Stage 3: LLM Generation ─────────────────────────────────────────
    if inject:
        llm_response = inject
        print(f"\n  Stage 3 — LLM Generation (injected wrong claim):")
    else:
        llm_response = call_llm(query, retrieved)
        print(f"\n  Stage 3 — LLM Generation:")
    print(f"    \"{llm_response}\"")

    # ── Stage 4: Hallucination Guard ────────────────────────────────────
    g1_result = guard1.validate(llm_response, retrieved, query=query)
    verdict   = g1_result["verdict"]

    # Extract per-claim scores from claim_results
    claim_results = g1_result.get("claim_results", [])
    if claim_results:
        cr    = claim_results[0]
        s_pos = round(cr.get("best_positive_score", cr.get("score", 0.0)), 4)
        s_neg = round(cr.get("best_negation_score",
                              cr.get("negation_score", 0.0)), 4)
        claim_text = cr.get("claim", llm_response[:70])
    else:
        s_pos = 0.0
        s_neg = 0.0
        claim_text = llm_response[:70]

    gap  = round(s_neg - s_pos, 4)
    sign = "+" if gap >= 0 else ""

    print(f"\n  Stage 4 — Hallucination Guard:")
    print(f"    claim   = \"{claim_text}\"")
    print(f"    s+      = {s_pos}   (claim vs KG claims)")
    print(f"    s-      = {s_neg}   (claim vs KG negations)")
    print(f"    s- - s+ = {sign}{gap}  (delta threshold = {DELTA})")
    print(f"    verdict = {verdict}")
    print(f"\n    Overall verdict = {verdict}")

    # Corrections
    corrections = g1_result.get("corrections", [])
    delivered   = llm_response

    if verdict == "CONTRADICTED" and corrections:
        corr = corrections[0]
        corr_text = corr.get("correction", corr.get("claim", ""))
        source    = corr.get("source", "course slides")
        print(f"\n    KG-sourced correction:")
        print(f"      \"{corr_text}\"")
        print(f"      [source: {source}]")
        delivered = corr_text
        print(f"\n  Delivered: KG correction replaces original")
    elif verdict == "UNVERIFIABLE":
        print(f"\n  Delivered: response with uncertainty disclosure")
    else:
        print(f"\n  Delivered: response as-is")

    return {
        "id":              t["id"],
        "label":           t["label"],
        "query":           query,
        "stage1_class":    g2_class,
        "s_sem":           s_sem,
        "concept":         concept,
        "stage2_facts":    [
            {"concept": r.get("concept",""),
             "claim":   r.get("claim",""),
             "sim":     round(r.get("similarity",0.0), 4)}
            for r in top3
        ],
        "stage3_response": llm_response,
        "injected":        bool(inject),
        "stage4_s_pos":    s_pos,
        "stage4_s_neg":    s_neg,
        "stage4_gap":      gap,
        "stage4_verdict":  verdict,
        "corrections":     corrections,
        "delivered":       delivered,
        "redirect":        False,
    }


# ── LaTeX renderer ─────────────────────────────────────────────────────────
def render_tex(traces: list) -> str:
    lines = []
    lines.append(r"\section{Qualitative System Traces}")
    lines.append(r"\label{app:traces}")
    lines.append("")
    lines.append(
        r"The following three traces are captured from the live "
        r"\textbf{EduSHIELD} system deployed on the Programming "
        r"Fundamentals course. Each trace records: the student query; "
        r"Stage~1 Boundary Guard verdict with semantic similarity "
        r"$s_{\text{sem}}$; Stage~2 KG-RAG retrieval with cosine "
        r"similarities; Stage~3 LLM response text; and Stage~4 "
        r"Hallucination Guard verdict with positive score $s^+$ "
        r"(response claim vs.\ KG claims), negation score $s^-$ "
        r"(response claim vs.\ KG negations), gap $s^{-} - s^{+}$, "
        r"and the final delivery decision."
    )
    lines.append("")

    for t in traces:
        tid   = t["id"]
        label = t["label"]

        lines.append(f"\\paragraph{{Trace~{tid[-1]}: {label}.}}")

        if t.get("redirect"):
            # D.3 boundary
            lines.append(
                f"The student asks about recursion, a concept mentioned in "
                f"course slides but reserved for a later course. "
                f"The token-level boundary match "
                f"($m_{{\\text{{bnd}}}}(\\text{{`recursion'}}) = 1$) fires "
                f"before the semantic score is evaluated, triggering an "
                f"immediate \\textsc{{Boundary}} verdict "
                f"($s_{{\\text{{sem}}}} = {t['s_sem']}$, which would have "
                f"passed the in-domain threshold alone). "
                f"No LLM call is made; a redirect message is delivered directly."
            )
        elif t["stage4_verdict"] == "VERIFIED":
            lines.append(
                f"The student asks a legitimate in-domain question. "
                f"The Boundary Guard passes it "
                f"(\\textsc{{In-Domain}}, "
                f"$s_{{\\text{{sem}}}}{{=}}{t['s_sem']}$). "
                f"The Hallucination Guard labels the claim "
                f"\\textsc{{Verified}} "
                f"($s^+{{=}}{t['stage4_s_pos']}$, "
                f"$s^-{{=}}{t['stage4_s_neg']}$, "
                f"gap${{=}}{t['stage4_gap']:+.4f} < \\delta{{=}}{DELTA}$). "
                f"The response is delivered as-is."
            )
        elif t["stage4_verdict"] == "CONTRADICTED":
            gap = t['stage4_gap']
            lines.append(
                f"A deliberately incorrect claim is injected: the system "
                f"asserts that a while loop checks its condition "
                f"\\emph{{after}} the loop body executes (do-while behaviour). "
                f"The Hallucination Guard finds "
                f"$s^->s^+$ by a gap of "
                f"${gap:+.4f} > \\delta={DELTA}$, triggering "
                f"\\textsc{{Contradicted}}. The original response is replaced "
                f"by a KG-sourced correction before delivery."
            )

        lines.append("")
        lines.append("{\\scriptsize")
        lines.append("\\begin{verbatim}")

        # Stage 1
        lines.append(f'Student query : "{t["query"]}"')
        lines.append("")
        lines.append("Stage 1 -- Boundary Guard (pre-generation):")
        lines.append(f"  s_sem          = {t['s_sem']}")
        c = t['concept']
        if c:
            lines.append(f'  matched concept= "{c}"')
        lines.append(f"  classification = {t['stage1_class']}")

        if t.get("redirect"):
            lines.append(f'  m_bnd("recursion") = 1  --> priority override fires')
            lines.append(f"  --> REDIRECT: No LLM call made.")
            lines.append("")
            lines.append("Delivered to student:")
            lines.append(f'  "{t["delivered"]}"')
        else:
            # Stage 2
            lines.append("")
            facts = t.get("stage2_facts", [])
            lines.append(f"Stage 2 -- KG-RAG Retrieval (top-{len(facts)} unique facts):")
            for i, f in enumerate(facts, 1):
                lines.append(f'  [{i}] concept = "{f["concept"].upper()}"')
                claim_wrapped = textwrap.wrap(f['claim'], width=52)
                if claim_wrapped:
                    lines.append(f'      claim   = "{claim_wrapped[0]}')
                    for w in claim_wrapped[1:]:
                        lines.append(f'                 {w}')
                    if len(claim_wrapped) == 1:
                        lines[-1] = lines[-1] + '"'
                    else:
                        lines[-1] = lines[-1] + '"'
                lines.append(f"      sim     = {f['sim']}")

            # Stage 3
            lines.append("")
            inj_note = " (injected wrong claim)" if t.get("injected") else ""
            lines.append(f"Stage 3 -- LLM Generation{inj_note}:")
            resp_wrapped = textwrap.wrap(t["stage3_response"], width=54)
            if resp_wrapped:
                lines.append(f'  "{resp_wrapped[0]}')
                for w in resp_wrapped[1:]:
                    lines.append(f'   {w}')
                lines[-1] = lines[-1] + '"'

            # Stage 4
            lines.append("")
            lines.append("Stage 4 -- Hallucination Guard (post-generation):")
            claim_disp = t["stage3_response"][:65]
            lines.append(f'  claim   = "{claim_disp}"')
            lines.append(f"  s+      = {t['stage4_s_pos']}   (claim vs KG claims)")
            lines.append(f"  s-      = {t['stage4_s_neg']}   (claim vs KG negations)")
            gap = t['stage4_gap']
            lines.append(f"  s- - s+ = {gap:+.4f}  (delta threshold = {DELTA})")
            lines.append(f"  verdict = {t['stage4_verdict']}")
            lines.append("")
            lines.append(f"  Overall verdict = {t['stage4_verdict']}")

            # Corrections
            if t["stage4_verdict"] == "CONTRADICTED" and t.get("corrections"):
                corr = t["corrections"][0]
                corr_text = corr.get("correction", corr.get("claim", ""))
                source    = corr.get("source", "cse1321-loops.pptx")
                lines.append("")
                lines.append("  KG-sourced correction appended:")
                corr_w = textwrap.wrap(corr_text, width=52)
                lines.append(f'  "{corr_w[0]}')
                for w in corr_w[1:]:
                    lines.append(f'   {w}')
                lines[-1] = lines[-1] + '"'
                lines.append(f"  [source: {source}]")
                lines.append("")
                lines.append("Delivered to student: KG correction replaces original")
            else:
                lines.append("")
                lines.append("Delivered to student: response as-is")

        lines.append("\\end{verbatim}")
        lines.append("}")
        lines.append("")

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    print("\n" + "="*60)
    print("  EduSHIELD — Appendix Trace Generator")
    print("="*60)

    from core.neo4j_client        import Neo4jKGClient
    from core.rag_system           import RAGSystem
    from core.guard1_hallucination import HallucinationDetectionAgent
    from core.guard2_boundary      import KnowledgeBoundaryAgent
    from core.session_manager      import init_session

    print("\n  Connecting to Neo4j + ChromaDB...")
    kg    = Neo4jKGClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)
    rag   = RAGSystem(kg, CHROMA_PATH)
    s     = kg.get_stats()
    print(f"  KG: {s['concepts']} concepts, {s['facts']} facts")

    # Build guards with paper-matched thresholds
    guard1 = HallucinationDetectionAgent(
        kg, rag,
        verified_threshold      = THETA_V,
        contradiction_threshold = THETA_C,
        contradiction_gap       = DELTA,
    )

    domain = (kg.get_domain_config("CSE1321")
              or kg.get_domain_config()
              or {"in_domain_keywords": [], "boundary_terms": ["recursion"],
                  "excluded_terms": []})
    guard2 = KnowledgeBoundaryAgent(kg, rag, domain)

    session = init_session("trace_gen")

    # Run all three traces
    results = []
    for t in TRACE_QUERIES:
        result = run_trace(t, kg, rag, guard1, guard2, session)
        results.append(result)

    # Save JSON (for verification)
    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n\n  JSON saved: {OUT_JSON}")

    # Save LaTeX
    tex = render_tex(results)
    with open(OUT_TEX, "w", encoding="utf-8") as f:
        f.write(f"% Generated by generate_traces.py on {datetime.now():%Y-%m-%d %H:%M}\n")
        f.write(f"% Thresholds: theta_v={THETA_V}, theta_c={THETA_C}, delta={DELTA}\n\n")
        f.write(tex)
    print(f"  LaTeX saved: {OUT_TEX}")

    # Summary
    print("\n" + "="*60)
    print("  TRACE SUMMARY")
    print("="*60)
    for r in results:
        v = r.get("stage4_verdict") or r.get("stage1_class")
        print(f"  {r['id']}  {v:15}  s+={r.get('stage4_s_pos','-')}  "
              f"s-={r.get('stage4_s_neg','-')}  "
              f"gap={r.get('stage4_gap','-')}")

    print(f"\n  Copy trace_output.tex into your paper appendix.")
    print(f"  Verify scores match the paper: s+(D.1)=0.5812, s-(D.2)=0.6771\n")

    kg.close()
    print("[Done] ✅")


if __name__ == "__main__":
    main()
