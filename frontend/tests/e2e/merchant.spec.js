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

test("an interrupted response resumes the same order after reload", async ({
  page,
  request,
}) => {
  const profile = {
    businessName: "Retry Shop",
    owner: "Retry Merchant",
    phone: "0712345678",
    type: "Retail shop",
    city: "Nairobi",
    address: "Test Street",
    point: { lat: -1.28, lng: 36.82 },
  };
  const signup = await request.post("/api/merchants", { data: profile });
  expect(signup.ok()).toBeTruthy();
  const account = await signup.json();
  const catalog = await (await request.get("/api/catalog/products")).json();
  const before = catalog.find((p) => p.id === "rice").stock;
  await page.goto("/checkout");
  await page.evaluate(
    ({ account }) => {
      localStorage.setItem("base-grid:session", JSON.stringify(account.token));
      localStorage.setItem(
        "base-grid:merchant",
        JSON.stringify(account.merchant),
      );
      localStorage.setItem("base-grid:cart", JSON.stringify({ rice: 1 }));
    },
    { account },
  );
  await page.reload();
  let orderId;
  await page.route(
    "**/api/orders",
    async (route) => {
      const response = await route.fetch();
      orderId = (await response.json()).id;
      await route.abort("failed");
    },
    { times: 1 },
  );
  await page.getByRole("button", { name: "Place demo order" }).click();
  await expect(page.getByRole("alert")).toContainText("could not be reached");
  await page.reload();
  await page
    .getByRole("button", { name: "Check order status", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "You’re all stocked up." }),
  ).toBeVisible();
  const history = await (
    await request.get("/api/orders", {
      headers: { Authorization: "Bearer " + account.token },
    })
  ).json();
  expect(history).toHaveLength(1);
  expect(history[0].id).toBe(orderId);
  const after = await (await request.get("/api/catalog/products")).json();
  expect(after.find((p) => p.id === "rice").stock).toBe(before - 1);
});
