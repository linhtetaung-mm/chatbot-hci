/* Real browser regression checks. Fixtures use demo mode, temporary files and no .env. */
const engine = process.env.HCI_BROWSER || "chromium";
const browserType = require("playwright")[engine];
assertBrowserType();
function assertBrowserType() {
  if (!["chromium", "webkit", "firefox"].includes(engine))
    throw new Error("Unsupported HCI_BROWSER");
}
const { spawn } = require("node:child_process");
const { once } = require("node:events");
const { createInterface } = require("node:readline");
const { mkdir } = require("node:fs/promises");
const path = require("node:path");
const assert = require("node:assert/strict");
const project = path.resolve(__dirname, "..");
const python =
  process.env.HCI_TEST_PYTHON || path.join(project, ".venv/bin/python");
const fixture = spawn(python, ["tests/browser_fixture.py"], {
  cwd: project,
  stdio: ["ignore", "pipe", "inherit"],
});
let browser;
const errors = [];
const records = [];
const artifactDir = process.env.HCI_UI_ARTIFACTS;

async function fit(page, label) {
  const result = await page.evaluate(() => ({
    width: window.innerWidth,
    content: document.documentElement.scrollWidth,
    smallInputs: [
      ...document.querySelectorAll(
        "input:not([type=radio]):not([type=checkbox]),textarea,select",
      ),
    ].filter(
      (el) =>
        el.getClientRects().length &&
        parseFloat(getComputedStyle(el).fontSize) < 16,
    ).length,
  }));
  assert.ok(
    result.content <= result.width + 1,
    `${label}: horizontal page overflow ${JSON.stringify(result)}`,
  );
  assert.equal(
    result.smallInputs,
    0,
    `${label}: small inputs cause mobile zoom`,
  );
  records.push(label);
}
async function login(page, code) {
  await page.locator("#code").fill(code);
  await page.locator("#login button").click();
  await page.locator("#login").waitFor({ state: "detached" });
}
async function consent(page) {
  for (const input of await page.locator("#consent input").all())
    await input.check();
  await page.locator("#consent button").click();
  await page.locator("#start").waitFor();
}
async function beginChat(page) {
  await page.locator("#start button").click();
  await page.locator("#text").waitFor();
}
async function send(page, text) {
  await page.locator("#text").fill(text);
  await page.locator("#send button").click();
  await page.locator("#text:not(:disabled)").waitFor();
}
async function screenshot(page, file) {
  if (artifactDir)
    await page.screenshot({
      path: path.join(artifactDir, file),
      fullPage: true,
    });
}

(async () => {
  const lines = createInterface({ input: fixture.stdout });
  const config = await Promise.race([
    once(lines, "line").then(([line]) => JSON.parse(line)),
    once(fixture, "exit").then(([code]) => {
      throw new Error(`Fixture exited early: ${code}`);
    }),
    new Promise((_, reject) => {
      const timer = setTimeout(
        () => reject(new Error("Fixture startup timed out")),
        15000,
      );
      timer.unref();
    }),
  ]);
  if (artifactDir) await mkdir(artifactDir, { recursive: true });
  browser = await browserType.launch({ headless: true });
  for (const [index, [width, height]] of [
    [320, 740],
    [390, 844],
    [768, 1024],
    [1440, 1000],
  ].entries()) {
    const context = await browser.newContext({
      viewport: { width, height },
      ...(engine !== "firefox" ? { isMobile: width < 600 } : {}),
      hasTouch: width < 600,
    });
    const page = await context.newPage();
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(config.origin);
    await page.locator("#login").waitFor();
    await fit(page, `${width}: login`);
    await login(page, config.codes[index]);
    if (await page.locator("#consent").count()) {
      await fit(page, `${width}: consent`);
      await consent(page);
    }
    await beginChat(page);
    await send(page, "I had a rough day because of a small deadline.");
    await fit(page, `${width}: chat`);
    await screenshot(page, `chat-${width}.png`);
    await page.locator("#finish").click();
    await page.locator("#rate").waitFor();
    await fit(page, `${width}: ratings`);
    // All seven choices stay aligned and visible; endpoints are unchanged.
    const tops = await page
      .locator("input[name=support_needed]")
      .evaluateAll((inputs) =>
        inputs.map((input) => Math.round(input.getBoundingClientRect().top)),
      );
    assert.equal(new Set(tops).size, 1, `${width}: rating controls misaligned`);
    await screenshot(page, `ratings-${width}.png`);
    await page.locator('input[name=support_needed][value="5"]').check();
    await page.locator('input[name=felt_understood][value="6"]').check();
    if (width === 320) {
      await page.locator("#post_distress").fill("73");
      await page.route("**/api/action", async (route) => {
        if (route.request().postDataJSON().action === "rate")
          return route.fulfill({
            status: 503,
            contentType: "text/html",
            body: "Unavailable",
          });
        return route.continue();
      });
      await page.locator("#rate button").click();
      await page.locator("#notice:not([hidden])").waitFor();
      await page.locator("#app[aria-busy=false]").waitFor();
      assert.equal(await page.locator("#post_distress").inputValue(), "73");
      assert.ok(
        await page.locator('input[name=support_needed][value="5"]').isChecked(),
      );
      assert.ok(
        await page
          .locator('input[name=felt_understood][value="6"]')
          .isChecked(),
      );
      await page.unroute("**/api/action");
      records.push(
        "Rating recovery: failed submission retains all selected answers in the tab",
      );
    }
    await page.locator("#rate button").click();
    await page.locator(".saved").waitFor();
    await page.locator("#logout").click();
    await page.goto(`${config.origin}/admin`);
    await page.locator("#login").waitFor();
    await login(page, config.admin);
    await page.locator("#enroll").waitFor();
    for (const details of await page.locator("details").all())
      await details.evaluate((el) => {
        el.open = true;
      });
    await fit(page, `${width}: researcher`);
    await screenshot(page, `researcher-${width}.png`);
    if (width === 1440) {
      // Recover an unused test account without creating another enrollment.
      await page.locator("#reissue select").selectOption({ index: 3 });
      await page.locator("#reissue input").fill("REPLACE CODE");
      await page.locator("#reissue button").click();
      await page.locator("#replacement:not([hidden])").waitFor();
      const replacement = (
        await page.locator("#replacement").innerText()
      ).match(/Replacement access code: ([A-Z2-9-]+)/)[1];
      const headers = { Origin: config.origin, "X-Chatbot-Request": "1" };
      const oldLogin = await context.request.post(
        config.origin + "/api/login",
        { headers, data: { code: config.codes[3] } },
      );
      assert.equal(oldLogin.status(), 401);
      const newLogin = await context.request.post(
        config.origin + "/api/login",
        { headers, data: { code: replacement } },
      );
      assert.equal(newLogin.status(), 200);
      records.push(
        "Access recovery: replacement code works and old code is rejected",
      );
    }
    await context.close();
  }
  // Lost requests before and after saving must retain text and reuse the same request ID.
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    ...(engine !== "firefox" ? { isMobile: true } : {}),
    hasTouch: true,
  });
  const page = await context.newPage();
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(config.origin);
  await page.locator("#login").waitFor();
  await login(page, config.codes[1]);
  if (await page.locator("#consent").count()) await consent(page);
  await beginChat(page);
  let fault = "before",
    releaseHold,
    signalHeld;
  const held = new Promise((resolve) => {
    signalHeld = resolve;
  });
  const requests = [];
  await page.route("**/api/action", async (route) => {
    const data = route.request().postDataJSON();
    if (data.action === "send") {
      requests.push(data.request_id);
      if (fault === "before") {
        fault = "";
        return route.fulfill({
          status: 503,
          contentType: "text/html",
          body: "<h1>Host unavailable</h1>",
        });
      }
      if (fault === "hold") {
        fault = "";
        const response = await route.fetch();
        signalHeld();
        await new Promise((resolve) => {
          releaseHold = resolve;
        });
        return route.fulfill({ response });
      }
      if (fault === "after") {
        fault = "";
        await route.fetch();
        return route.abort("failed");
      }
    }
    return route.continue();
  });
  const text = "My group meeting was difficult today.";
  await page.locator("#text").fill(text);
  await page.locator("#send button").click();
  await page.locator("#retry:not(:disabled)").waitFor();
  assert.equal(await page.locator(".message.user").count(), 1);
  assert.ok(
    (await page.locator("#notice").innerText()).includes(
      "temporarily unavailable",
    ),
  );
  await page.locator("#retry").click();
  await page.locator("#text:not(:disabled)").waitFor();
  assert.equal(requests[0], requests[1]);
  assert.equal(await page.locator(".message.user").count(), 1);
  fault = "after";
  await send(page, "I am still worried about the same meeting.");
  assert.equal(await page.locator(".message.user").count(), 2);
  assert.equal(await page.locator("#retry").count(), 0);
  records.push(
    "Recovery: HTML error before save; lost response after save; no duplicate messages",
  );
  // A reconnect screen recovers from an initial non-JSON API failure.
  const reconnect = await context.newPage();
  await reconnect.route("**/api/state*", (route) =>
    route.fulfill({
      status: 503,
      contentType: "text/html",
      body: "Unavailable",
    }),
  );
  await reconnect.goto(config.origin);
  await reconnect.locator("#reconnect").waitFor();
  await reconnect.unroute("**/api/state*");
  await reconnect.locator("#reconnect").click();
  await reconnect.locator("#text").waitFor();
  records.push("Recovery: initial API failure and reconnect");
  // Stop stays available while a reply is delayed, and its late response cannot reopen the chat.
  fault = "hold";
  await page.locator("#text").fill("One more thought about my meeting.");
  await page.locator("#send button").click();
  await held;
  assert.ok(await page.locator("#stop").isEnabled());
  page.once("dialog", (dialog) => dialog.accept());
  await page.locator("#stop").click();
  await page.locator("#start").waitFor();
  releaseHold();
  await page.locator("#app[aria-busy=false]").waitFor();
  assert.equal(await page.locator("#text").count(), 0);
  records.push(
    "Stop during a delayed reply: remains available; no chat revival",
  );

  await context.close();
  assert.deepEqual(errors, [], "Browser JavaScript errors");
  console.log(
    `PASS: ${records.length} browser checks; ${engine}; widths 320, 390, 768, 1440; no JavaScript errors.`,
  );
  console.log(records.join("\n"));
})()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    if (browser) await browser.close();
    fixture.kill("SIGTERM");
  });
