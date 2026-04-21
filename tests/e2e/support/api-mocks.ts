/**
 * Reusable Playwright route interceptors for LexEval API endpoints.
 *
 * Each helper registers a mock for one endpoint family.  Call them in
 * test beforeEach / test body before navigating to the page under test.
 */

import type { Page } from "@playwright/test";

const API = "/api/v1";

// ── Auth ─────────────────────────────────────────────────────────────────────

export async function mockRegister(page: Page, token = "test-token") {
  await page.route(`**${API}/auth/register`, (route) =>
    route.fulfill({ json: { access_token: token } })
  );
}

export async function mockLogin(page: Page, token = "test-token") {
  await page.route(`**${API}/auth/login`, (route) =>
    route.fulfill({ json: { access_token: token } })
  );
}

// ── Dashboard ────────────────────────────────────────────────────────────────

export async function mockDashboardStats(page: Page) {
  await page.route(`**${API}/dashboard/stats`, (route) =>
    route.fulfill({
      json: {
        total_cases: 3,
        evaluations_run: 5,
        models_evaluated: 4,
        avg_clusters: 2.4,
      },
    })
  );
}

// ── Cases ────────────────────────────────────────────────────────────────────

const MOCK_CASE = {
  id: "case-uuid-1",
  title: "Smith v. Jones",
  filename: "smith_v_jones.pdf",
  raw_text: "The standard of review is de novo.",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

export async function mockListCases(page: Page, cases = [MOCK_CASE]) {
  await page.route(`**${API}/cases`, (route) => {
    if (route.request().method() === "GET") return route.fulfill({ json: cases });
    return route.fallback();
  });
}

export async function mockUploadCase(page: Page, caseData = MOCK_CASE) {
  await page.route(`**${API}/cases`, (route) => {
    if (route.request().method() === "POST")
      return route.fulfill({ status: 201, json: caseData });
    return route.fallback();
  });
}

// ── Rubrics ──────────────────────────────────────────────────────────────────

const MOCK_RUBRIC = {
  id: "rubric-uuid-1",
  case_id: "case-uuid-1",
  criteria: [
    { id: "accuracy", name: "Accuracy", description: "Factual correctness.", weight: 0.6 },
    { id: "reasoning", name: "Reasoning", description: "Legal reasoning quality.", weight: 0.4 },
  ],
  raw_response: '{"criteria":[...]}',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

export async function mockGenerateRubric(page: Page, rubric = MOCK_RUBRIC) {
  await page.route(`**${API}/rubrics`, (route) =>
    route.fulfill({ status: 201, json: rubric })
  );
}

export async function mockGetRubricByCase(page: Page, rubric = MOCK_RUBRIC) {
  await page.route(`**${API}/rubrics/case/**`, (route) =>
    route.fulfill({ json: rubric })
  );
}

// ── Evaluations ──────────────────────────────────────────────────────────────

const MOCK_EVALUATION = {
  id: "eval-uuid-1",
  case_id: "case-uuid-1",
  question: "What is the applicable standard of review?",
  model_names: [
    "LiquidAI/LFM2-24B-A2B",
    "openai/gpt-oss-20b",
    "google/gemma-3n-E4B-it",
    "arize-ai/qwen-2-1.5b-instruct",
    "meta-llama/Meta-Llama-3-8B-Instruct-Lite",
  ],
  status: "done",
  response_count: 200, // 5 models * 40 responses each
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

export async function mockListEvaluations(page: Page, evals = [MOCK_EVALUATION]) {
  await page.route(`**${API}/evaluations`, (route) => {
    if (route.request().method() === "GET") return route.fulfill({ json: evals });
    return route.fallback();
  });
}

export async function mockGetEvaluation(page: Page, evaluation = MOCK_EVALUATION) {
  await page.route(`**${API}/evaluations/${evaluation.id}`, (route) =>
    route.fulfill({ json: evaluation })
  );
}

export async function mockCreateEvaluation(page: Page, evaluation = MOCK_EVALUATION) {
  await page.route(`**${API}/evaluations`, (route) => {
    if (route.request().method() === "POST")
      return route.fulfill({ status: 201, json: { ...evaluation, status: "running" } });
    return route.fallback();
  });
}

export async function mockListModels(page: Page) {
  await page.route(`**${API}/evaluations/models`, (route) =>
    route.fulfill({
      json: [
        { id: "LiquidAI/LFM2-24B-A2B", name: "LFM2 24B", provider: "LiquidAI" },
        { id: "openai/gpt-oss-20b", name: "GPT OSS 20B", provider: "OpenAI" },
        { id: "google/gemma-3n-E4B-it", name: "Gemma 3n E4B", provider: "Google" },
        { id: "arize-ai/qwen-2-1.5b-instruct", name: "Qwen 2 1.5B", provider: "Arize/Alibaba" },
        {
          id: "meta-llama/Meta-Llama-3-8B-Instruct-Lite",
          name: "Llama 3 8B Lite",
          provider: "Meta",
        },
      ],
    })
  );
}

// ── Analysis ─────────────────────────────────────────────────────────────────

const MOCK_ANALYSIS = {
  id: "analysis-uuid-1",
  evaluation_id: "eval-uuid-1",
  k: 3,
  clusters: [
    { cluster_id: 0, response_indices: Array.from({ length: 70 }, (_, i) => i), centroid_index: 5, centroid_response_text: "The standard of review is de novo." },
    { cluster_id: 1, response_indices: Array.from({ length: 80 }, (_, i) => i + 70), centroid_index: 72, centroid_response_text: "Under the abuse of discretion standard..." },
    { cluster_id: 2, response_indices: Array.from({ length: 50 }, (_, i) => i + 150), centroid_index: 155, centroid_response_text: "The court applies a clearly erroneous standard." },
  ],
  centroid_indices: [5, 72, 155],
  scores: { "0": 0.88, "1": 0.72, "2": 0.61 },
  winning_cluster: 0,
  model_shares: {
    "LiquidAI/LFM2-24B-A2B": 0.31,
    "openai/gpt-oss-20b": 0.25,
    "google/gemma-3n-E4B-it": 0.19,
    "arize-ai/qwen-2-1.5b-instruct": 0.14,
    "meta-llama/Meta-Llama-3-8B-Instruct-Lite": 0.11,
  },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

export async function mockRunAnalysis(page: Page, analysis = MOCK_ANALYSIS) {
  await page.route(`**${API}/analysis/*/run`, (route) =>
    route.fulfill({ json: analysis })
  );
}

export async function mockGetAnalysis(page: Page, analysis = MOCK_ANALYSIS) {
  await page.route(`**${API}/analysis/*`, (route) => {
    if (!route.request().url().includes("/run")) return route.fulfill({ json: analysis });
    return route.fallback();
  });
}

// ── Composite helpers ─────────────────────────────────────────────────────────

/** Mock every endpoint needed to render an authenticated dashboard. */
export async function mockAuthenticatedApp(page: Page) {
  await mockDashboardStats(page);
  await mockListCases(page);
  await mockListEvaluations(page);
  await mockListModels(page);
}

/**
 * Inject auth state into localStorage before the page loads so the app
 * treats the session as authenticated without going through the login flow.
 *
 * Two keys are required:
 *  - "auth_token"    — read by the Axios interceptor for every API request
 *  - "auth-storage"  — Zustand persist state; drives the ProtectedRoute guard
 */
export async function injectAuthToken(page: Page, token = "test-token") {
  await page.addInitScript((t) => {
    const fakeUser = {
      id: "user-uuid-1",
      email: "test@example.com",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    localStorage.setItem("auth_token", t);
    localStorage.setItem(
      "auth-storage",
      JSON.stringify({ state: { token: t, user: fakeUser }, version: 0 })
    );
  }, token);
}
