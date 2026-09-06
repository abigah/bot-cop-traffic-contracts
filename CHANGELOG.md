# Changelog

## v1 — in use

Schema version 1, built from the design doc's §5. **The prober is deployed
against it and the hub is being built against it, so treat it as frozen**: a
breaking change now means a `v2/` directory beside `v1/`, not an edit.

- Schemas for the eight payloads, an example each, and ten must-reject cases.
- HMAC vectors, including negative cases for a wrong secret, a tampered body, a
  shifted timestamp, and a correctly signed request that is simply too old.
- Fixtures for the delivery cadence and the heartbeat site rule.
- `site_status_fresh_seconds` on the site-rule fixture. Without it, "probe first"
  and "already probed" cannot be told apart: both arrive with the site last seen
  up, and only the age of that knowledge separates them.
- `docs/signing.md` and `docs/decisions.md`.

Additive changes that do not break a conformant implementation — a new optional
field, another fixture case — can land here. Anything a v1 consumer could
mis-read cannot.
