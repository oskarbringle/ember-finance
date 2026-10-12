import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: handleRequest } = await import(workerUrl.href);
  return handleRequest(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
  );
}

test("server-renders Ember's spreadsheet analytics shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /<title>Ember — Personal Finance<\/title>/i);
  assert.match(html, /Private by design/);
  assert.match(html, /Stored on this Mac/);
  assert.match(html, /Loading dashboard/);
});

test("source uses the workbook-first navigation and no statement workflow", async () => {
  const page = await readFile(
    new URL("../app/page.tsx", import.meta.url),
    "utf8",
  );
  assert.match(page, /"Overview"/);
  assert.match(page, /"Spending"/);
  assert.match(page, /"Net Worth"/);
  assert.match(page, /Import \/ Replace Data/);
  assert.doesNotMatch(page, /ReviewPage|TransactionDrawer|PDF statement/);
});
