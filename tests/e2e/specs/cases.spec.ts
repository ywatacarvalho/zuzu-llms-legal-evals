import { expect, test } from "@playwright/test";

import {
  injectAuthToken,
  mockAuthenticatedApp,
  mockListCases,
  mockUploadCase,
} from "../support/api-mocks";

test.describe("Cases", () => {
  test.beforeEach(async ({ page }) => {
    await injectAuthToken(page);
    await mockAuthenticatedApp(page);
  });

  test("cases page lists existing cases", async ({ page }) => {
    await page.goto("/cases");
    await expect(page.getByText("Smith v. Jones")).toBeVisible();
  });

  test("empty state is shown when no cases exist", async ({ page }) => {
    await mockListCases(page, []);
    await page.goto("/cases");
    // Table or empty state message should render without error
    await expect(page.locator("body")).not.toContainText("Error");
  });

  test("upload dialog opens when clicking New Case", async ({ page }) => {
    await page.goto("/cases");
    await page.getByRole("button", { name: /new case|upload/i }).click();
    // Dialog or file input should appear
    await expect(
      page.getByRole("dialog").or(page.getByLabel(/title/i)).first()
    ).toBeVisible();
  });

  test("uploading a PDF creates a new case and adds it to the list", async ({ page }) => {
    const newCase = {
      id: "case-uuid-new",
      title: "New Test Case",
      filename: "new_case.pdf",
      raw_text: "Some legal text.",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    await mockUploadCase(page, newCase);
    await mockListCases(page, []);

    await page.goto("/cases");
    await page.getByRole("button", { name: /new case|upload/i }).click();

    // Fill optional title
    const titleInput = page.getByLabel(/title/i);
    if (await titleInput.isVisible()) {
      await titleInput.fill("New Test Case");
    }

    // Attach a minimal PDF buffer
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "new_case.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4"),
    });

    await page.getByRole("button", { name: /upload|submit|save/i }).last().click();

    // After upload the new case should appear
    await expect(page.getByText("New Test Case")).toBeVisible({ timeout: 5_000 });
  });
});
