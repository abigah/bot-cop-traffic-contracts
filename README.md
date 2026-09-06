# bot-cop-traffic-contracts

The conformance kit for Bot Cop Traffic Division: JSON Schemas, example
payloads, HMAC test vectors and rule fixtures.

**The contracts are the product.** A prober performs HTTP checks from outside
the monitored infrastructure and delivers raw results; a hub replays them and
owns every alerting decision. Neither needs to know how the other is built — only
this. A second prober implementation, in another language on another platform, is
"another thing that passes this kit", and that is what makes the redundancy real
rather than two copies of one codebase sharing one bug.

Consumed by:

| Repo | Language | Role |
|---|---|---|
| `bot-cop-traffic-division` | PHP | the hub the extranets run |
| `bot-cop-traffic-client` | PHP | the site-side toolkit |
| `bot-cop-traffic-prober` | TypeScript | the Cloudflare Worker prober |

## Layout

```
v1/
  schema/            JSON Schema 2020-12, one file per payload
  examples/          a valid example per schema, named to match
  examples-invalid/  payloads that must be refused, each with the rule it isolates
  hmac/vectors.json  signed bodies with their expected signatures
  fixtures/          the cadence and site-rule cases, as data
docs/
  signing.md         the signing algorithm, byte for byte
  decisions.md       choices made here that the design doc did not cover
tools/
  validate.mjs       checks this kit against itself
  generate-hmac-vectors.py
```

The version lives in the directory name and in `X-Monitoring-Schema`. A breaking
change means `v2/` beside `v1/`, not an edit to `v1/`.

## The payloads

| Schema | Direction | Endpoint |
|---|---|---|
| `manifest` | hub → prober | `GET {extranet}/monitoring/manifest` |
| `results` | prober → hub | `POST {extranet}/monitoring/results` |
| `results-response` | hub → prober | the response to the above |
| `heartbeat-verdicts` | prober → hub | `POST {extranet}/monitoring/heartbeats` |
| `exceptions` | prober → hub | `POST {extranet}/monitoring/exceptions` |
| `change-notice` | hub → prober | `POST {prober}/tenants/{tenant}/changed` |
| `ping` | site → prober | `GET\|POST {prober}/ping/{token}[/start\|/fail]` |
| `exception-report` | site → prober | `POST {prober}/report/{token}` |

Everything except the two site-to-prober endpoints is HMAC-signed; see
[docs/signing.md](docs/signing.md) for why those two are not.

## The fixtures

`v1/fixtures/` holds the two rules that are easy to describe in prose and easy to
get subtly wrong in code:

- **`delivery-cadence.json`** — when a prober may hold results back and when it
  must deliver at once. The extranets hibernate, so every delivery wakes one.
- **`heartbeat-site-rule.json`** — whether a missed job is its own problem or
  part of an outage already in progress. Note the `probe-then-judge` branch: the
  prober spends one extra request to find out, only in the case that matters.

Each case names a pure function, its input and its expected output. An
implementation binds its own function to the cases; nothing here is executable.

## Status

**In use, and effectively frozen.** The prober is deployed against v1 and the
hub is being built against it. Additive changes that no conformant
implementation could mis-read are fine; anything else is a `v2/` beside `v1/`.

## Checking the kit

```sh
npm install
npm test
```

CI runs this on every push, and additionally regenerates the HMAC vectors to
confirm they still match the examples they are derived from — an edited example
with stale signatures would otherwise ship looking perfectly correct.

This validates the kit against itself — every schema compiles, every example
validates, every must-reject case is refused, and every HMAC vector reproduces
its stated signature. It is not the conformance kit; it is the guard that stops
the kit shipping something that cannot be true. The conformance kit is what the
prober and the hub run against these files in their own test suites.

Node is a convenience for that check. The artefacts are plain JSON and carry no
dependency on it.

## Consuming it

Pin a commit. Both directions of a contract change have to land somewhere, and
a floating reference means a hub and a prober can disagree about what version 1
is while both claiming to be current.
