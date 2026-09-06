# Signing

Every request between a prober and a hub is signed. This is the one piece both
implementations must agree on byte for byte, so it is specified here in full and
pinned by the vectors in `v1/hmac/vectors.json`.

## Headers

| Header | On | Value |
|---|---|---|
| `X-Monitoring-Schema` | every request | the integer schema version, `1` today |
| `X-Monitoring-Timestamp` | every request | Unix seconds, as a decimal string |
| `X-Monitoring-Signature` | every request | `v1=<lowercase hex>` |
| `X-Monitoring-Prober` | prober → hub | the prober id, so the hub knows which secret to try |
| `X-Monitoring-Tenant` | hub → prober | the tenant slug, for the same reason |

## The signed string

```
{timestamp}.{raw request body}
```

The timestamp is the value of `X-Monitoring-Timestamp`. The body is the exact
bytes on the wire — not a re-serialised, re-indented or re-ordered form of them.
A verifier that parses JSON before checking the signature has already lost: it
must hold the raw body, verify, and only then parse. An empty body signs as the
timestamp, a dot, and nothing.

## The algorithm

HMAC-SHA256 over the UTF-8 bytes of the signed string, keyed with the UTF-8
bytes of the shared secret, rendered as lowercase hex.

Compare in constant time. A byte-by-byte comparison that returns early leaks the
signature one character at a time.

## Verifying

1. Refuse an `X-Monitoring-Schema` you do not implement. Do not guess, and do not
   fall back to the newest version you know — an unknown version means the sender
   believes something about this payload that you do not.
2. Refuse a timestamp more than **300 seconds** from your own clock, in either
   direction. This is what stops a captured request being replayed tomorrow.
3. Compute the signature for each secret you hold for that counterparty and
   accept if any matches. Two are configured during rotation (current and
   previous), which is what lets a secret change without a gap.
4. Only now parse the body.

Steps 1 and 2 are cheap and reject most abuse before any cryptography happens,
but they are not a substitute for step 3 — check all three.

## What is not signed

Pings (`GET|POST {prober}/ping/{token}`) and exception reports
(`POST {prober}/report/{token}`) are authenticated by the token in the path, not
by HMAC. They come from arbitrary site code — a queue worker, a deploy script —
which cannot be trusted to hold a tenant secret, and they must stay
fire-and-forget. Both endpoints are throttled per token instead, and a token
grants nothing but the ability to say that one heartbeat fired or that one site
threw an error.

The schema version is carried in a header, which is outside the signed string.
It is also a field inside every signed body, so for those payloads it is covered
transitively; verify the header against the body's `schema` field and reject a
mismatch.

## Vectors

`v1/hmac/vectors.json` holds signed examples with their expected signatures, and
negative cases that must be refused: a wrong secret, a tampered body, a shifted
timestamp, and a correctly signed request that is simply too old. An
implementation is not conformant until it agrees with all of them.

Regenerate them with `python3 tools/generate-hmac-vectors.py` after changing an
example payload. The keys in the file are fixed test values, not secrets.
