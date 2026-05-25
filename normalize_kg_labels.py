"""
EduSHIELD — KG Concept Label Normalization
==========================================
Fixes junk slide-heading concept labels in Neo4j so Guard #1
can produce meaningful negation embeddings.

PROBLEM:
  Labels like "our final gate is not", "python – if-elif-else – bad version",
  "think of it another way" are slide headings, not concept names.
  Auto-negation of these labels produces meaningless embeddings,
  causing Guard #1 catch rate to be low (~30%).

FIX:
  For each concept label, call the LLM to produce a clean concept name.
  Then update Neo4j and regenerate the negation for all facts under that concept.

WHAT CHANGES:
  - Concept node: label updated in place (Neo4j)
  - Fact nodes: negation field regenerated with clean label context
  - ChromaDB: must rebuild after running this script

RUN:
  cd ~/Desktop/EduSHIELD
  python normalize_kg_labels.py --course CSE1321 --dry-run   # preview only
  python normalize_kg_labels.py --course CSE1321              # apply changes
  python normalize_kg_labels.py --all                         # all courses

  Then rebuild ChromaDB:
  python run_ingestion.py --rebuild-index --course CSE1321
  python run_ingestion.py --rebuild-index --course CSE1300
  python run_ingestion.py --rebuild-index --course MATH1112

  Then re-run evals:
  python eval/eval_guard2_hallucination.py
  python eval/eval_guard1_boundary.py
  python eval/eval_rag.py
  python eval/eval_ab_hallucination.py
  python eval/eval_llm_judge.py
  python eval/visualize_results.py
"""

import os, sys, re, json, time, argparse
from openai import OpenAI
from neo4j import GraphDatabase

# ── Config ────────────────────────────────────────────────────────────────────
NEO4J_URI      = "neo4j://127.0.0.1:7687"
NEO4J_USER     = "neo4j"
NEO4J_PASSWORD = "password123"

PARLEY_API_KEY  = "tE70kPnhkWhMAw5ppVzg2Ma6KHaQ"
PARLEY_BASE_URL = "https://keys.theparley.org/v1"
LLM_MODEL       = "gpt-4o"

# ── Junk label patterns — these are slide headings, not concepts ───────────────
JUNK_PATTERNS = [
    # Sentence fragments and articles
    r"^(our|the|a|an|this|that|these|those|some|more|many|few)\s",
    # Numbered slides / sections
    r"^(slide|section|chapter|part|unit|week|day|class|lecture)\s*\d",
    # Vague directives
    r"^(think|consider|note|remember|recall|review|let's|let us|here is|here are)",
    # Question words without concept
    r"^(what|why|how|when|where|who)\s+(is|are|was|were|do|does|did|can|will|would|should|could)\b",
    # Bad version / example markers
    r"(bad version|good version|wrong way|right way|another way|example of|examples of)",
    # Connective phrases
    r"^(and|or|but|so|also|then|next|finally|first|second|third|last)",
    # Python/CS junk with dashes
    r"–\s*(bad|good|old|new|v\d|version|example|sample)",
    # Generic slide titles
    r"^(introduction|overview|summary|conclusion|recap|agenda|objectives|goals|motivation)",
    # Too short to be meaningful
]

def is_junk_label(label: str) -> bool:
    """Return True if the label looks like a slide heading, not a concept."""
    label = label.strip().lower()
    if len(label) < 4:
        return True
    if len(label.split()) > 8:  # Too long — likely a sentence
        return True
    for pat in JUNK_PATTERNS:
        if re.search(pat, label, re.IGNORECASE):
            return True
    return False


def clean_label_with_llm(client: OpenAI, label: str,
                          facts_sample: list[str]) -> str | None:
    """
    Ask Claude to produce a clean concept name for a junk label.
    Returns None if the label should be filtered out entirely.
    """
    facts_text = "\n".join(f"- {f}" for f in facts_sample[:5])

    prompt = f"""You are helping clean up a knowledge graph for a CS/Math tutoring system.

The following concept label was extracted from a slide heading and is not a clean concept name:
LABEL: "{label}"

Here are some facts stored under this concept:
{facts_text}

Your task:
1. If the facts describe a real CS/Math concept, return ONLY the clean concept name (2-5 words max).
   Examples: "for loop" → "for loop", "if-elif-else – bad version" → "if-elif-else statement",
   "our final gate is not" → "NOT gate", "think of it another way" → null
2. If the facts are too vague or the concept is not meaningful, return exactly: null

Return ONLY the clean concept name or null. No explanation. No quotes."""

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content.strip().strip('"').strip("'").lower()
        if result in ("null", "none", "", "n/a"):
            return None
        # Sanity check — must be short
        if len(result.split()) > 6:
            return None
        return result
    except Exception as e:
        print(f"    [!] LLM error for '{label}': {e}")
        return label  # Keep original on error


def auto_generate_negation(claim: str) -> str:
    """Simple rule-based negation — same logic as extraction_engine."""
    claim = claim.strip()
    # Direct negation patterns
    negations = [
        (r"\bis\b",       "is not"),
        (r"\bare\b",      "are not"),
        (r"\bwas\b",      "was not"),
        (r"\bwere\b",     "were not"),
        (r"\bhas\b",      "has no"),
        (r"\bhave\b",     "have no"),
        (r"\bcan\b",      "cannot"),
        (r"\bwill\b",     "will not"),
        (r"\bshould\b",   "should not"),
        (r"\bmust\b",     "must not"),
        (r"\ballows\b",   "does not allow"),
        (r"\benables\b",  "does not enable"),
        (r"\bcreates\b",  "does not create"),
        (r"\bdefines\b",  "does not define"),
        (r"\brepresents\b","does not represent"),
        (r"\bstores\b",   "does not store"),
        (r"\breturns\b",  "does not return"),
    ]
    for pattern, replacement in negations:
        if re.search(pattern, claim, re.IGNORECASE):
            return re.sub(pattern, replacement, claim, count=1, flags=re.IGNORECASE)
    # Fallback: prepend "It is false that"
    return f"It is false that: {claim}"


def run_normalization(course_id: str | None, dry_run: bool):
    """Main normalization pipeline."""

    # ── Connect ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  EduSHIELD — KG Label Normalization")
    print(f"  Course: {course_id or 'ALL'}  |  Dry run: {dry_run}")
    print(f"{'='*60}\n")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    client = OpenAI(
        api_key=PARLEY_API_KEY,
        base_url=PARLEY_BASE_URL
    )

    with driver.session() as session:

        # ── 1. Fetch all concept labels ───────────────────────────────────────
        if course_id:
            result = session.run(
                "MATCH (c:Concept) WHERE c.course_id = $cid "
                "RETURN c.label AS label, c.course_id AS cid",
                cid=course_id.upper()
            )
        else:
            result = session.run(
                "MATCH (c:Concept) RETURN c.label AS label, c.course_id AS cid"
            )

        all_concepts = [(r["label"], r["cid"]) for r in result if r["label"]]
        print(f"  Total concepts loaded: {len(all_concepts)}")

        # ── 2. Filter to junk labels only ─────────────────────────────────────
        junk = [(lbl, cid) for lbl, cid in all_concepts if is_junk_label(lbl)]
        clean = len(all_concepts) - len(junk)
        print(f"  Clean labels (no action needed): {clean}")
        print(f"  Junk labels to normalize:        {len(junk)}")

        if not junk:
            print("\n  [ok] No junk labels found — KG is already clean!")
            driver.close()
            return

        # ── 3. Preview junk labels ────────────────────────────────────────────
        print(f"\n  Sample junk labels:")
        for lbl, cid in junk[:15]:
            print(f"    [{cid}] \"{lbl}\"")
        if len(junk) > 15:
            print(f"    ... and {len(junk)-15} more")

        if dry_run:
            print(f"\n  [DRY RUN] Would normalize {len(junk)} labels.")
            print(f"  Run without --dry-run to apply changes.")
            driver.close()
            return

        # ── 4. Normalize each junk label with LLM ────────────────────────────
        print(f"\n  Normalizing {len(junk)} junk labels...")
        print(f"  (This will make {len(junk)} LLM API calls — may take a few minutes)\n")

        updated   = 0
        filtered  = 0
        kept      = 0
        log       = []

        for i, (old_label, cid) in enumerate(junk):
            print(f"  [{i+1}/{len(junk)}] \"{old_label}\"", end="", flush=True)

            # Get sample facts for this concept
            facts_result = session.run(
                "MATCH (f:Fact)-[:DESCRIBES]->(c:Concept {label: $lbl}) "
                "RETURN f.claim AS claim LIMIT 5",
                lbl=old_label
            )
            facts_sample = [r["claim"] for r in facts_result if r["claim"]]

            if not facts_sample:
                # No facts — delete the concept node entirely
                print(f" → DELETED (no facts)")
                session.run(
                    "MATCH (c:Concept {label: $lbl}) DETACH DELETE c",
                    lbl=old_label
                )
                filtered += 1
                log.append({"old": old_label, "new": None, "action": "deleted_no_facts"})
                continue

            # Ask LLM for clean label
            new_label = clean_label_with_llm(client, old_label, facts_sample)

            if new_label is None:
                # Too vague — delete concept and its facts
                print(f" → FILTERED OUT (too vague)")
                session.run(
                    "MATCH (c:Concept {label: $lbl}) "
                    "OPTIONAL MATCH (f:Fact)-[:DESCRIBES]->(c) "
                    "DETACH DELETE c, f",
                    lbl=old_label
                )
                filtered += 1
                log.append({"old": old_label, "new": None, "action": "filtered_vague"})

            elif new_label == old_label:
                print(f" → KEPT (unchanged)")
                kept += 1
                log.append({"old": old_label, "new": old_label, "action": "kept"})

            else:
                print(f" → \"{new_label}\"")

                # Update concept label in Neo4j
                session.run(
                    "MATCH (c:Concept {label: $old}) SET c.label = $new",
                    old=old_label, new=new_label
                )

                # Regenerate negations for all facts under this concept
                # (old negations were based on junk label context)
                facts_to_regen = session.run(
                    "MATCH (f:Fact)-[:DESCRIBES]->(c:Concept {label: $lbl}) "
                    "WHERE f.is_negation = false "
                    "RETURN f.fact_id AS fid, f.claim AS claim",
                    lbl=new_label
                )
                regen_count = 0
                for fr in facts_to_regen:
                    if fr["claim"]:
                        new_neg = auto_generate_negation(fr["claim"])
                        session.run(
                            "MATCH (f:Fact {fact_id: $fid}) SET f.negation = $neg",
                            fid=fr["fid"], neg=new_neg
                        )
                        regen_count += 1

                print(f"      ↳ regenerated {regen_count} negations")
                updated += 1
                log.append({
                    "old": old_label, "new": new_label,
                    "action": "updated", "negations_regenerated": regen_count
                })

            # Rate limit — avoid hammering Anthropic API
            time.sleep(0.3)

        # ── 5. Summary ────────────────────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"  NORMALIZATION COMPLETE")
        print(f"  Labels updated:  {updated}")
        print(f"  Labels filtered: {filtered}  (deleted from KG)")
        print(f"  Labels kept:     {kept}  (LLM confirmed as acceptable)")
        print(f"{'='*60}")

        # Save log
        log_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "eval", "results", "kg_normalization_log.json"
        )
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w") as f:
            json.dump({
                "course": course_id or "ALL",
                "total_junk": len(junk),
                "updated": updated,
                "filtered": filtered,
                "kept": kept,
                "changes": log
            }, f, indent=2)
        print(f"\n  Log saved: {log_path}")

        print(f"""
  NEXT STEPS:
  1. Rebuild ChromaDB (required after label changes):
     python run_ingestion.py --rebuild-index --course CSE1321
     python run_ingestion.py --rebuild-index --course CSE1300
     python run_ingestion.py --rebuild-index --course MATH1112

  2. Re-run evals:
     python eval/eval_guard2_hallucination.py
     python eval/eval_guard1_boundary.py
     python eval/eval_rag.py
     python eval/eval_ab_hallucination.py
     python eval/eval_llm_judge.py
     python eval/visualize_results.py
""")

    driver.close()


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Normalize junk KG concept labels to improve Guard #1 catch rate"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--course",  type=str,
                       help="Course ID to normalize (e.g. CSE1321)")
    group.add_argument("--all",     action="store_true",
                       help="Normalize all courses")

    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without applying them")
    parser.add_argument("--neo4j-password", type=str,
                        help="Neo4j password (default: reads NEO4J_PASSWORD env var)")

    args = parser.parse_args()

    # Password override
    if args.neo4j_password:
        NEO4J_PASSWORD = args.neo4j_password
    elif os.environ.get("NEO4J_PASSWORD"):
        NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]

    # Parley API key is hardcoded — no env var needed

    course = args.course if not args.all else None
    run_normalization(course, args.dry_run)
