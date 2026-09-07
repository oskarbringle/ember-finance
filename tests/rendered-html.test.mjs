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

test("server-renders Ember's local-first application shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>Ember — Personal Finance<\/title>/i);
  assert.match(html, /Private by design/);
  assert.match(html, /Stored on this Mac/);
  assert.match(html, /API offline · run the local start script/);
  assert.doesNotMatch(html, />OB</);
});

test("source starts from zero and does not contain a demo dashboard fallback", async () => {
  const [page, finance] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/lib/finance.ts", import.meta.url), "utf8"),
  ]);
  assert.match(finance, /export const EMPTY_DASHBOARD/);
  assert.match(page, /useState<Dashboard>\(EMPTY_DASHBOARD\)/);
  assert.match(
    page,
    /\[accounts, setAccounts\] = useState<Account\[\]>\(\[\]\)/,
  );
  assert.match(
    page,
    /\[transactions, setTransactions\] = useState<Transaction\[\]>\(\[\]\)/,
  );
  assert.match(page, /Start with a clean slate/);
  assert.match(page, /const \[page, setPage\] = useState\("Home"\)/);
  assert.match(page, /\["Home", House\]/);
  assert.match(page, /className="account-edit-button"/);
  assert.doesNotMatch(
    page,
    /fallbackDashboard|fallbackAccounts|fallbackTransactions/,
  );
  assert.doesNotMatch(page, /Preview data · start API to edit/);
});
