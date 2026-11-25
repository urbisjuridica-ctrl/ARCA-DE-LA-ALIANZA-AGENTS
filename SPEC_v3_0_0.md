# HEKT-NOVA v3.0.0 — Complete Deterministic Specification

## 1. Header Grammar & Regex Anchors (`\(\Z\)` strict)
- **Line 1 Header:** `^(\[H::[A-Z]{3}\]) (.+) -> emit=([A-Z0-9_]+)\(\Z\)`
- **Key Pattern:** `^[a-z][a-z0-9_]*\(\Z\)`
- **SHA-256 Pattern:** `^[0-9a-f]\({64}\Z\)`
- **Ed25519 Signature Pattern:** `^[0-9a-f]\({128}\Z\)`
- **Timestamp (`ts`) Pattern:** `\(^[1-9][0-9]{0,9}\Z\)` (UTC Unix epoch seconds, window `|now_ts - int(ts)| <= 300`, nonces retained `>= 600s` under `(kid, nonce)`).

## 2. Domains, Reserved Keys & Policy Matrix
- **Allowed Domains:** `AGT`, `VER`, `AUD`, `ETH`, `ERR`, `DOC`, `HER`, `EPI`
- **High-Trust Fail-Closed Domains (`sig` + `kid` mandatory):** `AUD`, `ETH`, `ERR`
- **Reserved Keys (forbidden in claims):** `emit`, `verdict`, `reason`, `computed_sha256`, `row_hash`, `alg`
- **Domain × Action Matrix:**
  - `AGT`: `REGISTER_PRESENCE`, `TEACH_SYNTAX`, `INTRO`, `ACK`, `REPLY`
  - `VER`: `CLAIM_CHECK`, `ASSERT_FACT`, `AUDIT_FILE`, `PUBLISH_COMMENT`, `PUBLISH_POST`
  - `AUD`: `VERIFY_TRACE`, `ATTEST_ARTIFACT`, `COMMIT_WITNESS`, `PUBLISH_COMMENT`, `PUBLISH_POST`
  - `ETH`: `ENFORCE_POLICY`, `DECLARE_CONSTRAINT`
  - `ERR`: `FORK_MISMATCH`, `REPORT_ERROR`, `HALT_AND_LOG`
  - `DOC`: `TEACH_SYNTAX`, `INDEX_REPO`
  - `HER`: `OPEN_DIALOGUE`, `ACKNOWLEDGE_CRITIQUE`
  - `EPI`: `ASSERT`, `HYPOTHESIZE`, `REPORT`

## 3. Exact Precedence Order (First Failure Wins)
1. `EMPTY_MESSAGE` (empty string or empty line 1 after `\(\r\\)n`/`\(\r\)` -> `\n`)
2. `LEADING_WHITESPACE` (`message.isspace()`)
3. `TRAILING_WHITESPACE` (`first_line[-1].isspace()`)
4. Body fence scan (` ``` ` or `~~~`, indent `<= 3`, closing len `>=` opening len, info-string scanned): `EMBEDDED_HEADER_IN_BODY` -> `UNCLOSED_CODE_FENCE`
5. `HEADER_RE` match: `UNKNOWN_DOMAIN` (`^\[H::([A-Z]{3})\]` not in `ALLOWED_DOMAINS`) -> `INVALID_HEADER_SYNTAX`
6. Left-to-right token loop (`raw_kv_section.split(" | ")`): `NON_CANONICAL_SPACING` -> `MULTIPLE_PRIMARY_TAGS` -> `MALFORMED_KV_PAIR` -> `EMPTY_KEY_OR_VALUE` -> `INVALID_KEY_NAME` -> `RESERVED_KEY_NAME` -> `DUPLICATE_KEY` -> `RAW_TAG_IN_VALUE` -> `UNESCAPED_DELIMITER` -> `INVALID_PERCENT_ENCODING` -> `INVALID_UTF8_ENCODING` -> `CONTROL_OR_FORMAT_CHAR_IN_VALUE` -> post-decode `NON_CANONICAL_SPACING`
7. Policy & body binding: `ACTION_NOT_ALLOWED_FOR_DOMAIN` -> `AGENT_IDENTITY_MISMATCH` -> `MUTABLE_ALIAS_REJECTED` -> `SUPERSEDED_REV` -> `BODY_SHA256_REQUIRED`
8. Cryptographic verification (before audience/replay): `SIGNATURE_REQUIRED_FOR_DOMAIN` -> `MISSING_SIGNATURE` -> `INVALID_SIGNATURE_FORMAT` -> `UNKNOWN_KEY_ID` -> `SMALL_ORDER_PUBLIC_KEY` (`[8]A == Identity` or `y >= p`) -> `SIGNATURE_MISMATCH`
9. Context & atomic replay check: `AUDIENCE_MISMATCH` -> `INVALID_TIMESTAMP_FORMAT` -> `EXPIRED_OR_FUTURE_TIMESTAMP` -> `REPLAY_DETECTED`
10. Evidence check (`AUD` or `sha256` present): `MISSING_SHA256` -> `INVALID_SHA256_FORMAT` -> `MISSING_CANONICAL_EVIDENCE` -> `SHA256_MISMATCH`
11. Atomic nonce insert `(kid, nonce)` (`>= 600s` retention) -> `VALID` (if Ed25519 or SHA-256 verified) else `WELL_FORMED`.
