# LexEval - LLM Legal Reasoning Evaluation Platform

LexEval is a research platform for evaluating how large language models perform on legal reasoning tasks. The current implementation combines three connected layers:

- Frank source-grounding, controller-card, and variation workflow
- RRD core rubric construction
- Dasha downstream clustering, scoring overlays, judge panels, and escalation logic

The RRD paper source is `documents/Rubric Paper.pdf`. Frank source materials live under `documents/FrankInstructions/`. The application serves its API under `/api/v1`.

---

## 1. Introduction and Scope

LexEval is an LLM legal reasoning evaluation research platform. It evaluates legal-answer quality by separating source-grounded benchmark construction from downstream model comparison.

The implemented workflow is intentionally layered:

- Frank / controller-card layer: source screening, extraction, B-series routing, gold-answer generation, controller-card creation, human review, and optional variation selection
- RRD core workflow: setup responses, fixed-k conditioning centroids, response-conditioned rubric proposal, recursive decompose-filter loop, and frozen rubric
- Dasha downstream workflow: comparison responses, adaptive clustering, centroid composition, scoring overlays, citation verification, judge panels, and Zak escalation

Clustering is part of the product-layer evaluation workflow, not the paper-faithful rubric-construction method. The rubric must be frozen before downstream comparison begins.

---

## 2. End-to-End Pipeline

### Stage 1 - Legal case ingestion

1. The user uploads a legal case PDF through `POST /api/v1/cases`.
2. `pdfplumber` extracts the full text.
3. The case text is stored alongside the user's legal question.

If a rubric is built without case text, the Frank pipeline is skipped and the system falls back to the question-only RRD path.

### Stage 2 - Frank pre-RRD grounding and review gate

Frank runs before the RRD loop when source text is available.

#### 2.1 Source intake screening

The source is screened with a 17-item intake checklist plus `stop_triggered`. The screening result is persisted in `screening_result`.

#### 2.2 Source extraction

The source is transformed into an 18-key structured extraction object, including:

- doctrine-family signals
- black-letter rule and trigger facts
- best-supported answer path
- source boundaries and non-decisions
- `canonical_source_case_name`
- `canonical_source_case_citation`
- `source_case_monitoring_relevant`

This artifact is persisted in `source_extraction`.

#### 2.3 B-series doctrine-pack routing

The extracted source is routed to one of six Statute of Frauds packs:

- `pack_marriage`
- `pack_suretyship`
- `pack_one_year`
- `pack_land`
- `pack_ucc_2201`
- `pack_executor`

Routing uses the B-series classification gates and can perform a second confusion-set routing pass when confidence is low. Routing metadata records:

- `selected_pack`
- `secondary_issues`
- `secondary_candidate_packs`
- `governing_law_candidate`
- `main_gate_order`
- `confidence`
- `routing_status`

Valid routing statuses are:

- `stable`
- `multiple_plausible`
- `unstable`

#### 2.4 Question validation

The question-writing checklist runs as an informational pass and stores its output in `question_analysis`. This step does not block the pipeline.

#### 2.5 Gold packet mapping and failure modes

For routed packs, LexEval generates:

- a gold packet mapping
- pack-specific predicted failure modes

These are stored in `gold_packet_mapping` and `predicted_failure_modes`.

#### 2.6 Gold answer and locked controller card

Frank then generates:

- a weak reference answer
- a clean benchmark gold answer
- a 36-field locked controller card

The controller card is the downstream contract for rubric drafting and evaluation. It includes pack identity, base-question metadata, variation defaults, and citation-verification mode.

Controller-card data is persisted in:

- `controller_card`
- `controller_card_version`
- `workflow_source_case_name`
- `workflow_source_case_citation`
- `case_citation_verification_mode`

#### 2.7 Self-audit and mandatory pause

Frank runs self-audit and then pauses with:

- `fi_status = "awaiting_review"`

At this point the rubric is not frozen. The platform saves the intermediate Frank artifacts and waits for human action.

#### 2.8 Human review and variation gate

Reviewer actions:

- `approve`
- `reject`
- `reroute`

Approval advances the rubric into:

- `fi_status = "variation_pending"`

From there, the reviewer can:

- skip variation and proceed with the base question
- generate a variation menu
- select a lane-coded variation

Implemented lane codes:

- `A1` variable swap
- `A2` threshold-preserving numeric shift
- `A3` specificity shift
- `A4` non-controlling salience injection
- `B1` fact omission / ambiguity test
- `B2` controlled generalization

If a lane is selected, the rubric may enter `dual_rubric_mode`, persist `variation_question`, and later produce `variation_criteria`.

#### 2.9 Question generation utility

Reverse-engineered question generation exists as an on-demand route:

- `POST /api/v1/rubrics/{rubric_id}/generate-question`

It is available as a utility and persisted in `generated_question`. It is not currently a mandatory automated step in the main rubric-build path.

### Stage 3 - RRD setup-response generation

After Frank review completes, or immediately on the question-only path, the RRD setup stage begins.

LexEval generates 100 setup responses:

- 4 internal setup models
- 25 responses per setup model
- total 100 setup responses

Concurrency is controlled by a semaphore:

- `_CONCURRENCY_LIMIT = 4`

Setup-model output is persisted for provenance in `setup_responses`.

Internal setup models:

| Model ID | Provider | Role |
|---|---|---|
| `deepseek-ai/DeepSeek-V3` | DeepSeek | Control / setup |
| `deepseek-ai/DeepSeek-R1` | DeepSeek | Setup / strong reference on non-FI path |
| `Qwen/Qwen2.5-7B-Instruct-Turbo` | Alibaba | Setup / weak reference |
| `meta-llama/Llama-3.3-70B-Instruct-Turbo` | Meta | Setup |

On the Frank path:

- the Frank gold answer becomes the strong reference used in the refinement loop
- setup responses are generated only after review completes

### Stage 4 - RRD conditioning sample: fixed k=8 centroids

The 100 setup responses are embedded with `sentence-transformers` using `all-mpnet-base-v2`.

LexEval then clusters the setup responses with fixed:

- `k = 8`

The representative response with highest cosine similarity to each cluster centroid is selected. These 8 texts become the conditioning sample for the initial rubric proposal.

Persisted artifact:

- `conditioning_sample`

### Stage 5 - Response-conditioned initial rubric proposal

The control model proposes an initial rubric conditioned on:

- the legal question
- the 8 centroid conditioning responses
- doctrine-pack context when available

Each criterion is normalized into the schema:

- `id`
- `name`
- `description`
- `weight`
- `module_id` when module structure is available

Weights are normalized to sum to 1.0 after proposal generation.

### Stage 6 - Recursive decompose-filter loop

This is the core RRD refinement mechanism.

#### Breadth trigger

A criterion is considered too broad when it passes more than 2 of the 8 centroid texts:

- `_BREADTH_THRESHOLD = 2`

Such criteria are decomposed into narrower children.

#### Depth limit

Only one level of decomposition is allowed:

- `_MAX_DECOMPOSITION_DEPTH = 1`

Children are never recursively decomposed again.

#### Misalignment filter

A child criterion is rejected as misaligned only when it passes the weak reference and fails the strong reference.

On the Frank path, the strong reference is the approved Frank gold answer.

#### Redundancy filter

Each surviving child is checked against already accepted criteria and removed if redundant.

#### Stopping rule

The loop stops when any of the following occur:

- accumulated rejected proposals reaches 5
- no broad criteria remain
- 20 passes are reached

Current implemented thresholds:

- `_MAX_REJECTED_PROPOSALS = 5`
- hard pass cap = 20

Persisted refinement artifacts:

- `criteria`
- `decomposition_tree`
- `refinement_passes`
- `stopping_metadata`
- `strong_reference_text`
- `weak_reference_text`

### Stage 7 - Weight assignment, Karthic enrichment, and optional variation rubric

After refinement, LexEval computes final criterion weights with whitened-uniform weighting.

Let $m$ be the number of accepted criteria and $n = 8$ be the number of conditioning centroids. If $M \in \{0,1\}^{n \times m}$ is the binary score matrix, then:

$$
\Sigma = \mathrm{Cov}(M) + \varepsilon I, \quad \varepsilon = 10^{-6}
$$

and the whitened-uniform vector is:

$$
w_{\mathrm{WU}} = \Sigma^{-1/2} \cdot \mathbf{1}_m \; / \; \| \Sigma^{-1/2} \cdot \mathbf{1}_m \|_1
$$

Negative components are clipped to zero before renormalization. Equal weighting is used as a fallback on numerical failure.

When `module_id` values are present, LexEval blends module priors with WU weights:

- `0.3 x module_prior + 0.7 x wu_weight`

Module priors are:

- M1: 28%
- M2: 40%
- M3: 19%
- M4: 13%

#### Karthic row-card enrichment

After the RRD loop, LexEval enriches criteria with Karthic row-card fields such as:

- `row_code`
- `na_guidance`
- `golden_target_summary`
- `golden_contains`
- `allowed_omissions`
- `contradiction_flags`
- `comparison_guidance`
- `scoring_anchors`
- `primary_failure_labels`
- `row_status`

An overlap audit then checks distinctness among enriched criteria.

#### Optional variation rubric

When a reviewer selects a lane and `dual_rubric_mode` is enabled, LexEval can generate:

- `variation_question`
- `variation_criteria`

The base rubric remains in `criteria`. The variation rubric is stored separately in `variation_criteria`.

### Stage 8 - Comparison response generation

The user creates an evaluation from a frozen rubric and chooses 2 to 5 comparison-pool models.

For each selected model, LexEval generates:

- 40 base responses per model

When `variation_question` is present, LexEval also generates:

- 40 variation responses per model

Each response row stores:

- `question_version = "base"` or `"variation"`

Current concurrency settings:

- `_RESPONSES_PER_MODEL = 40`
- `_CONCURRENCY_LIMIT = 25`

### Stage 9 - Analysis: clustering, scoring, overlays, and panels

The analysis workflow consumes a frozen rubric and completed model responses.

#### 9.1 Base-track clustering

Base responses are embedded and clustered with adaptive silhouette-score selection.

Lower bound for the adaptive sweep:

$$
k_{\min} = \max(\lfloor n_{\text{models}} \times 1.5 \rfloor, 4)
$$

Each cluster records:

- centroid response text
- response indices
- model counts
- centroid composition summary

#### 9.2 Centroid scoring

Each centroid is scored against the frozen rubric criteria. LexEval stores:

- `baseline_scores`
- `scores`
- `weighting_comparison`
- `winning_cluster`
- `model_shares`

Three weighting views are computed:

- `uniform`
- `heuristic`
- `whitened_uniform`

The primary ranking remains the heuristic track.

#### 9.3 FI and Module 0 tags

When a rubric has a doctrine pack, centroid scoring also returns:

- `failure_tags`
- `metadata_tags`

Module 0 metadata covers:

- bottom-line outcome
- outcome correctness
- reasoning alignment
- jurisdiction assumption
- controlling doctrine named

#### 9.4 Dasha composition and overlays

LexEval computes full centroid-composition blocks and stores:

- `centroid_composition`

It then applies Dasha overlay logic:

- optional case-citation verification
- penalty codes
- cap codes
- `final_scores`

Additional persisted outputs include:

- `penalties_applied`
- `cap_status`
- `case_citation_metadata`

#### 9.5 Dual-track analysis

When `dual_rubric_mode` is active and variation responses exist, LexEval loads base and variation responses separately by `question_version`.

The variation track can be clustered independently and is stored in:

- `variation_scores`

If variation responses are unavailable, analysis falls back to rescoring base centroids against the variation rubric.

#### 9.6 Judge panels and Zak escalation

`POST /api/v1/analysis/{evaluation_id}/run` accepts optional:

- `judge_models`

Judge models must come from the internal judge allowlist. When multiple judges are selected, LexEval stores:

- `judge_panel`
- `judge_votes`

If no centroid receives a strict majority of first-place votes, LexEval raises:

- `zak_review_flag`

### Stage 10 - Ranking

Ranking remains anchored to LexEval's original downstream rule:

- identify the winning cluster under the primary heuristic track
- rank models by their share inside that winning cluster

Dasha `final_scores`, penalties, caps, and dual-track outputs are reported in parallel. They do not replace the primary ranking rule.

---

## 3. Control Model Policy

The primary control model is:

- `deepseek-ai/DeepSeek-V3`

This model is used for:

- rubric proposal and refinement
- centroid scoring
- default single-judge analysis when no judge panel is provided

The paper-faithful methodological requirement is the recursive refinement process itself, not the specific model identity.

---

## 4. Prompt Contract

Prompt builders live in two files:

- `backend/app/services/rubric_prompts.py`
- `backend/app/services/dasha_prompts.py`

### RRD + Frank + Karthic prompt builders

| Function | Purpose |
|---|---|
| `build_setup_system_prompt` | Setup-response system prompt |
| `build_initial_proposal_messages` | Response-conditioned initial rubric proposal |
| `build_decompose_messages` | Criterion decomposition |
| `build_binary_eval_messages` | Binary pass/fail criterion scoring |
| `build_filter_redundancy_messages` | Redundancy detection |
| `build_source_intake_screening_messages` | 17-item source intake screening |
| `build_source_extraction_messages` | 18-key source extraction |
| `build_routing_messages` | Six-pack B-series routing |
| `build_locked_controller_card_messages` | Step 2A locked controller card |
| `build_gold_packet_mapping_messages` | Gold packet mapping |
| `build_failure_mode_prediction_messages` | Pack-specific failure-mode prediction |
| `build_gold_answer_messages` | Clean benchmark gold-answer generation |
| `build_self_audit_messages` | Frank self-audit |
| `build_question_validation_messages` | Question-writing checklist |
| `build_question_generation_messages` | Reverse-engineered question generation |
| `build_karthic_row_card_messages` | Karthic row-card enrichment |
| `build_overlap_audit_messages` | Karthic overlap audit |
| `build_variation_rubric_messages` | Lane-sensitive variation rubric |
| `build_variation_menu_messages` | Variation menu generation |
| `build_selected_variation_messages` | Selected-lane variation package |
| `build_draft_comparison_messages` | Draft-versus-source comparison utility |

### Dasha prompt builders

| Function | Purpose |
|---|---|
| `build_metadata_tags_messages` | Structured Module 0 metadata extraction |
| `build_case_citation_verification_messages` | Citation verification and hallucination classification |
| `build_scoring_overlay_messages` | Penalty and cap application |

Centroid scoring schema itself is defined inline in `backend/app/services/analysis_service.py`.

---

## Tech Stack

### Backend

| Layer | Technology |
|---|---|
| API framework | FastAPI |
| ORM | SQLAlchemy 2.0 async |
| Database | PostgreSQL + asyncpg |
| Migrations | Alembic |
| PDF extraction | pdfplumber |
| Embeddings | sentence-transformers (`all-mpnet-base-v2`) |
| Clustering | scikit-learn k-means + silhouette scoring |
| LLM API | Together AI API |
| Async HTTP | httpx |
| Background jobs | FastAPI BackgroundTasks |
| Auth | JWT with python-jose and passlib bcrypt |
| Validation | Pydantic v2 |
| Linting and formatting | Ruff |
| Testing | pytest + pytest-asyncio + httpx |

### Frontend

| Layer | Technology |
|---|---|
| Framework | React 18 + TypeScript + Vite |
| Styling | Tailwind CSS + shadcn/ui |
| Routing | React Router v6 |
| Auth state | Zustand |
| Server state | TanStack Query |
| Tables | TanStack Table |
| Charts | Recharts |
| Icons | lucide-react |
| Notifications | Sonner |
| Internationalization | react-i18next + i18next |
| Themes | next-themes with CSS variables |
| Linting and formatting | ESLint + Prettier |
| Testing | Vitest + React Testing Library + MSW |
| E2E | Playwright |

---

## Repository Layout

```text
llms-legal-evals/
|-- app-venv/
|-- requirements.txt
|-- pyproject.toml
|-- alembic.ini
|-- Procfile
|-- .env.example
|-- documents/
|   |-- Rubric Paper.pdf
|   |-- FrankInstructions/
|   `-- *.pdf
|-- backend/
|   |-- alembic/               # Database migrations (6 revisions)
|   |-- app/
|   |   |-- api/routes/
|   |   |-- core/
|   |   |-- db/
|   |   |-- models/
|   |   |-- repositories/
|   |   |-- schemas/
|   |   `-- services/          # rubric_service, frank_service, response_service,
|   |                          # analysis_service, rubric_prompts, dasha_prompts
|   `-- tests/
|-- frontend/
|   |-- src/
|   |   |-- components/
|   |   |-- config/
|   |   |-- hooks/
|   |   |-- lib/
|   |   |-- locales/
|   |   |-- pages/
|   |   |-- services/
|   |   |-- stores/
|   |   `-- types/
|   `-- tests/
`-- tests/
        |-- e2e/
        |-- fullpipeline/
        `-- prefilterllms/
```

---

## Model Roles

### Internal rubric, audit, and judge models

These models are used for setup responses, refinement, or judging and are excluded from the comparison pool.

| Role | Model ID |
|---|---|
| Control model | `deepseek-ai/DeepSeek-V3` |
| Strong reference (non-FI path) | `deepseek-ai/DeepSeek-R1` |
| Weak reference | `Qwen/Qwen2.5-7B-Instruct-Turbo` |
| Setup model | `deepseek-ai/DeepSeek-V3` |
| Setup model | `deepseek-ai/DeepSeek-R1` |
| Setup model | `Qwen/Qwen2.5-7B-Instruct-Turbo` |
| Setup model | `meta-llama/Llama-3.3-70B-Instruct-Turbo` |

Judge-panel allowlist:

- `deepseek-ai/DeepSeek-V3`
- `deepseek-ai/DeepSeek-R1`
- `Qwen/Qwen2.5-7B-Instruct-Turbo`
- `meta-llama/Llama-3.3-70B-Instruct-Turbo`

The frontend currently allows up to 3 selected judge models per analysis run.

### User-facing comparison pool

Users select 2 to 5 models from this pool for response generation.

| Model ID | Name | Provider |
|---|---|---|
| `LiquidAI/LFM2-24B-A2B` | LFM2 24B | LiquidAI |
| `openai/gpt-oss-20b` | GPT OSS 20B | OpenAI |
| `arize-ai/qwen-2-1.5b-instruct` | Qwen 2 1.5B | Arize/Alibaba |
| `meta-llama/Meta-Llama-3-8B-Instruct-Lite` | Llama 3 8B Lite | Meta |
| `essentialai/rnj-1-instruct` | RNJ-1 | EssentialAI |
| `openai/gpt-oss-120b` | GPT OSS 120B | OpenAI |
| `Qwen/Qwen3-235B-A22B-Instruct-2507-tput` | Qwen3 235B | Alibaba |
| `MiniMaxAI/MiniMax-M2.5` | MiniMax M2.5 | MiniMaxAI |
| `deepseek-ai/DeepSeek-V3.1` | DeepSeek V3.1 | DeepSeek |
| `Qwen/Qwen3.5-397B-A17B` | Qwen3.5 397B | Alibaba |
| `zai-org/GLM-5` | GLM-5 | ZhipuAI |
| `deepcogito/cogito-v2-1-671b` | Cogito V2.1 671B | DeepCogito |
| `MiniMaxAI/MiniMax-M2.7` | MiniMax M2.7 | MiniMaxAI |
| `zai-org/GLM-5.1` | GLM-5.1 | ZhipuAI |

All model calls are made through Together AI.

---

## API Endpoints

All endpoints are mounted under `/api/v1`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/auth/register` | Register and return JWT |
| `POST` | `/auth/login` | Login and return JWT |
| `GET` | `/auth/me` | Current user |
| `GET` | `/dashboard/stats` | Dashboard summary |
| `POST` | `/cases` | Upload legal case PDF |
| `GET` | `/cases` | List cases |
| `GET` | `/cases/{case_id}` | Get case detail |
| `POST` | `/rubrics` | Start standalone rubric build |
| `GET` | `/rubrics` | List rubrics |
| `GET` | `/rubrics/frozen` | List frozen rubrics |
| `GET` | `/rubrics/evaluation/{evaluation_id}` | Get rubric for evaluation |
| `GET` | `/rubrics/{rubric_id}` | Rubric detail |
| `GET` | `/rubrics/{rubric_id}/logs` | Rubric-build logs |
| `POST` | `/rubrics/{rubric_id}/stop` | Stop running rubric build |
| `POST` | `/rubrics/{rubric_id}/rerun` | Re-run failed rubric build |
| `POST` | `/rubrics/{rubric_id}/approve` | Approve, reject, or reroute Frank review |
| `POST` | `/rubrics/{rubric_id}/variation-menu` | Generate variation menu |
| `POST` | `/rubrics/{rubric_id}/select-variation` | Select lane or skip variation |
| `POST` | `/rubrics/{rubric_id}/validate-question` | Run question validation |
| `POST` | `/rubrics/{rubric_id}/generate-question` | Generate reverse-engineered question |
| `POST` | `/rubrics/{rubric_id}/extract-only` | Mode A: source screening and extraction |
| `POST` | `/rubrics/{rubric_id}/compare-draft` | Mode C: compare draft to source |
| `POST` | `/rubrics/{rubric_id}/draft-failure-modes` | Mode E: predict failure modes |
| `GET` | `/evaluations/models` | List comparison-pool models |
| `POST` | `/evaluations` | Create evaluation |
| `GET` | `/evaluations` | List evaluations |
| `GET` | `/evaluations/{evaluation_id}` | Evaluation detail |
| `GET` | `/evaluations/{evaluation_id}/responses` | List generated responses, including `question_version` |
| `GET` | `/evaluations/{evaluation_id}/logs` | Response-generation logs |
| `POST` | `/evaluations/{evaluation_id}/stop` | Stop running evaluation |
| `POST` | `/evaluations/{evaluation_id}/rerun` | Re-run evaluation |
| `POST` | `/analysis/{evaluation_id}/run` | Run clustering and analysis |
| `GET` | `/analysis/{evaluation_id}/status` | Analysis status |
| `GET` | `/analysis/{evaluation_id}/logs` | Analysis logs |
| `GET` | `/analysis/{evaluation_id}` | Analysis results |

`POST /analysis/{evaluation_id}/run` accepts an optional JSON body:

```json
{
    "judge_models": [
        "deepseek-ai/DeepSeek-V3",
        "deepseek-ai/DeepSeek-R1"
    ]
}
```

---

## Persisted Research Artifacts

### Rubrics

Core RRD artifacts:

- `criteria`
- `decomposition_tree`
- `refinement_passes`
- `stopping_metadata`
- `conditioning_sample`
- `setup_responses`
- `strong_reference_text`
- `weak_reference_text`
- `is_frozen`

Frank and controller-card artifacts:

- `fi_status`
- `fi_stream_id`
- `review_notes`
- `screening_result`
- `source_extraction`
- `routing_metadata`
- `doctrine_pack`
- `gold_packet_mapping`
- `predicted_failure_modes`
- `gold_answer`
- `generated_question`
- `self_audit_result`
- `question_analysis`
- `controller_card`
- `controller_card_version`
- `workflow_source_case_name`
- `workflow_source_case_citation`
- `case_citation_verification_mode`

Variation and dual-rubric artifacts:

- `selected_lane_code`
- `dual_rubric_mode`
- `base_question`
- `base_gold_answer`
- `variation_question`
- `variation_criteria`

Karthic enrichment is stored directly inside `criteria` and `variation_criteria` when present.

### Model responses

Response rows persist:

- `model_name`
- `response_text`
- `run_index`
- `question_version`

### Analyses

Analysis records persist:

- `k`
- `clusters`
- `centroid_indices`
- `scores`
- `winning_cluster`
- `model_shares`
- `weighting_mode`
- `baseline_scores`
- `weighting_comparison`
- `silhouette_scores_by_k`
- `failure_tags`
- `centroid_composition`
- `penalties_applied`
- `cap_status`
- `final_scores`
- `case_citation_metadata`
- `judge_panel`
- `judge_votes`
- `zak_review_flag`
- `variation_scores`

---

## Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 15+
- Together AI API key

### Backend

```bash
# 1. Activate virtual environment
app-venv\Scripts\activate
# or
source app-venv/bin/activate

# 2. Copy and configure environment
cp .env.example .env
# Set required environment variables locally without committing any secret values.

# 3. Create the database
createdb lexeval

# 4. Run migrations from the repository root
alembic upgrade head

# 5. Start the API
cd backend
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs at `http://localhost:5173`.

### Deployment note

Deployments run Alembic automatically through the release hook in `Procfile`.

---

## Verification

Run the checks relevant to the area changed.

```bash
# Backend tests
app-venv/Scripts/python.exe -m pytest backend/tests/

# Frontend tests
cd frontend
npm test

# End-to-end tests
cd tests/e2e
npm test

# Full methodology benchmark
python -m tests.fullpipeline.run_benchmark
```

---

## Database Migrations

Current Alembic chain:

| Revision | Description |
|---|---|
| `be24afdd1cc7` | Initial schema |
| `0f1a2b3c4d5e` | RRD v2 schema and weighting columns |
| `a1b2c3d4e5f6` | Setup provenance and silhouette fields |
| `b2c3d4e5f6a7` | Standalone rubric support |
| `c3d4e5f6a7b8` | Frank pipeline columns and analysis `failure_tags` |
| `d4e5f6a7b8c9` | Controller card, variation, citation, Dasha analysis, and `question_version` |

---

## PostgreSQL Database Layout

The current migrations create application tables in the default `public` schema. No custom PostgreSQL schema names are defined by the app migrations.

Shared column contract:

- every application table includes `created_at timestamptz not null default now()`
- every application table includes `updated_at timestamptz not null default now()`
- primary keys use `uuid`

### `public.status_enum`

Used by `public.evaluations.status`.

| Value |
|---|
| `pending` |
| `rubric_building` |
| `rubric_frozen` |
| `running` |
| `done` |
| `failed` |

### `public.alembic_version`

Alembic-managed migration state table.

| Column | Type | Notes |
|---|---|---|
| `version_num` | `varchar(32)` | Current migration revision identifier |

### `public.users`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` | Primary key |
| `email` | `text` | Not null, unique, indexed |
| `hashed_password` | `text` | Not null |
| `created_at` | `timestamptz` | Not null, default `now()` |
| `updated_at` | `timestamptz` | Not null, default `now()` |

### `public.legal_cases`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` | Primary key |
| `title` | `text` | Not null |
| `filename` | `text` | Not null |
| `raw_text` | `text` | Nullable extracted source text |
| `created_at` | `timestamptz` | Not null, default `now()` |
| `updated_at` | `timestamptz` | Not null, default `now()` |

### `public.rubrics`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` | Primary key |
| `evaluation_id` | `uuid` | Nullable FK to `evaluations.id`, indexed, `ON DELETE SET NULL` |
| `case_id` | `uuid` | Nullable FK to `legal_cases.id`, indexed, `ON DELETE SET NULL` |
| `question` | `text` | Nullable |
| `status` | `text` | Not null, default `building` |
| `criteria` | `json` | Nullable frozen base rubric criteria |
| `raw_response` | `text` | Nullable raw proposal payload |
| `decomposition_tree` | `json` | Nullable refinement tree |
| `refinement_passes` | `json` | Nullable pass log |
| `stopping_metadata` | `json` | Nullable stopping details |
| `conditioning_sample` | `json` | Nullable fixed-k centroid texts |
| `is_frozen` | `boolean` | Not null, default `false` |
| `setup_responses` | `json` | Nullable setup provenance |
| `strong_reference_text` | `text` | Nullable |
| `weak_reference_text` | `text` | Nullable |
| `screening_result` | `json` | Nullable Frank intake screen |
| `source_extraction` | `json` | Nullable structured source extraction |
| `gold_packet_mapping` | `json` | Nullable doctrinal map |
| `doctrine_pack` | `text` | Nullable selected pack id |
| `routing_metadata` | `json` | Nullable routing details |
| `predicted_failure_modes` | `json` | Nullable failure-mode list |
| `gold_answer` | `text` | Nullable approved benchmark answer |
| `generated_question` | `text` | Nullable reverse-engineered question |
| `self_audit_result` | `json` | Nullable Frank audit output |
| `question_analysis` | `json` | Nullable question-checklist output |
| `fi_status` | `text` | Nullable Frank workflow state |
| `fi_stream_id` | `text` | Nullable SSE/log stream id |
| `review_notes` | `text` | Nullable reviewer notes |
| `controller_card` | `json` | Nullable locked controller card |
| `controller_card_version` | `text` | Nullable controller-card version |
| `selected_lane_code` | `text` | Nullable, indexed |
| `dual_rubric_mode` | `boolean` | Not null, default `false`, indexed |
| `base_question` | `text` | Nullable |
| `base_gold_answer` | `text` | Nullable |
| `variation_question` | `text` | Nullable |
| `variation_criteria` | `json` | Nullable variation rubric |
| `workflow_source_case_name` | `text` | Nullable |
| `workflow_source_case_citation` | `text` | Nullable |
| `case_citation_verification_mode` | `boolean` | Not null, default `false` |
| `created_at` | `timestamptz` | Not null, default `now()` |
| `updated_at` | `timestamptz` | Not null, default `now()` |

### `public.evaluations`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` | Primary key |
| `case_id` | `uuid` | Nullable FK to `legal_cases.id`, indexed, `ON DELETE SET NULL` |
| `rubric_id` | `uuid` | Nullable FK to `rubrics.id`, indexed, `ON DELETE SET NULL` |
| `question` | `text` | Not null |
| `model_names` | `json` | Nullable selected comparison models |
| `status` | `status_enum` | Not null, indexed |
| `created_at` | `timestamptz` | Not null, default `now()` |
| `updated_at` | `timestamptz` | Not null, default `now()` |

### `public.model_responses`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` | Primary key |
| `evaluation_id` | `uuid` | Not null FK to `evaluations.id`, indexed, `ON DELETE CASCADE` |
| `model_name` | `text` | Not null |
| `response_text` | `text` | Nullable |
| `run_index` | `integer` | Not null, default `0` |
| `question_version` | `text` | Not null, default `base` |
| `created_at` | `timestamptz` | Not null, default `now()` |
| `updated_at` | `timestamptz` | Not null, default `now()` |

### `public.analyses`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` | Primary key |
| `evaluation_id` | `uuid` | Not null FK to `evaluations.id`, indexed, `ON DELETE CASCADE` |
| `k` | `integer` | Not null selected cluster count |
| `clusters` | `json` | Nullable cluster membership data |
| `centroid_indices` | `json` | Nullable centroid index list |
| `scores` | `json` | Nullable primary heuristic scores |
| `winning_cluster` | `integer` | Nullable |
| `model_shares` | `json` | Nullable winning-cluster shares |
| `weighting_mode` | `text` | Nullable primary weighting label |
| `baseline_scores` | `json` | Nullable per-criterion scores |
| `weighting_comparison` | `json` | Nullable comparison across weighting strategies |
| `silhouette_scores_by_k` | `json` | Nullable adaptive-k diagnostics |
| `failure_tags` | `json` | Nullable Frank/Dasha failure tags |
| `centroid_composition` | `json` | Nullable centroid composition block |
| `penalties_applied` | `json` | Nullable Dasha penalties |
| `cap_status` | `json` | Nullable Dasha caps |
| `final_scores` | `json` | Nullable overlaid final scores |
| `case_citation_metadata` | `json` | Nullable citation verification output |
| `judge_panel` | `json` | Nullable selected judge metadata |
| `judge_votes` | `json` | Nullable per-judge results |
| `zak_review_flag` | `json` | Nullable Zak escalation metadata |
| `variation_scores` | `json` | Nullable dual-track / variation results |
| `created_at` | `timestamptz` | Not null, default `now()` |
| `updated_at` | `timestamptz` | Not null, default `now()` |

---

## Environment Variables

This README intentionally omits all real credential values, usernames, passwords, hosts, and token strings.

| Variable | Description |
|---|---|
| `DATABASE_URL` | Async PostgreSQL connection string supplied through the local environment or deployment secret store |
| `SECRET_KEY` | JWT signing secret |
| `ALGORITHM` | JWT algorithm, default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL in minutes |
| `TOGETHER_API_KEY` | Together AI API key |
| `REDIS_URL` | Reserved for future queueing / background extensions |

---

## Project Rules

- Keep backend business logic in services and repositories.
- Keep frontend user-visible text in locale JSON files.
- Do not use SQLModel.
- Do not use admin-template packages.
- Keep theme values in CSS variables and the frontend theme config.
- Add or update tests for new features and bug fixes.
- Keep comparison-pool models separate from setup, control, and judge models.

---

## Benchmark Cases

| File | Regression focus |
|---|---|
| `documents/_Anglemire v Policemens Benev Assn of Chicago_Marriage.pdf` | Marriage-issue separation |
| `documents/_Demeritt v Bickford_Surety.pdf` | Surety / collateral-promise reasoning |
| `documents/_Westside Wrecker Service Inc v Skafi_OneYear.pdf` | One-year provision reasoning and ranking stability |
