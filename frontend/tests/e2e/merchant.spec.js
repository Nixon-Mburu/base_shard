import { test, expect } from "@playwright/test";
test("merchant signup, persistent basket, declined payment, successful payment", async ({
  page,
}) => {
  await page.goto("/signup");
  await page
    .getByLabel("Business name", { exact: true })
    .fill("Wanjiku Market");
  await page.getByLabel("Contact name").fill("Wanjiku");
  await page.getByLabel("Phone number").fill("0712345678");
  await page.getByRole("button", { name: "Continue to location" }).click();
  await page.getByLabel("Latitude", { exact: true }).fill("-1.28");
  await page.getByLabel("Longitude", { exact: true }).fill("36.82");
  await page
    .getByLabel("Street, building & delivery directions")
    .fill("Moi Avenue, ground floor");
  await page.getByRole("button", { name: "Save & start shopping" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Good business starts with great stock.",
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Add Premium pishori rice", exact: true })
    .click();
  await page.reload();
  await expect(
    page.getByText("1 item in your order", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Review order" }).click();
  await page.getByLabel("Demo payment outcome").selectOption("declined");
  await page.getByRole("button", { name: "Place demo order" }).click();
  await expect(page.getByRole("alert")).toContainText("declined");
  await page.getByLabel("Demo payment outcome").selectOption("success");
  await page.getByRole("button", { name: "Place demo order" }).click();
  await expect(
    page.getByRole("heading", { name: "You’re all stocked up." }),
  ).toBeVisible();
  await expect(
    page.getByText("No money was charged", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Continue shopping" }).click();
  await expect(
    page.getByRole("button", { name: "Cart, 0 items" }),
  ).toBeVisible();
});
test("catalog filters and empty checkout work on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/orders");
  await page.getByLabel("Search inventory").fill("not-a-product");
  await expect(
    page.getByRole("heading", { name: "No matching products" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(page.locator(".product-card")).toHaveCount(8);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.goto("/checkout");
  await expect(
    page.getByRole("heading", { name: "Your next restock is waiting." }),
  ).toBeVisible();
});
