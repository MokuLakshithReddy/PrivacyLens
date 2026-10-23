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
