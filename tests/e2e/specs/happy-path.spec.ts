/**
 * Happy-path E2E spec — covers the full LexEval pipeline:
 *
 *   Login → Dashboard → Upload case → Generate rubric →
 *   Create evaluation → View evaluation → Run analysis → View results
 *
 * All backend API calls are intercepted with Playwright route mocks so the
 * tests run without a live database or AI services.
 */

import { expect, test } from "@playwright/test";

import {
  injectAuthToken,
  mockAuthenticatedApp,
  mockCreateEvaluation,
  mockGenerateRubric,
  mockGetAnalysis,
  mockGetEvaluation,
  mockGetRubricByCase,
  mockListCases,
  mockListEvaluations,
  mockListModels,
  mockRunAnalysis,
  mockUploadCase,
} from "../support/api-mocks";

const CASE_ID = "case-uuid-1";
const EVAL_ID = "eval-uuid-1";

// ── Dashboard ─────────────────────────────────────────────────────────────────

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await injectAuthToken(page);
    await mockAuthenticatedApp(page);
  });

  test("shows KPI cards with real values after loading", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("3", { exact: true })).toBeVisible();   // total_cases
    await expect(page.getByText("5", { exact: true })).toBeVisible();   // evaluations_run
    await expect(page.getByText("4", { exact: true })).toBeVisible();   // models_evaluated
  });

  test("sidebar navigation links are visible", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: /cases/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /evaluations/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /results/i })).toBeVisible();
  });
});

// ── Case upload ───────────────────────────────────────────────────────────────

test.describe("Case upload flow", () => {
  test.beforeEach(async ({ page }) => {
    await injectAuthToken(page);
    await mockAuthenticatedApp(page);
  });

  test("navigating to /cases shows the cases table", async ({ page }) => {
    await page.goto("/cases");
    await expect(page.getByText("Smith v. Jones")).toBeVisible();
  });

  test("case detail page renders after clicking a case row", async ({ page }) => {
    await page.route(`**/api/v1/cases/${CASE_ID}`, (route) =>
      route.fulfill({
        json: {
          id: CASE_ID,
          title: "Smith v. Jones",
          filename: "smith_v_jones.pdf",
          raw_text: "The standard of review is de novo.",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      })
    );
    await mockGetRubricByCase(page);

    await page.goto(`/cases/${CASE_ID}`);
    await expect(page.getByText("Smith v. Jones")).toBeVisible();
  });
});

// ── Rubric generation ─────────────────────────────────────────────────────────

test.describe("Rubric generation", () => {
  test.beforeEach(async ({ page }) => {
    await injectAuthToken(page);
    await mockAuthenticatedApp(page);
    await page.route(`**/api/v1/cases/${CASE_ID}`, (route) =>
      route.fulfill({
        json: {
          id: CASE_ID,
          title: "Smith v. Jones",
          filename: "smith_v_jones.pdf",
          raw_text: "Legal text.",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      })
    );
  });

  test("generating a rubric shows the criteria on the case detail page", async ({ page }) => {
    // No rubric yet
    await page.route(`**/api/v1/rubrics/case/${CASE_ID}`, (route) =>
      route.fulfill({ status: 404, json: { detail: "Not found" } })
    );
    await mockGenerateRubric(page);

    await page.goto(`/cases/${CASE_ID}`);
    const generateBtn = page.getByRole("button", { name: /generate rubric/i });
    await expect(generateBtn).toBeVisible();
    await generateBtn.click();

    // After generation the rubric criteria should appear
    await expect(page.getByText("Accuracy")).toBeVisible({ timeout: 5_000 });
  });

  test("existing rubric criteria are shown without needing to generate", async ({ page }) => {
    await mockGetRubricByCase(page);
    await page.goto(`/cases/${CASE_ID}`);
    await expect(page.getByText("Accuracy")).toBeVisible();
  });
});

// ── Evaluation creation ───────────────────────────────────────────────────────

test.describe("Evaluation creation", () => {
  test.beforeEach(async ({ page }) => {
    await injectAuthToken(page);
    await mockAuthenticatedApp(page);
    await mockListModels(page);
  });

  test("evaluations page lists existing evaluations", async ({ page }) => {
    await page.goto("/evaluations");
    await expect(
      page.getByText("What is the applicable standard of review?")
    ).toBeVisible();
  });

  test("opening the new evaluation form shows model selector", async ({ page }) => {
    await page.goto("/evaluations");
    await page.getByRole("button", { name: /new evaluation/i }).click();
    await expect(
      page
        .getByRole("button", { name: /GPT OSS 20B/i })
        .or(page.getByText(/select.*model/i))
        .first()
    ).toBeVisible({ timeout: 3_000 });
  });

  test("creating an evaluation adds it to the list", async ({ page }) => {
    const createdEval = {
      id: "eval-uuid-new",
      case_id: CASE_ID,
      question: "What is the burden of proof?",
      model_names: [
        "LiquidAI/LFM2-24B-A2B",
        "openai/gpt-oss-20b",
        "google/gemma-3n-E4B-it",
        "arize-ai/qwen-2-1.5b-instruct",
        "meta-llama/Meta-Llama-3-8B-Instruct-Lite",
      ],
      status: "running",
      response_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    await mockCreateEvaluation(page, createdEval);

    await page.goto("/evaluations");
    await page.getByRole("button", { name: /new evaluation/i }).click();

    // Wait for form to load cases and models
    await expect(page.getByLabel(/legal case/i).or(page.getByLabel(/case/i)).first()).toBeVisible({ timeout: 3_000 });

    // Select a case
    const caseSelect = page.getByLabel(/legal case/i).or(page.getByLabel(/case/i)).first();
    await caseSelect.selectOption({ index: 1 });

    // Enter question (must be ≥ 10 chars)
    const questionInput = page.getByLabel(/legal question/i).or(page.getByLabel(/question/i)).first();
    await questionInput.fill("What is the burden of proof?");

    // Select all 5 required models
    await page.getByRole("button", { name: "LFM2 24B" }).click();
    await page.getByRole("button", { name: "GPT OSS 20B" }).click();
    await page.getByRole("button", { name: "Gemma 3n E4B" }).click();
    await page.getByRole("button", { name: "Qwen 2 1.5B" }).click();
    await page.getByRole("button", { name: "Llama 3 8B Lite" }).click();

    // Submit (button becomes enabled once 2-5 models are selected)
    await page.getByRole("button", { name: /run evaluation/i }).click();

    await expect(page.getByText("What is the burden of proof?")).toBeVisible({
      timeout: 5_000,
    });
  });
});

// ── Analysis & results ────────────────────────────────────────────────────────

test.describe("Analysis and results", () => {
  test.beforeEach(async ({ page }) => {
    await injectAuthToken(page);
    await mockAuthenticatedApp(page);
    await mockListEvaluations(page);
    await mockGetEvaluation(page);
    await mockGetAnalysis(page);
    await mockRunAnalysis(page);
  });

  test("results list shows evaluations with 'done' status", async ({ page }) => {
    await page.goto("/results");
    await expect(
      page.getByText("What is the applicable standard of review?")
    ).toBeVisible();
  });

  test("results page shows winner banner and cluster charts", async ({ page }) => {
    await page.goto(`/results/${EVAL_ID}`);
    // Winner banner or top model name should be visible
    await expect(page.getByText("openai/gpt-oss-20b", { exact: true }).first()).toBeVisible({
      timeout: 5_000,
    });
  });

  test("clicking Run Analysis triggers the analysis endpoint and shows results", async ({
    page,
  }) => {
    // Override getAnalysis to return 404 first so "Run Analysis" button appears
    await page.route(`**/api/v1/analysis/${EVAL_ID}`, (route) =>
      route.fulfill({ status: 404, json: { detail: "Not found" } })
    );

    await page.goto(`/results/${EVAL_ID}`);
    const runBtn = page.getByRole("button", { name: /run analysis/i });
    await expect(runBtn).toBeVisible({ timeout: 3_000 });
    await runBtn.click();

    // After run, winner banner should appear
    await expect(page.getByText("openai/gpt-oss-20b", { exact: true }).first()).toBeVisible({
      timeout: 8_000,
    });
  });

  test("cluster centroid cards are rendered with response text", async ({ page }) => {
    await page.goto(`/results/${EVAL_ID}`);
    await expect(
      page.getByText("The standard of review is de novo.")
    ).toBeVisible({ timeout: 5_000 });
  });
});
