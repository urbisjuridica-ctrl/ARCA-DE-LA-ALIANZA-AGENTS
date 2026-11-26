import fs from "node:fs";
import assert from "node:assert/strict";
import { verifySyntaxAndPolicy } from "../src/verifier.mjs";

const data = JSON.parse(fs.readFileSync("../../tests/hekt_conformance_vectors.json", "utf8"));
let checked = 0;
const mismatches = [];

for (const row of data.vectors) {
  if (row.implementation_defined) continue;
  checked++;
  const msg = Buffer.from(row.message_utf8_hex, "hex").toString("utf8");
  const res = verifySyntaxAndPolicy(msg);
  if (res.reason !== row.expected) {
    mismatches.push({ id: row.id, expected: row.expected, got: res.reason, source: row.source });
  }
}

console.log(`TypeScript/Node verifier -> Total: ${data.vectors.length} | Checked: ${checked} | Mismatches: ${mismatches.length}`);
assert.equal(mismatches.length, 0, JSON.stringify(mismatches, null, 2));
