import { defineConfig, devices } from "@playwright/test";

/**
 * E2E tests use Playwright route interception to mock all backend API calls,
 * so no live backend or database is required.
 *
 * To run against a live stack instead, set LEXEVAL_BASE_URL and
 * LEXEVAL_API_URL environment variables and remove route mocking from tests.
 *
 * Run:  npx playwright test
 * UI:   npx playwright test --ui
 */
export default defineConfig({
  testDir: "./specs",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],

  use: {
    baseURL: process.env.LEXEVAL_BASE_URL ?? "http://localhost:5173",
    headless: true,
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  // Start the Vite dev server automatically when running E2E.
  // The server is started once for the entire test run.
  webServer: {
    command: "npm run dev",
    cwd: "../../frontend",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
