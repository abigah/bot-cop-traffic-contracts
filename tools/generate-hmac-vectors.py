#!/usr/bin/env python3
"""Regenerate v1/hmac/vectors.json.

The vectors are derived from the example payloads, so if an example changes the
signatures must be regenerated. Run from the repository root:

    python3 tools/generate-hmac-vectors.py

Nothing here is a secret: the keys are fixed test values and are refused by
anything that checks its secrets look like production ones.
"""

import hashlib
import hmac
import json
import pathlib

SECRET = "whsec_4b1g4h_pr0b3r_s3cr3t_do_not_use_in_production"
PREVIOUS_SECRET = "whsec_4b1g4h_pr3v10us_s3cr3t_do_not_use_in_production"
TIMESTAMP = 1788660000

ROOT = pathlib.Path(__file__).resolve().parent.parent


def sign(secret: str, timestamp: int, body: str) -> str:
    """The one operation the whole contract rests on. See docs/signing.md."""
    return hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.{body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def compact(example: str) -> str:
    """An example payload as the bytes that would go on the wire."""
    with (ROOT / "v1" / "examples" / example).open() as handle:
        return json.dumps(json.load(handle), separators=(",", ":"), ensure_ascii=False)


def main() -> None:
    results_body = compact("results.json")

    positive = []

    def add(name, description, body, secret=SECRET, timestamp=TIMESTAMP):
        positive.append({
            "name": name,
            "description": description,
            "secret": secret,
            "timestamp": timestamp,
            "body": body,
            "signature": sign(secret, timestamp, body),
            "verifies": True,
        })

    add("results-delivery",
        "A prober -> hub results delivery. The signed string is '{timestamp}.{raw body}'.",
        results_body)
    add("empty-body",
        "A change notice: POST {prober}/tenants/{tenant}/changed carries no body. "
        "The signed string is the timestamp, a dot, and nothing.",
        "")
    add("unicode-body",
        "A body containing multi-byte UTF-8. Implementations must sign the UTF-8 bytes, "
        "not a decoded or escaped form.",
        '{"schema":1,"message":"Le café est tombé — éèê 中文 🚀"}')
    add("previous-secret",
        "The same body signed with a tenant's previous secret. During rotation the verifier "
        "accepts a match against any configured secret, so this must verify too.",
        results_body, secret=PREVIOUS_SECRET)
    add("manifest-response",
        "A hub -> prober manifest response. The direction does not change the algorithm; "
        "only which side holds which secret.",
        compact("manifest.json"))
    add("ping-body",
        "A site -> prober ping. Pings authenticate by the token in the path, not by HMAC, "
        "but a client that signs anyway must produce this.",
        '{"message":"Nightly digest sent to 412 recipients","duration_ms":8410}')

    negative = [
        {
            "name": "wrong-secret",
            "description": "Correct body and timestamp, signed with a secret the verifier does "
                           "not hold. Must be rejected.",
            "secret": "whsec_not_a_configured_secret",
            "timestamp": TIMESTAMP,
            "body": results_body,
            "signature": sign(SECRET, TIMESTAMP, results_body),
            "verifies": False,
            "reason": "signature was produced with a different secret",
        },
        {
            "name": "tampered-body",
            "description": "A signature lifted from a valid delivery and replayed with one byte "
                           "of the body changed. Must be rejected.",
            "secret": SECRET,
            "timestamp": TIMESTAMP,
            "body": results_body.replace('"up":true', '"up":false', 1),
            "signature": sign(SECRET, TIMESTAMP, results_body),
            "verifies": False,
            "reason": "body does not match the signed body",
        },
        {
            "name": "timestamp-shifted",
            "description": "A valid signature presented with a different timestamp header. The "
                           "timestamp is inside the signed string, so this cannot verify.",
            "secret": SECRET,
            "timestamp": TIMESTAMP + 60,
            "body": results_body,
            "signature": sign(SECRET, TIMESTAMP, results_body),
            "verifies": False,
            "reason": "timestamp is part of the signed string",
        },
        {
            "name": "skew-exceeded",
            "description": "A correctly signed request whose timestamp is 6 minutes old. The "
                           "signature verifies but the request must still be refused, because "
                           "tolerance is +/- 300 seconds.",
            "secret": SECRET,
            "timestamp": TIMESTAMP,
            "body": results_body,
            "signature": sign(SECRET, TIMESTAMP, results_body),
            "verifies": False,
            "reason": "outside the +/- 300 second skew window",
            "verifier_now": TIMESTAMP + 360,
        },
    ]

    document = {
        "$comment": "Generated fixtures. See ../../docs/signing.md for the algorithm. "
                    "Regenerate with tools/generate-hmac-vectors.py.",
        "algorithm": "HMAC-SHA256",
        "encoding": "lowercase hex",
        "signed_string": "{timestamp}.{raw request body}",
        "skew_tolerance_seconds": 300,
        "headers": {
            "schema": "X-Monitoring-Schema",
            "timestamp": "X-Monitoring-Timestamp",
            "signature": "X-Monitoring-Signature",
            "prober": "X-Monitoring-Prober",
            "tenant": "X-Monitoring-Tenant",
        },
        "signature_header_format": "v1=<hex>",
        "positive": positive,
        "negative": negative,
    }

    out = ROOT / "v1" / "hmac" / "vectors.json"
    out.write_text(json.dumps(document, indent="\t", ensure_ascii=False) + "\n")
    print(f"wrote {len(positive)} positive and {len(negative)} negative vectors to {out}")


if __name__ == "__main__":
    main()
