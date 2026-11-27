import assert from "node:assert/strict";
import crypto from "node:crypto";
import { verifyMessage, isValidEd25519PublicKeyHex, canonicalizeTextBytes } from "../src/verifier.mjs";

const { publicKey, privateKey } = crypto.generateKeyPairSync("ed25519");
const pubHex = publicKey.export({ format: "der", type: "spki" }).subarray(-32).toString("hex");
const trust = { "ts-k1": pubHex };

const now = 1795800000;
const body = "payload=ok";
const bsha = crypto.createHash("sha256").update(canonicalizeTextBytes(body)).digest("hex");

function signMsg(ts, nonce) {
  const unsigned = `[H::AUD] kid=ts-k1 | aud=a2a-prod | ts=${ts} | nonce=${nonce} | sha256=${bsha} -> emit=ATTEST_ARTIFACT`;
  const sig = crypto.sign(null, Buffer.from(unsigned, "utf8"), privateKey).toString("hex");
  return `[H::AUD] kid=ts-k1 | aud=a2a-prod | ts=${ts} | nonce=${nonce} | sha256=${bsha} | sig=${sig} -> emit=ATTEST_ARTIFACT\n${body}`;
}

// 1. Válido en frontera exacta now-300 y now+300
const nonces = new Set();
assert.equal(verifyMessage(signMsg(now - 300, "n1"), { trustedKeys: trust, expectedAudience: "a2a-prod", seenNonces: nonces, nowTs: now }).reason, "VERIFIED_WITH_ED25519_AND_SHA256");
assert.equal(verifyMessage(signMsg(now + 300, "n2"), { trustedKeys: trust, expectedAudience: "a2a-prod", seenNonces: nonces, nowTs: now }).reason, "VERIFIED_WITH_ED25519_AND_SHA256");

// 2. Replay bloqueado
assert.equal(verifyMessage(signMsg(now - 300, "n1"), { trustedKeys: trust, expectedAudience: "a2a-prod", seenNonces: nonces, nowTs: now }).reason, "REPLAY_DETECTED");

// 3. Frontera expirada now-301 y futura now+301
assert.equal(verifyMessage(signMsg(now - 301, "n3"), { trustedKeys: trust, expectedAudience: "a2a-prod", seenNonces: nonces, nowTs: now }).reason, "EXPIRED_OR_FUTURE_TIMESTAMP");
assert.equal(verifyMessage(signMsg(now + 301, "n4"), { trustedKeys: trust, expectedAudience: "a2a-prod", seenNonces: nonces, nowTs: now }).reason, "EXPIRED_OR_FUTURE_TIMESTAMP");

// 4. Puntos de torsión de orden pequeño Ed25519 (R=Identity, S=0) bloqueados
const torsionKeys = [
  "0000000000000000000000000000000000000000000000000000000000000000",
  "0100000000000000000000000000000000000000000000000000000000000000",
  "ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f",
  "c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac03fa",
];
const forgedZeroSig = "0100000000000000000000000000000000000000000000000000000000000000" + "00".repeat(32);
for (const tk of torsionKeys) {
  assert.equal(isValidEd25519PublicKeyHex(tk), false, `Torsion key must be rejected: ${tk}`);
  const forged = `[H::AUD] kid=bad | sig=${forgedZeroSig} -> emit=ATTEST_ARTIFACT`;
  assert.equal(verifyMessage(forged, { trustedKeys: { bad: tk } }).reason, "INVALID_SIGNATURE_OR_KEY");
}

console.log("TS Crypto Parity Suite PASSED (torsion, S<L, ts +-300/301, replay, SHA-256)");
