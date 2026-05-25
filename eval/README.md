# EduSHIELD Evaluation and Results Analysis Guide

This README is dedicated to evaluation workflows only.
It explains how to run each evaluation script, where outputs are stored, and how to interpret results for reporting.

## 1. Scope

The evaluation suite covers:

1. Guard A (Boundary Classification)
2. Guard B (Hallucination Detection)
3. RAG retrieval quality
4. LLM-as-judge response quality
5. A/B hallucination reduction
6. Manual hint review (human rating loop)
7. Figure generation for analysis and reporting

All outputs are written to:

- `eval/results/`
- `eval/results/figures/` (for plots)

## 2. Before You Run

From project root:

```bash
cd /Users/Desktop/EduSHIELD
```

Recommended checks:

1. Neo4j is running and reachable using config in `config.py`.
2. Chroma index exists at `data/chroma_index/`.
3. Environment variables/API keys are configured (OpenAI or Parley route).
4. Test CSVs exist:
   - `guard2_test_set.csv`
   - `rag_gold_pairs_v3.csv`
   - `hint_review_prompts.csv`

## 3. Suggested Execution Order

Run in this order so the downstream analysis has complete artifacts:

```bash
python3 eval/eval_guard1_boundary.py
python3 eval/eval_guard2_hallucination.py
python3 eval/eval_rag.py
python3 eval/eval_llm_judge.py
python3 eval/eval_ab_hallucination.py
python3 eval/visualize_results.py
```

Manual review is optional but recommended for publication claims:

```bash
python3 eval/eval_hint_manual.py --generate
# Rate rows in eval/results/hint_review_manual.csv
python3 eval/eval_hint_manual.py --score
```

## 4. Script-by-Script Reference

### 4.1 Guard A Boundary Evaluation

Script:

- `eval/eval_guard1_boundary.py`

Input:

- `guard2_test_set.csv` (question, label)

Primary outputs:

- `eval/results/guard1_boundary_results.csv`
- `eval/results/guard1_boundary_metrics.json`
- `eval/results/guard1_boundary_report.txt`

Key metrics to read:

1. `accuracy`
2. `f1_macro`
3. `recall_per_class.IN_DOMAIN`
4. `recall_per_class.OUT_OF_DOMAIN`
5. `confusion_matrix`
6. `confidence_intervals_95`

Interpretation notes:

- Macro-F1 is the best single summary across all three classes.
- IN_DOMAIN recall estimates how often legitimate course questions are accepted.
- OUT_OF_DOMAIN recall estimates how well off-topic requests are blocked.
- BOUNDARY is typically hardest and should be discussed explicitly in limitations.

### 4.2 Guard B Hallucination Evaluation

Script:

- `eval/eval_guard2_hallucination.py`

Primary outputs:

- `eval/results/guard2_hallucination_results.csv`
- `eval/results/guard2_hallucination_metrics.json`
- `eval/results/guard2_hallucination_report.txt`
- `eval/results/guard2_v3_spotcheck.json`

Key metrics to read:

1. `factscore`
2. `catch_rate`
3. `false_contradiction_rate`
4. `unverifiable_rate`
5. `verdict_breakdown`

Interpretation notes:

- High FActScore + low false contradiction means good precision on correct answers.
- Catch rate reflects detection coverage on injected wrong responses.
- If catch rate lags but FActScore is high, discuss precision-recall tradeoff.

### 4.3 RAG Retrieval Evaluation

Script:

- `eval/eval_rag.py`

Input:

- `rag_gold_pairs_v3.csv`

Primary outputs:

- `eval/results/rag_results.csv`
- `eval/results/rag_metrics.json`
- `eval/results/rag_report.txt`

Key metrics to read:

1. `recall_at_1`
2. `recall_at_3`
3. `recall_at_5`
4. `mrr`
5. `context_precision`
6. `faithfulness`
7. `per_module`
8. `misses`

Interpretation notes:

- Recall@5 and MRR are retrieval ranking quality anchors.
- `misses` list is highly actionable for ontology/synonym updates.
- Module-level recall helps prioritize ingestion and labeling cleanup.

### 4.4 LLM-as-Judge Quality Evaluation

Script:

- `eval/eval_llm_judge.py`

Input:

- `hint_review_prompts.csv`

Primary outputs:

- `eval/results/llm_judge_results.csv`
- `eval/results/llm_judge_metrics.json`
- `eval/results/llm_judge_report.txt`

Key metrics to read:

1. `avg_factual_accuracy`
2. `avg_pedagogical_quality`
3. `avg_course_grounding`
4. `avg_composite_score`
5. `distribution`
6. `per_type`

Interpretation notes:

- Composite score summarizes overall quality.
- Per-type breakdown helps identify weak question families.
- Track poor rate (<3) for risk monitoring over time.

### 4.5 A/B Hallucination Reduction

Script:

- `eval/eval_ab_hallucination.py`

Input:

- `hint_review_prompts.csv`

Primary outputs:

- `eval/results/ab_hallucination_results.csv`
- `eval/results/ab_hallucination_metrics.json`
- `eval/results/ab_hallucination_report.txt`

Key metrics to read:

1. `guard_on` vs `guard_off` verdict rates
2. `reduction_pct`
3. `responses_improved`

Interpretation notes:

- This isolates impact of grounding + guard pipeline.
- `reduction_pct` is the main A/B effectiveness claim.

### 4.6 Manual Hint Review (Human-in-the-loop)

Script:

- `eval/eval_hint_manual.py`

Two-phase flow:

1. Generate samples:

```bash
python3 eval/eval_hint_manual.py --generate
```

2. Open `eval/results/hint_review_manual.csv` and fill `your_rating` using:

- A = Appropriate
- G = Too Generic
- F = Factually Wrong

3. Score results:

```bash
python3 eval/eval_hint_manual.py --score
```

Primary metric:

- Error rate = (G + F) / rated

## 5. Figure Generation

Script:

- `eval/visualize_results.py`

Run:

```bash
python3 eval/visualize_results.py
```

Reads metrics JSON files and writes publication-ready charts to:

- `eval/results/figures/`

If a figure is missing, confirm the corresponding metrics JSON exists first.

## 6. Current Results Snapshot (from existing JSON files)

These values are from the current repo state and should be regenerated after any major code/data change.

1. Guard A boundary:
   - Accuracy: 0.7214
   - Macro-F1: 0.6166
   - IN_DOMAIN recall: 0.8022
2. Guard B hallucination:
   - FActScore: 0.9283 (target met)
   - Catch rate: 0.55 (target not met)
   - False contradiction rate: 0.05 (target met)
3. RAG retrieval:
   - Recall@5: 0.8462
   - MRR: 0.8141
   - Context precision: 0.8192
   - Faithfulness: 0.54
4. LLM-as-judge:
   - Composite score: 4.297 / 5.0
   - Poor rate: 2/50 = 4%
5. A/B hallucination reduction:
   - Reduction: 46.67%

## 7. Analysis Checklist for Reports/Papers

Use this checklist when writing the results section:

1. Report both central metrics and confidence intervals where available.
2. State which targets are met vs not met.
3. Compare against included baselines in JSON files.
4. Include at least one error analysis subsection:
   - boundary confusion (Guard A)
   - missed concept retrievals (RAG)
   - wrong-response misses (Guard B catch failures)
5. Separate automatic metrics from manual evaluation claims.
6. Add reproducibility details:
   - sample sizes
   - random seed usage
   - data files used

## 8. Common Failure Modes and Quick Checks

1. API connection errors:
   - Verify API keys and base URL config in `config.py`.
2. Empty or poor retrieval:
   - Rebuild ingestion/index and verify Chroma path.
3. Unexpectedly low boundary metrics:
   - Verify DomainConfig exists and course registry terms are populated.
4. Missing figures:
   - Ensure required metrics JSON files exist before running visualizer.

## 9. Minimal Re-run Command Set

For a fast refresh of all key outputs:

```bash
python3 eval/eval_guard1_boundary.py && \
python3 eval/eval_guard2_hallucination.py && \
python3 eval/eval_rag.py && \
python3 eval/eval_llm_judge.py && \
python3 eval/eval_ab_hallucination.py && \
python3 eval/visualize_results.py
```

This is the recommended command block before final result analysis or manuscript updates.
