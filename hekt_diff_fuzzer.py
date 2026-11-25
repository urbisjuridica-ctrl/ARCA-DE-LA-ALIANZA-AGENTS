#!/usr/bin/env python3
"""Differential fuzzer for the HEKT-NOVA v3.0.0 syntax + action-policy stage.

Compares an independent reference parser (written from the maintainer's v2.9/v3.0 notes, NOT from
hekt_external_verifier.py) with your verify_message(), and prints only the disagreements.

Run locally (the sandbox cannot call your verifier):
    python3 hekt_diff_fuzzer.py --impl hekt_external_verifier:verify_message --n 200000 --seed 1
    python3 hekt_diff_fuzzer.py --selftest          # reference vs itself: must print 0 mismatches
    python3 hekt_diff_fuzzer.py --mutants           # planted bugs: shows the fuzzer can find them

Scope: only the syntax stage (spec steps 1-6) and ACTION_NOT_ALLOWED_FOR_DOMAIN. If your verifier
returns a state/crypto reason (replay, signature, body sha256...) the syntax stage passed, so it is
normalised to PASS. Keys ts/sig/sha256/kid/nonce/aud are deliberately not generated.
Rules I had to guess are marked  # GUESS  -- a disagreement there means "decide and document", not "bug".
"""
import argparse, collections, importlib, json, random, re, sys, unicodedata
from urllib.parse import unquote_to_bytes

# ------------------------------------------------------------------ reference parser
HEADER_RE = re.compile(r"^(\[H::[A-Z]{3}\]) (.+) -> emit=([A-Z0-9_]+)\Z")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]*\Z")
FENCE_OPEN = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)\Z")
FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*\Z")
BAD_PERCENT = re.compile(r"%(?![0-9A-Fa-f]{2})")
ALLOWED_DOMAINS = {"AGT", "VER", "AUD", "ETH", "ERR", "DOC", "HER", "EPI"}
RESERVED_KEYS = {"emit", "verdict", "reason", "computed_sha256", "row_hash", "alg"}
MATRIX = {
    "AGT": {"REGISTER_PRESENCE", "TEACH_SYNTAX", "INTRO", "ACK", "REPLY"},
    "VER": {"CLAIM_CHECK", "ASSERT_FACT", "AUDIT_FILE", "PUBLISH_COMMENT", "PUBLISH_POST"},
    "AUD": {"VERIFY_TRACE", "ATTEST_ARTIFACT", "COMMIT_WITNESS", "PUBLISH_COMMENT", "PUBLISH_POST"},
    "ETH": {"ENFORCE_POLICY", "DECLARE_CONSTRAINT"},
    "ERR": {"FORK_MISMATCH", "REPORT_ERROR", "HALT_AND_LOG"},
    "DOC": {"TEACH_SYNTAX", "INDEX_REPO"},
    "HER": {"OPEN_DIALOGUE", "ACKNOWLEDGE_CRITIQUE"},
    "EPI": {"ASSERT", "HYPOTHESIZE", "REPORT"},
}
# invisible / blank code points beyond the general categories  # GUESS (v3.0.0 lists only some of these)
EXTRA_RANGES = [(0x034F, 0x034F), (0x115F, 0x1160), (0x17B4, 0x17B5), (0x180B, 0x180F), (0x2800, 0x2800),
                (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFFA0, 0xFFA0), (0x1BCA0, 0x1BCA3),
                (0x1D173, 0x1D17A), (0xE0000, 0xE007F), (0xE0100, 0xE01EF)]
FLAGS_V3 = dict(leading="first_char", probe_upper=True, scan_info=True, strip_after_decode=True,
                reject_zs=True, reject_extra=True)


def forbidden(ch, f):
    cat, cp = unicodedata.category(ch), ord(ch)
    if cat in ("Cc", "Cf", "Zl", "Zp", "Co", "Cs", "Cn"):  # Cn depends on the Unicode version  # GUESS
        return True
    if f["reject_zs"] and cat == "Zs" and ch != " ":
        return True
    return f["reject_extra"] and any(lo <= cp <= hi for lo, hi in EXTRA_RANGES)


def scan_body(body, f):
    fence = None
    for line in body:
        if fence is None:
            m = FENCE_OPEN.match(line)
            if m:
                if f["scan_info"] and "[H::" in m.group(3):
                    return "EMBEDDED_HEADER_IN_BODY"
                fence = (m.group(2)[0], len(m.group(2)))
                continue
            if "[H::" in line:
                return "EMBEDDED_HEADER_IN_BODY"
        else:
            m = FENCE_CLOSE.match(line)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1]:
                fence = None
    return "UNCLOSED_CODE_FENCE" if fence else None


def parse(message, f=FLAGS_V3):
    """Returns 'PASS' or a rejection reason."""
    if message == "":
        return "EMPTY_MESSAGE"
    if f["leading"] == "first_char":
        if message[0].isspace():
            return "LEADING_WHITESPACE"
    elif message.isspace():  # v2.9 literal reading
        return "LEADING_WHITESPACE"
    lines = message.replace("\r\n", "\n").replace("\r", "\n").split("\n")  # split on LF only  # GUESS
    first = lines[0]
    if first == "":
        return "EMPTY_MESSAGE"
    if first[-1].isspace():
        return "TRAILING_WHITESPACE"
    r = scan_body(lines[1:], f)
    if r:
        return r
    m = HEADER_RE.match(first)
    if not m:
        probe = re.match(r"^\[H::([A-Z]{3})\]" if f["probe_upper"] else r"^\[H::([A-Za-z]{3})\]", first)
        if probe and probe.group(1) not in ALLOWED_DOMAINS:
            return "UNKNOWN_DOMAIN"
        return "INVALID_HEADER_SYNTAX"
    tag, section, action = m.groups()
    dom = tag[4:7]
    if dom not in ALLOWED_DOMAINS:
        return "UNKNOWN_DOMAIN"
    seen = set()
    for tok in section.split(" | "):
        if tok == "" or tok != tok.strip():
            return "NON_CANONICAL_SPACING"
        if "=" in tok:
            k0, v0 = tok.split("=", 1)
            if k0 != k0.strip() or v0 != v0.strip():
                return "NON_CANONICAL_SPACING"
        if tok.startswith("[H::"):
            return "MULTIPLE_PRIMARY_TAGS"
        if "=" not in tok:
            return "MALFORMED_KV_PAIR"
        key, val = tok.split("=", 1)
        if not key or not val:
            return "EMPTY_KEY_OR_VALUE"
        if not KEY_RE.match(key):
            return "INVALID_KEY_NAME"
        if key in RESERVED_KEYS:
            return "RESERVED_KEY_NAME"
        if key in seen:
            return "DUPLICATE_KEY"
        seen.add(key)
        if "[H::" in val:
            return "RAW_TAG_IN_VALUE"
        if "|" in val or "=" in val or "->" in val:
            return "UNESCAPED_DELIMITER"
        if BAD_PERCENT.search(val):
            return "INVALID_PERCENT_ENCODING"
        try:
            dec = unquote_to_bytes(val).decode("utf-8")
        except UnicodeDecodeError:
            return "INVALID_UTF8_ENCODING"
        if any(forbidden(c, f) for c in dec):  # control check before the strip check  # GUESS
            return "CONTROL_OR_FORMAT_CHAR_IN_VALUE"
        norm = unicodedata.normalize("NFC", dec)
        if f["strip_after_decode"] and norm != norm.strip():
            return "NON_CANONICAL_SPACING"
    return "PASS" if action in MATRIX[dom] else "ACTION_NOT_ALLOWED_FOR_DOMAIN"


# ------------------------------------------------------------------ adapter for your verifier
IN_SCOPE = {"EMPTY_MESSAGE", "LEADING_WHITESPACE", "TRAILING_WHITESPACE", "EMBEDDED_HEADER_IN_BODY",
            "UNCLOSED_CODE_FENCE", "UNKNOWN_DOMAIN", "INVALID_HEADER_SYNTAX", "NON_CANONICAL_SPACING",
            "MULTIPLE_PRIMARY_TAGS", "MALFORMED_KV_PAIR", "EMPTY_KEY_OR_VALUE", "INVALID_KEY_NAME",
            "RESERVED_KEY_NAME", "DUPLICATE_KEY", "RAW_TAG_IN_VALUE", "UNESCAPED_DELIMITER",
            "INVALID_PERCENT_ENCODING", "INVALID_UTF8_ENCODING", "CONTROL_OR_FORMAT_CHAR_IN_VALUE",
            "ACTION_NOT_ALLOWED_FOR_DOMAIN"}
OUT_OF_SCOPE = {"BODY_SHA256_REQUIRED", "AUDIENCE_MISMATCH", "REPLAY_DETECTED", "AGENT_IDENTITY_MISMATCH",
                "MUTABLE_ALIAS_REJECTED", "SUPERSEDED_REV", "SIGNATURE_REQUIRED_FOR_DOMAIN", "MISSING_SIGNATURE",
                "UNKNOWN_KEY_ID", "SMALL_ORDER_PUBLIC_KEY", "SIGNATURE_MISMATCH", "MISSING_SHA256",
                "INVALID_SHA256_FORMAT", "MISSING_CANONICAL_EVIDENCE", "SHA256_MISMATCH",
                "INVALID_SIGNATURE_FORMAT", "INVALID_TIMESTAMP_FORMAT"}
PASS_VERDICTS = {"VALID", "WELL_FORMED", "UNVERIFIED"}


def to_pair(res):
    """Best-effort: turn whatever verify_message returns into (verdict, reason). Edit if yours differs."""
    if isinstance(res, tuple):
        return str(res[0]), str(res[1]) if len(res) > 1 else ""
    if isinstance(res, dict):
        return str(res.get("verdict", "")), str(res.get("reason", ""))
    if hasattr(res, "verdict"):
        return str(res.verdict), str(getattr(res, "reason", ""))
    if hasattr(res, "to_json"):
        d = json.loads(res.to_json())
        return str(d.get("verdict", "")), str(d.get("reason", ""))
    m = re.match(r"^\s*([A-Z_]+)\s*[\(|]\s*([A-Z0-9_]+)", str(res))  # "REJECTED (X)" or "VALID | X"
    return (m.group(1), m.group(2)) if m else (str(res), "")


def normalise(verdict, reason, extra_oos):
    if verdict in PASS_VERDICTS:
        return "PASS"
    if reason in IN_SCOPE:
        return reason
    if reason in OUT_OF_SCOPE or reason in extra_oos:
        return "PASS"  # syntax stage passed; a later stage rejected
    return "UNKNOWN_REASON:" + reason


def make_impl(spec, kwargs, extra_oos):
    mod, fn = spec.split(":")
    f = getattr(importlib.import_module(mod), fn)

    def call(msg):
        try:
            return normalise(*to_pair(f(msg, **kwargs)), extra_oos)
        except Exception as e:  # an exception on hostile input is itself a finding
            return "IMPL_EXCEPTION:" + type(e).__name__
    return call


# ------------------------------------------------------------------ generator
DOMS = sorted(ALLOWED_DOMAINS)
BAD_DOMS = ["ver", "Ver", "XYZ", "VE", "VERS", "A1T", ""]
ACTS = sorted({a for s in MATRIX.values() for a in s})
BAD_ACTS = ["", "intro", "BAD-ACT", "INTRO ", "OPEN_DIALOGUE", "REPORT"]
KEYS_OK = ["claim", "note", "refs", "peer", "name", "origin", "proto", "a", "a1", "x_y"]
KEYS_BAD = ["Bad-Key", "1a", "a-b", "a b", "A", "_a", "claim ", " claim", "verdict", "reason", "emit", "alg",
            "computed_sha256", "row_hash", "refs", "claim"]
VALS_OK = ["x", "hello", "AGT,VER", "claude-sonnet-5-5", "v2.4.0", "a%20b", "a b", "caf%C3%A9", "cafe%CC%81", "café"]
VALS_TRICKY = [
    "a|b", "a=b", "a->b", "a%7Cb%3Dc", "[H::AUD]", "[H::aud]", "%5BH::AUD%5D", "%255BH::AUD%255D", "a%0A[H::AUD]",
    "a%0A%5BH::AUD%5D", "%00", "%09", "a%0Ab", "%ZZ", "%", "%2", "%G1", "%FF", "%C0%AF", "%ED%A0%80", "%e2%80%8b",
    "a%E2%80%8Bb", "a%E2%80%A8b", "a%E2%80%AEb", "a%C2%85b", "a%EF%B8%8Fb", "a%EE%80%80b", "a%F3%A0%81%81b",
    "a%E2%81%A0b", "a%C2%A0b", "a%C2%A0", "%20a", "a%20", "%20", "a%CD%8Fb", "a%E1%A0%8Bb", "a%E3%85%A4b",
    "a%E2%A0%80b", "a%EF%BF%BFb", "a%CE%B8b", "\u200bx", "x\u200b", "a\tb", "a\u00a0b", "a\u2028b", "\uff1d", "",
    " ", "x ", " x", "ａｂ", "\u0435", "x\x00y",
]
ARROWS = [" ->emit=%s", "-> emit=%s", " -> emit =%s", " - > emit=%s", " \u2192 emit=%s", " -> emit=%s -> emit=%s",
          " -> EMIT=%s", " -> emit=%s ", "  -> emit=%s", " -> emit=%s\u200b"]
SEPS = [" |", "| ", "|", " |  ", "  | ", "\t| ", " | | ", " ||"]
HEADS = ["[H::%s]", "[H:: %s]", "[H::%s ]", "[h::%s]", "[H:%s]", "[[H::%s]]", "[H::%s]]", "H::%s", "\uff3bH::%s\uff3d"]
EDGE = ["", " ", "\t", "\n", "\r", "\r\n", "\u00a0", "\u200b", "\ufeff", "\u2028", "\u0085", "\x0b", "\x0c", "\x00",
        "\x1b", "\u3000"]
BODY_LINES = ["text", "```", "~~~", "````", "~~~~", "  ```", "   ~~~", "    ```", "```js", "``` ", "~~~ x",
              "[H::AUD] k=v", "x [H::VER]", "```[H::AUD]", "~~~[H::AUD] k=v", "   [H::AUD]", "", " ", "`",
              "\u2028[H::AUD]", "[h::AUD]", "[H::"]
INSERT = ["\x00", "\t", "\x0b", "\x0c", "\x1c", "\x1f", " ", "\x7f", "\x85", "\xa0", "\u034f", "\u180b", "\u200b",
          "\u200e", "\u2028", "\u2029", "\u202e", "\u2060", "\u2800", "\u3164", "\ufe0f", "\ufeff", "\uffff", "\ue000",
          "\U000e0041", "|", "=", "->", "[", "]", "%", "%2", "\n", "\r", "\r\n", "`", "~", "\uff3b", "\uff3d", "\u00e9",
          "\u0435", " | ", " -> emit=", "[H::AUD]"]


def gen_structured(r):
    dom = r.choice(DOMS) if r.random() < 0.9 else r.choice(BAD_DOMS)
    pairs = []
    for _ in range(r.choice([0, 1, 1, 2, 2, 3, 4])):
        k = r.choice(KEYS_OK) if r.random() < 0.85 else r.choice(KEYS_BAD)
        v = r.choice(VALS_OK) if r.random() < 0.55 else r.choice(VALS_TRICKY)
        p = f"{k}={v}"
        x = r.random()
        if x < 0.03:
            p = k
        elif x < 0.05:
            p = "[H::AUD] " + p
        pairs.append(p)
    sep = " | " if r.random() < 0.85 else r.choice(SEPS)
    section = sep.join(pairs)
    act = r.choice(ACTS) if r.random() < 0.75 else r.choice(BAD_ACTS)
    arrow = " -> emit=%s" if r.random() < 0.9 else r.choice(ARROWS)
    head = "[H::%s]" if r.random() < 0.95 else r.choice(HEADS)
    msg = (head % dom) + " " + section + (arrow % ((act,) * arrow.count("%s")))
    if r.random() < 0.15:
        msg = r.choice(EDGE) + msg
    if r.random() < 0.15:
        msg = msg + r.choice(EDGE)
    if r.random() < 0.35:
        body = [r.choice(BODY_LINES) for _ in range(r.randint(1, 5))]
        msg += r.choice(["\n", "\r\n", "\r"]) + "\n".join(body)
    return msg


def mutate(r, s):
    for _ in range(r.randint(1, 3)):
        if not s:
            s = r.choice(INSERT)
            continue
        i = r.randrange(len(s) + 1)
        op = r.random()
        if op < 0.6:
            s = s[:i] + r.choice(INSERT) + s[i:]
        elif op < 0.8 and i < len(s):
            s = s[:i] + s[i + 1:]
        elif op < 0.9 and i < len(s):
            j = min(len(s), i + r.randint(1, 8))
            s = s[:j] + s[i:j] + s[j:]
        else:
            s = s[:i]
    return s


def gen(r):
    s = gen_structured(r)
    x = r.random()
    return mutate(r, s) if x < 0.4 else s


# ------------------------------------------------------------------ driver
def describe(s):
    odd = sorted({c for c in s if ord(c) > 126 or ord(c) < 32})
    return " ".join(f"U+{ord(c):04X}({unicodedata.category(c)})" for c in odd[:6])


def run(impl, n, seed, flags, max_ex):
    r = random.Random(seed)
    buckets = collections.defaultdict(lambda: [0, []])
    for _ in range(n):
        msg = gen(r)
        ref, got = parse(msg, flags), impl(msg)
        if ref != got:
            b = buckets[(ref, got)]
            b[0] += 1
            if len(b[1]) < max_ex:
                b[1].append(msg)
    return buckets


def severity(ref, got):
    if ref != "PASS" and got == "PASS":
        return 0  # your verifier accepts something the reference rejects
    if got.startswith("IMPL_EXCEPTION"):
        return 1
    if ref == "PASS":
        return 2  # your verifier rejects something the reference accepts
    return 3  # both reject, different reasons


def report(buckets, n, label, as_json=None):
    total = sum(c for c, _ in buckets.values())
    print(f"\n== {label}: {n} messages, {total} mismatches in {len(buckets)} distinct (reference, impl) pairs ==")
    names = {0: "IMPL ACCEPTS, REFERENCE REJECTS", 1: "IMPL EXCEPTION", 2: "IMPL REJECTS, REFERENCE ACCEPTS",
             3: "BOTH REJECT, DIFFERENT REASON"}
    rows = sorted(buckets.items(), key=lambda kv: (severity(*kv[0]), -kv[1][0]))
    last = None
    for (ref, got), (cnt, ex) in rows:
        sv = severity(ref, got)
        if sv != last:
            print(f"\n-- {names[sv]} --")
            last = sv
        print(f"[{cnt:6}x] reference={ref}  impl={got}")
        for m in ex:
            print(f"           {m[:140]!r}  {describe(m)}")
    if as_json:
        with open(as_json, "w") as fh:
            json.dump([{"reference": a, "impl": b, "count": c, "examples": e} for (a, b), (c, e) in rows], fh, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", default="hekt_external_verifier:verify_message")
    ap.add_argument("--impl-kwargs", default="{}", help='JSON, e.g. \'{"trusted_keys": {}}\'')
    ap.add_argument("--extra-out-of-scope", default="", help="comma-separated extra reasons from later stages")
    ap.add_argument("--n", type=int, default=100000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--max-examples", type=int, default=3)
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--mutants", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        report(run(lambda m: parse(m), a.n, a.seed, FLAGS_V3, a.max_examples), a.n, "selftest (expect 0)")
        return
    if a.mutants:
        planted = {"v2.9 leading-whitespace rule": dict(FLAGS_V3, leading="whole"),
                   "case-insensitive domain probe": dict(FLAGS_V3, probe_upper=False),
                   "fence info string not scanned": dict(FLAGS_V3, scan_info=False),
                   "no post-decode strip check": dict(FLAGS_V3, strip_after_decode=False),
                   "NBSP/Zs allowed": dict(FLAGS_V3, reject_zs=False),
                   "extra invisibles allowed": dict(FLAGS_V3, reject_extra=False)}
        for name, fl in planted.items():
            b = run(lambda m, fl=fl: parse(m, fl), a.n, a.seed, FLAGS_V3, 1)
            print(f"mutant '{name}': {sum(c for c, _ in b.values())} mismatches in {len(b)} pairs",
                  "-> detected" if b else "-> MISSED")
        return
    extra = {x for x in a.extra_out_of_scope.split(",") if x}
    impl = make_impl(a.impl, json.loads(a.impl_kwargs), extra)
    report(run(impl, a.n, a.seed, FLAGS_V3, a.max_examples), a.n, "reference vs " + a.impl, a.json)


if __name__ == "__main__":
    main()
