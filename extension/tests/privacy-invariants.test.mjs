import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = async (path) => readFile(new URL(path, import.meta.url), "utf8");

test("storage inspection never reads values, keys, or cookies", async () => {
  const inspector = await source("../src/content/storage-inspector.ts");
  assert.doesNotMatch(inspector, /\.getItem\s*\(/);
  assert.doesNotMatch(inspector, /\.key\s*\(/);
  assert.doesNotMatch(inspector, /document\.cookie/);
  assert.match(inspector, /window\.localStorage\.length/);
  assert.match(inspector, /window\.sessionStorage\.length/);
});

test("network telemetry retains an origin instead of a request path", async () => {
  const observer = await source("../src/background/network/traffic-observer.ts");
  assert.match(observer, /url:\s*targetUrl\.origin/);
  assert.doesNotMatch(observer, /targetUrl\.pathname/);
});

test("backend sync does not transmit storage metadata", async () => {
  const router = await source("../src/background/messaging/message-router.ts");
  assert.match(router, /scan_session_id:\s*batch\.scanSessionId/);
  assert.doesNotMatch(router, /storage_keys:\s*batch\.storage/);
});

test("domain classification uses the maintained public suffix list", async () => {
  const observer = await source("../src/background/network/traffic-observer.ts");
  assert.match(observer, /from 'psl'/);
  assert.doesNotMatch(observer, /MULTI_LABEL_SUFFIXES/);
});

test("request deduplication is event-id based", async () => {
  const router = await source("../src/background/messaging/message-router.ts");
  assert.match(router, /r\.requestId === signal\.requestId/);
  assert.doesNotMatch(router, /r\.targetDomain === signal\.targetDomain && r\.category === signal\.category/);
});

test("backend failures are not treated as successful ingestion", async () => {
  const router = await source("../src/background/messaging/message-router.ts");
  assert.match(router, /const ingestRes = await fetch/);
  assert.match(router, /if \(!ingestRes\.ok\)/);
  assert.match(router, /Observation ingestion failed/);
  assert.match(router, /BackendSyncError/);
  assert.match(router, /catch \(error\) \{\s+if \(error instanceof BackendSyncError\) throw error/s);
  assert.doesNotMatch(router, /catch \{\s+return null;\s+\}\s+}\s+catch/);
});

test("backend HTTP errors surface while transport failures can fall back", async () => {
  const router = await source("../src/background/messaging/message-router.ts");
  const background = await source("../src/background/index.ts");
  assert.match(router, /status\?\: number/);
  assert.match(router, /signal: controller\.signal/);
  assert.match(router, /return null/);
  assert.match(background, /catch \(error\) \{\s+sendResponse\(\{\s+error:/s);
  assert.match(background, /if \(!analysis\) \{\s+analysis = store\.evaluateLocally\(session\);/s);
});
