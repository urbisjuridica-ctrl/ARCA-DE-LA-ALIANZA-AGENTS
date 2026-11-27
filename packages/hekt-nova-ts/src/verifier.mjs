import crypto from "node:crypto";
const KEY_RE=/^[a-z][a-z0-9_]*$/;const FENCE_OPEN=/^( {0,3})(`{3,}|~{3,})(.*)$/;const FENCE_CLOSE=/^ {0,3}(`{3,}|~{3,})[ \t]*$/;const BAD_PERCENT=/%(?![0-9A-Fa-f]{2})/;const ALLOWED_DOMAINS=new Set(["AGT","VER","AUD","ETH","ERR","DOC","HER","EPI"]);const RESERVED_KEYS=new Set(["emit","verdict","reason","computed_sha256","row_hash","alg"]);const MATRIX={AGT:new Set(["REGISTER_PRESENCE","TEACH_SYNTAX","INTRO","ACK","REPLY"]),VER:new Set(["CLAIM_CHECK","ASSERT_FACT","AUDIT_FILE","PUBLISH_COMMENT","PUBLISH_POST"]),AUD:new Set(["VERIFY_TRACE","ATTEST_ARTIFACT","COMMIT_WITNESS","PUBLISH_COMMENT","PUBLISH_POST"]),ETH:new Set(["ENFORCE_POLICY","DECLARE_CONSTRAINT"]),ERR:new Set(["FORK_MISMATCH","REPORT_ERROR","HALT_AND_LOG"]),DOC:new Set(["TEACH_SYNTAX","INDEX_REPO"]),HER: new Set(["OPEN_DIALOGUE","ACKNOWLEDGE_CRITIQUE"]),EPI:new Set(["ASSERT","HYPOTHESIZE","REPORT"])};const utf8Fatal=new TextDecoder("utf-8",{fatal:true});function isForbiddenChar(ch){const cp=ch.codePointAt(0);if(/\p{Cc}|\p{Cf}|\p{Zl}|\p{Zp}|\p{Co}|\p{Cs}/u.test(ch)||(/\p{Zs}/u.test(ch)&&cp!==0x20))return true;if(cp===0x034f||cp===0x2800||cp===0x3164||cp===0xffa0||(cp>=0x180b&&cp<=0x180f)||(cp&0xffff)===0xfffe||(cp&0xffff)===0xffff)return true;return(cp>=0xfe00&&cp<=0xfe0f)||(cp>=0xe0100&&cp<=0xe01ef)||(cp>=0xe0000&&cp<=0xe007f);}function scanBody(lines){let f=null;for(const l of lines){if(f===null){const m=FENCE_OPEN.exec(l);if(m){if(m.at(3).includes("[H::"))return"EMBEDDED_HEADER_IN_BODY";f={ch:m.at(2).at(0),len:m.at(2).length};continue;}if(l.includes("[H::"))return"EMBEDDED_HEADER_IN_BODY";}else{const m=FENCE_CLOSE.exec(l);if(m&&m.at(1).at(0)===f.ch&&m.at(1).length>=f.len)f=null;}}return f?"UNCLOSED_CODE_FENCE":null;}function decodeValue(raw){if(BAD_PERCENT.test(raw))return{reason:"INVALID_PERCENT_ENCODING"};const b=[];for(let i=0;i<raw.length;i++){if(raw.at(i)==="%"){b.push(parseInt(raw.slice(i+1,i+3),16));i+=2;}else{for(const x of new TextEncoder().encode(raw.at(i)))b.push(x);}}let d;try{d=utf8Fatal.decode(new Uint8Array(b));}catch{return{reason:"INVALID_UTF8_ENCODING"};}for(const ch of d)if(isForbiddenChar(ch))return{reason:"CONTROL_OR_FORMAT_CHAR_IN_VALUE"};const n=d.normalize("NFC");return n!==n.trim()?{reason:"NON_CANONICAL_SPACING"}:{value:n};}export function verifySyntaxAndPolicy(msg){const rej=(r)=>({status:"REJECTED",reason:r,domains:[],fields:{}});if(!msg)return rej("EMPTY_MESSAGE");const lines=msg.replace(/\r\n/g,"\n").replace(/\r/g,"\n").split("\n"),first=lines.at(0);if(!first)return rej("EMPTY_MESSAGE");if(/^[\s\u000b\u000c\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\u001c-\u001f]/.test(msg))return rej("LEADING_WHITESPACE");if(/[\s\u000b\u000c\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\u001c-\u001f]$/.test(first))return rej("TRAILING_WHITESPACE");const be=scanBody(lines.slice(1));if(be)return rej(be);const m=/^(\[H::[A-Z]{3}\]) (.+) -> emit=([A-Z0-9_]+)$/.exec(first);if(!m){const p=/^\[H::([A-Z]{3})\]/.exec(first);return rej(p&&!ALLOWED_DOMAINS.has(p.at(1))?"UNKNOWN_DOMAIN":"INVALID_HEADER_SYNTAX");}const dom=m.at(1).slice(4,7),act=m.at(3);if(!ALLOWED_DOMAINS.has(dom))return rej("UNKNOWN_DOMAIN");const fields={};for(const tok of m.at(2).split(" | ")){if(!tok||tok!==tok.trim())return rej("NON_CANONICAL_SPACING");const eq=tok.indexOf("=");if(eq!==-1&&(tok.slice(0,eq)!==tok.slice(0,eq).trim()||tok.slice(eq+1)!==tok.slice(eq+1).trim()))return rej("NON_CANONICAL_SPACING");if(tok.startsWith("[H::"))return rej("MULTIPLE_PRIMARY_TAGS");if(eq===-1)return rej("MALFORMED_KV_PAIR");const k=tok.slice(0,eq),v=tok.slice(eq+1);if(!k||!v)return rej("EMPTY_KEY_OR_VALUE");if(!KEY_RE.test(k))return rej("INVALID_KEY_NAME");if(RESERVED_KEYS.has(k))return rej("RESERVED_KEY_NAME");if(Object.prototype.hasOwnProperty.call(fields,k))return rej("DUPLICATE_KEY");if(v.includes("[H::"))return rej("RAW_TAG_IN_VALUE");if(v.includes("|")||v.includes("=")||v.includes("->"))return rej("UNESCAPED_DELIMITER");const dec=decodeValue(v);if(dec.reason)return rej(dec.reason);fields[k]=dec.value;}return MATRIX[dom].has(act)?{status:"PASS",reason:"PASS",domains:[dom],action:act,fields}:rej("ACTION_NOT_ALLOWED_FOR_DOMAIN");}
const ED25519_P = (1n << 255n) - 19n;
const ED25519_L = (1n << 252n) + 27742317777372353535851937790883648493n;
const ED25519_D = 37095705934669439343138083508754565189542113879843219016388785533085940283555n;
const ED25519_SPKI_PREFIX = Buffer.from("302a300506032b6570032100", "hex");
const HIGH_TRUST_DOMAINS = new Set(["AUD", "ETH", "ERR"]);

function modP(n) { const r = n % ED25519_P; return r >= 0n ? r : r + ED25519_P; }
function modPow(base, exp, mod) {
  let res = 1n, b = base % mod, e = exp;
  while (e > 0n) { if (e & 1n) res = (res * b) % mod; b = (b * b) % mod; e >>= 1n; }
  return res;
}
function bytesToBigIntLE(buf) {
  let out = 0n;
  for (let i = 0; i < buf.length; i++) out |= BigInt(buf[i]) << (8n * BigInt(i));
  return out;
}

export function isValidEd25519PublicKeyHex(pubHex) {
  if (typeof pubHex !== "string" || !/^[0-9a-f]{64}$/i.test(pubHex)) return false;
  const raw = Buffer.from(pubHex, "hex");
  const signBit = (raw[31] >> 7) & 1;
  const yBytes = Buffer.from(raw);
  yBytes[31] &= 0x7f;
  const y = bytesToBigIntLE(yBytes);
  if (y >= ED25519_P) return false;
  const y2 = modP(y * y), u = modP(y2 - 1n), v = modP(ED25519_D * y2 + 1n);
  const v3 = modP(v * v * v), v7 = modP(v3 * v3 * v);
  let x = modP(u * v3 * modPow(modP(u * v7), (ED25519_P - 5n) / 8n, ED25519_P));
  if (modP(v * x * x) !== u) {
    x = modP(x * modPow(2n, (ED25519_P - 1n) / 4n, ED25519_P));
    if (modP(v * x * x) !== u) return false;
  }
  if (x === 0n && signBit === 1) return false;
  if ((x & 1n) !== BigInt(signBit)) x = modP(ED25519_P - x);
  if (x === 0n && y === 1n) return false;
  const edAdd = (P, Q) => {
    const [x1, y1, z1, t1] = P, [x2, y2, z2, t2] = Q;
    const A = modP((y1 - x1) * (y2 - x2)), B = modP((y1 + x1) * (y2 + x2));
    const C = modP(t1 * 2n * ED25519_D * t2), D = modP(z1 * 2n * z2);
    const E = modP(B - A), F = modP(D - C), G = modP(D + C), H = modP(B + A);
    return [modP(E * F), modP(G * H), modP(F * G), modP(E * H)];
  };
  let P = [x, y, 1n, modP(x * y)];
  P = edAdd(P, P); P = edAdd(P, P); P = edAdd(P, P);
  return !(P[0] === 0n && P[1] === P[2]);
}

export function verifyHeaderSignature(unsignedHeader, sigHex, pubHex) {
  if (!isValidEd25519PublicKeyHex(pubHex)) return false;
  if (typeof sigHex !== "string" || !/^[0-9a-f]{128}$/i.test(sigHex)) return false;
  const sigBuf = Buffer.from(sigHex, "hex");
  if (bytesToBigIntLE(sigBuf.subarray(32, 64)) >= ED25519_L) return false;
  try {
    const der = Buffer.concat([ED25519_SPKI_PREFIX, Buffer.from(pubHex, "hex")]);
    const keyObj = crypto.createPublicKey({ key: der, format: "der", type: "spki" });
    return crypto.verify(null, Buffer.from(unsignedHeader, "utf8"), keyObj, sigBuf);
  } catch { return false; }
}

export function canonicalizeTextBytes(text) {
  return Buffer.from(text.normalize("NFC").replaceAll("\r\n", "\n").replaceAll("\r", "\n"), "utf8");
}

export function verifyMessage(message, opts = {}) {
  const { trustedKeys = null, expectedAudience = null, seenNonces = null, nowTs = null, maxClockSkew = 300 } = opts;
  const syn = verifySyntaxAndPolicy(message);
  if (syn.reason !== "PASS") return { status: "REJECTED", reason: syn.reason };
  const lines = message.split("\n");
  const hdr = lines[0];
  const m = hdr.match(/^(\[H::[A-Z]{3}\])\s+(.+?)\s+->\s+emit=([A-Z][A-Z0-9_]*)$/);
  const dom = m[1].slice(4, -1), action = m[3];
  const pairs = m[2].split(" | ");
  const fields = {}, unsignedParts = [];
  for (const p of pairs) {
    const idx = p.indexOf("="), k = p.slice(0, idx), v = p.slice(idx + 1);
    fields[k] = v;
    if (k !== "sig") unsignedParts.push(p);
  }
  if ("ts" in fields) {
    if (!/^[0-9]{10,13}$/.test(fields.ts)) return { status: "REJECTED", reason: "INVALID_TIMESTAMP_FORMAT" };
    const now = nowTs === null ? Math.floor(Date.now() / 1000) : nowTs;
    const tsVal = fields.ts.length === 13 ? Math.floor(Number(fields.ts) / 1000) : Number(fields.ts);
    if (Math.abs(now - tsVal) > maxClockSkew) return { status: "REJECTED", reason: "EXPIRED_OR_FUTURE_TIMESTAMP" };
  }
  if ("sha256" in fields && !/^[0-9a-f]{64}$/.test(fields.sha256)) return { status: "REJECTED", reason: "INVALID_SHA256_FORMAT" };
  if ("sig" in fields && !/^[0-9a-f]{128}$/.test(fields.sig)) return { status: "REJECTED", reason: "INVALID_SIGNATURE_FORMAT" };
  const bodyText = lines.slice(1).join("\n");
  if (bodyText.length > 0 && !("sha256" in fields)) return { status: "REJECTED", reason: "BODY_SHA256_REQUIRED" };
  if ("sha256" in fields) {
    const actualSha = crypto.createHash("sha256").update(canonicalizeTextBytes(bodyText)).digest("hex");
    if (actualSha !== fields.sha256) return { status: "REJECTED", reason: "SHA256_MISMATCH" };
  }
  if (HIGH_TRUST_DOMAINS.has(dom) && !("sig" in fields)) return { status: "REJECTED", reason: "SIGNATURE_REQUIRED_FOR_DOMAIN" };
  if ("sig" in fields) {
    if (!trustedKeys || !("kid" in fields) || !Object.hasOwn(trustedKeys, fields.kid)) return { status: "UNVERIFIED", reason: "UNTRUSTED_OR_MISSING_KEY" };
    if (expectedAudience !== null && fields.aud !== expectedAudience) return { status: "REJECTED", reason: "AUDIENCE_MISMATCH" };
    if ("nonce" in fields && seenNonces !== null) {
      const nk = `${trustedKeys[fields.kid]}:${fields.kid}:${fields.nonce}`;
      if (seenNonces.has(nk)) return { status: "REJECTED", reason: "REPLAY_DETECTED" };
    }
    const unsignedHeader = `${m[1]} ${unsignedParts.join(" | ")} -> emit=${action}`;
    if (!verifyHeaderSignature(unsignedHeader, fields.sig, trustedKeys[fields.kid])) return { status: "REJECTED", reason: "INVALID_SIGNATURE_OR_KEY" };
    if ("nonce" in fields && seenNonces !== null) seenNonces.add(`${trustedKeys[fields.kid]}:${fields.kid}:${fields.nonce}`);
    return { status: "VALID", reason: "sha256" in fields ? "VERIFIED_WITH_ED25519_AND_SHA256" : "VERIFIED_WITH_ED25519", domains: [dom], action };
  }
  if ("sha256" in fields) return { status: "VALID", reason: "VERIFIED_WITH_SHA256", domains: [dom], action };
  return { status: "WELL_FORMED", reason: "HEADER_SYNTAX_OK", domains: [dom], action };
}
