# LexEval Full Pipeline Test Plan

## Purpose

Validate the complete RRD-compliant LexEval pipeline end-to-end using three benchmark
legal cases. Each run exercises every stage: PDF ingestion, response-conditioned rubric
construction (with recursive decomposition), comparison-response generation, and analysis
with three weighting modes.

## Benchmark Cases and Questions

### Case 1: Anglemire v. Policemen's Benevolent Ass'n of Chicago

- **PDF**: `documents/_Anglemire v Policemens Benev Assn of Chicago_Marriage.pdf`
- **Testing focus**: Decomposition quality and beneficiary/marriage-related issue separation.
- **Question**: Under the Illinois statute of frauds, was the insured's oral promise to name the plaintiff as beneficiary in his benefit association certificate, made in consideration of marriage, enforceable after the marriage was performed? Analyze whether the subsequent marriage and the insured's act of changing the beneficiary constituted part performance sufficient to remove the agreement from the statute of frauds, and whether the insured was estopped from later changing the beneficiary to other parties.

### Case 2: Demeritt v. Bickford

- **PDF**: `documents/_Demeritt v Bickford_Surety.pdf`
- **Testing focus**: Surety/indemnity reasoning and whether refinement reduces overlapping criteria.
- **Question**: Was the defendant's oral promise to indemnify the plaintiff for becoming surety on a note to a third party -- where the plaintiff acted solely in reliance on the defendant's promise -- an original undertaking outside the statute of frauds, or a collateral promise to answer for the debt of another that required a writing to be enforceable?

### Case 3: Westside Wrecker Service, Inc. v. Skafi

- **PDF**: `documents/_Westside Wrecker Service Inc v Skafi_OneYear.pdf`
- **Testing focus**: One-year/statute-of-frauds reasoning and ranking stability under weighting changes.
- **Question**: Was the oral agreement between Westside and the subcontractor towing companies, which was intended to run for the five-year term of a government towing contract, barred by the one-year provision of the Texas statute of frauds even though the agreement could have been terminated early by the city's cancellation of the program? Additionally, was the evidence legally sufficient to establish that the parties had formed a partnership under the Texas Revised Partnership Act, considering the totality of the statutory factors?

## Comparison Models (5-model fixed benchmark pool)

| Model ID | Provider | Selection rationale |
| ---------------------------- | --------- | ---------------------------- |
| `Qwen/Qwen3-235B-A22B-Instruct-2507-tput` | Alibaba | Strong large-model baseline |
| `openai/gpt-oss-120b` | OpenAI | High-capacity open model |
| `openai/gpt-oss-20b` | OpenAI | Efficient smaller open model |
| `LiquidAI/LFM2-24B-A2B` | LiquidAI | Cost-efficient baseline |
| `meta-llama/Meta-Llama-3-8B-Instruct-Lite` | Meta | Compact instruction-following baseline |

These do not overlap with setup models or the control/judge model, satisfying the exclusion rule.

## Pipeline Stages Per Case

### Stage 1: PDF Ingestion

- Extract case text from the PDF using pdfplumber.
- Store as a string; no database persistence required for the test.

### Stage 2: RRD Rubric Construction

Calls `rubric_service.build_rubric_for_evaluation()`:

1. Setup response generation: 4 setup models x 25 = 100 responses.
2. Fixed k=8 clustering: embed 100 responses, k-means k=8, extract 8 centroid texts.
3. Initial rubric proposal: DeepSeek V3 proposes criteria conditioned on question + 8 centroids.
4. Recursive decompose-filter loop:
   - Breadth check: decompose criteria matching >2 of 8 centroids.
   - Misalignment filter on each child criterion.
   - Redundancy filter against accepted criteria.
   - Stop when rejected proposals >= 15 or no broad criteria remain.
5. Output: frozen rubric with criteria, decomposition_tree, refinement_passes, stopping_metadata, conditioning_sample.

Estimated API calls: ~180-210 per case.

### Stage 3: Comparison Response Generation

- 5 models x 40 = 200 responses per case.
- Uses the same async generation logic as the production pipeline.

Estimated API calls: 200 per case.

### Stage 4: Analysis

Calls `analysis_service.run_analysis()`:

1. Embed and cluster 200 responses (data-adaptive k via silhouette score).
2. Score centroids against frozen rubric using DeepSeek V3 (per-criterion scores).
3. Apply three weighting modes: uniform, heuristic, whitened_uniform.
4. Rank models by share in winning cluster under each mode.

Estimated API calls: ~5-15 per case.

### Stage 5: Output and Verification

Write a JSON artifact per case to `tests/fullpipeline/results/` containing:
- case_name, question
- rubric (criteria, decomposition_tree, refinement_passes, stopping_metadata, conditioning_sample)
- analysis (k, clusters, scores, winning_cluster, model_shares, baseline_scores, weighting_comparison)

## Cost and Time

| Item                   | Per case     | 3 cases total    |
| ---------------------- | ------------ | ---------------- |
| Setup responses (100)  | ~100         | ~300             |
| Rubric refinement      | ~20-50       | ~60-150          |
| Comparison responses   | ~200         | ~600             |
| Centroid scoring       | ~5-15        | ~15-45           |
| **Total API calls**    | **~385-425** | **~1,155-1,275** |

Wall-clock time: 30-90 minutes per case with 8-way concurrency.

## Verification Checklist Per Case

### Rubric Construction
- [ ] 100 setup responses generated (or reasonable count after failures).
- [ ] 8 centroid texts extracted from fixed k=8 clustering.
- [ ] Initial rubric proposed with valid criteria (id, name, description, weight).
- [ ] At least one refinement pass executed.
- [ ] stopping_metadata.reason is convergence, rejection_threshold_reached, or max_passes_reached.
- [ ] decomposition_tree is non-empty (expected but not guaranteed).
- [ ] Final criteria weights sum to 1.0.

### Case-Specific Checks
- **Anglemire**: Rubric should contain separable criteria for statute of frauds, part performance, and estoppel.
- **Demeritt**: Final rubric should not have duplicate criteria covering "original vs. collateral undertaking".
- **Westside**: Compare model rankings across three weighting modes; record whether top-ranked model changes.

### Analysis
- [ ] Clustering produced k >= 2 clusters.
- [ ] All centroids scored with per-criterion breakdowns.
- [ ] weighting_comparison contains all three modes.
- [ ] Each mode produces winning_cluster and model_shares.
- [ ] JSON artifact written and parseable.

## Files

| File               | Purpose                                          |
| ------------------ | ------------------------------------------------ |
| `pipeline-plan.md` | This plan document                               |
| `run_benchmark.py` | Main async script                                |
| `conftest.py`      | PDF paths, questions, model list as shared config |
| `results/`         | Output folder for JSON artifacts (gitignored)    |
