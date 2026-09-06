# Changelog

## Unreleased — v1 draft

First cut of schema version 1, written from the design doc's §5. Nothing consumes
it yet, so it can still change freely; once the prober and the hub both build
against it, a change here is a `v2/`.

- Schemas for the eight payloads, examples for each, and ten must-reject cases.
- HMAC vectors, including negative cases for a wrong secret, a tampered body, a
  shifted timestamp, and a correctly signed request that is simply too old.
- Fixtures for the delivery cadence and the heartbeat site rule.
- `docs/signing.md` and `docs/decisions.md`.
