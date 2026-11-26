const KEY_RE = /^[a-z][a-z0-9_]*$/;
const FENCE_OPEN = /^( {0,3})(`{3,}|~{3,})(.*)$/;
const FENCE_CLOSE = /^ {0,3}(`{3,}|~{3,})[ \t]*$/;
const BAD_PERCENT = /%(?![0-9A-Fa-f]{2})/;
const ALLOWED_DOMAINS = new Set(["AGT", "VER", "AUD", "ETH", "ERR", "DOC", "HER", "EPI"]);
const RESERVED_KEYS = new Set(["emit", "verdict", "reason", "computed_sha256", "row_hash", "alg"]);
const MATRIX = { AGT: new Set(["REGISTER_PRESENCE", "TEACH_SYNTAX", "INTRO", "ACK", "REPLY"]), VER: new Set(["CLAIM_CHECK", "ASSERT_FACT", "AUDIT_FILE", "PUBLISH_COMMENT", "PUBLISH_POST"]), AUD: new Set(["VERIFY_TRACE", "ATTEST_ARTIFACT", "COMMIT_WITNESS", "PUBLISH_COMMENT", "PUBLISH_POST"]), ETH: new Set(["ENFORCE_POLICY", "DECLARE_CONSTRAINT"]), ERR: new Set(["FORK_MISMATCH", "REPORT_ERROR", "HALT_AND_LOG"]), DOC: new Set(["TEACH_SYNTAX", "INDEX_REPO"]), HER: new Set(["OPEN_DIALOGUE", "ACKNOWLEDGE_CRITIQUE"]), EPI: new Set(["ASSERT", "HYPOTHESIZE", "REPORT"]) };
const utf8Fatal = new TextDecoder("utf-8", { fatal: true });

function isForbiddenChar(ch) {
  const cp = ch.codePointAt(0);
  if (/\p{Cc}|\p{Cf}|\p{Zl}|\p{Zp}|\p{Co}|\p{Cs}/u.test(ch) || (/\p{Zs}/u.test(ch) && cp !== 0x20)) return true;
  if (cp === 0x034f || cp === 0x2800 || cp === 0x3164 || cp === 0xffa0 || (cp >= 0x180b && cp <= 0x180f) || (cp & 0xffff) === 0xfffe || (cp & 0xffff) === 0xffff) return true;
  return (cp >= 0xfe00 && cp <= 0xfe0f) || (cp >= 0xe0100 && cp <= 0xe01ef) || (cp >= 0xe0000 && cp <= 0xe007f);
}

function scanBody(bodyLines) {
  let fence = null;
  for (const line of bodyLines) {
    if (fence === null) {
      const m = FENCE_OPEN.exec(line);
      if (m) { if (m.at(3).includes("[H::")) return "EMBEDDED_HEADER_IN_BODY"; fence = { ch: m.at(2).at(0), len: m.at(2).length }; continue; }
      if (line.includes("[H::")) return "EMBEDDED_HEADER_IN_BODY";
    } else { const m = FENCE_CLOSE.exec(line); if (m && m.at(1).at(0) === fence.ch && m.at(1).length >= fence.len) fence = null; }
  }
  return fence ? "UNCLOSED_CODE_FENCE" : null;
}

function decodeValue(raw) {
  if (BAD_PERCENT.test(raw)) return { reason: "INVALID_PERCENT_ENCODING" };
  const bytes = [];
  for (let i = 0; i < raw.length; i++) { if (raw.at(i) === "%") { bytes.push(parseInt(raw.slice(i + 1, i + 3), 16)); i += 2; } else { for (const b of new TextEncoder().encode(raw.at(i))) bytes.push(b); } }
  let decoded; try { decoded = utf8Fatal.decode(new Uint8Array(bytes)); } catch { return { reason: "INVALID_UTF8_ENCODING" }; }
  for (const ch of decoded) if (isForbiddenChar(ch)) return { reason: "CONTROL_OR_FORMAT_CHAR_IN_VALUE" };
  const nfc = decoded.normalize("NFC");
  return nfc !== nfc.trim() ? { reason: "NON_CANONICAL_SPACING" } : { value: nfc };
}

export function verifySyntaxAndPolicy(message) {
  const rej = (reason) => ({ status: "REJECTED", reason, domains: [], fields: {} });
  if (!message) return rej("EMPTY_MESSAGE");
  const lines = message.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n"), first = lines.at(0);
  if (!first) return rej("EMPTY_MESSAGE");
  if (/^[\s\u000b\u000c\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\u001c-\u001f]/.test(message)) return rej("LEADING_WHITESPACE");
  if (/[\s\u000b\u000c\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\u001c-\u001f]$/.test(first)) return rej("TRAILING_WHITESPACE");
  const bodyErr = scanBody(lines.slice(1)); if (bodyErr) return rej(bodyErr);
  const m = /^(\[H::[A-Z]{3}\]) (.+) -> emit=([A-Z0-9_]+)$/.exec(first);
  if (!m) { const p = /^\[H::([A-Z]{3})\]/.exec(first); return rej(p && !ALLOWED_DOMAINS.has(p.at(1)) ? "UNKNOWN_DOMAIN" : "INVALID_HEADER_SYNTAX"); }
  const domain = m.at(1).slice(4, 7), action = m.at(3); if (!ALLOWED_DOMAINS.has(domain)) return rej("UNKNOWN_DOMAIN");
  const fields = {};
  for (const token of m.at(2).split(" | ")) {
    if (!token || token !== token.trim()) return rej("NON_CANONICAL_SPACING");
    const eq = token.indexOf("=");
    if (eq !== -1 && (token.slice(0, eq) !== token.slice(0, eq).trim() || token.slice(eq + 1) !== token.slice(eq + 1).trim())) return rej("NON_CANONICAL_SPACING");
    if (token.startsWith("[H::")) return rej("MULTIPLE_PRIMARY_TAGS");
    if (eq === -1) return rej("MALFORMED_KV_PAIR");
    const key = token.slice(0, eq), val = token.slice(eq + 1);
    if (!key || !val) return rej("EMPTY_KEY_OR_VALUE");
    if (!KEY_RE.test(key)) return rej("INVALID_KEY_NAME");
    if (RESERVED_KEYS.has(key)) return rej("RESERVED_KEY_NAME");
    if (Object.prototype.hasOwnProperty.call(fields, key)) return rej("DUPLICATE_KEY");
    if (val.includes("[H::")) return rej("RAW_TAG_IN_VALUE");
    if (val.includes("|") || val.includes("=") || val.includes("->")) return rej("UNESCAPED_DELIMITER");
    const dec = decodeValue(val); if (dec.reason) return rej(dec.reason);
    fields[key] = dec.value;
  }
  return MATRIX[domain].has(action) ? { status: "PASS", reason: "PASS", domains: [domain], action, fields } : rej("ACTION_NOT_ALLOWED_FOR_DOMAIN");
}
