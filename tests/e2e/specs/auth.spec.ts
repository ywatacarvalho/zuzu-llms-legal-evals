import { expect, test } from "@playwright/test";

import { mockDashboardStats, mockListCases, mockListEvaluations, mockListModels, mockLogin } from "../support/api-mocks";

const MOCK_USER = {
  id: "user-uuid-1",
  email: "test@example.com",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

test.describe("Authentication", () => {
  test("login page renders the app name and form", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "LexEval" })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in|login/i })).toBeVisible();
  });

  test("successful login redirects to dashboard", async ({ page }) => {
    await mockLogin(page);
    await mockDashboardStats(page);
    await mockListCases(page);
    await mockListEvaluations(page);
    await mockListModels(page);

    // Mock /auth/me called after login
    await page.route("**/api/v1/auth/me", (route) =>
      route.fulfill({ json: MOCK_USER })
    );

    await page.goto("/login");
    await page.getByLabel(/email/i).fill("test@example.com");
    await page.getByLabel(/password/i).fill("password123");
    await page.getByRole("button", { name: /sign in|login/i }).click();

    await expect(page).toHaveURL("/");
    await expect(page.getByText("LexEval")).toBeVisible();
  });

  test("invalid credentials shows an error message", async ({ page }) => {
    await page.route("**/api/v1/auth/login", (route) =>
      route.fulfill({ status: 401, json: { detail: "Invalid credentials" } })
    );

    await page.goto("/login");
    await page.getByLabel(/email/i).fill("wrong@example.com");
    await page.getByLabel(/password/i).fill("badpassword");
    await page.getByRole("button", { name: /sign in|login/i }).click();

    // Error message should appear; stay on login page
    await expect(page.getByText(/invalid email or password|invalid credentials|incorrect/i)).toBeVisible();
    await expect(page).toHaveURL("/login");
  });

  test("unauthenticated access to dashboard redirects to login", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL("/login");
  });
});
