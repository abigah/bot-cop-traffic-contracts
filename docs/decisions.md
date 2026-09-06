# Decisions taken while writing v1

The design doc (`bot-cop-traffic-prober/docs/monitoring-prober-design.md` §5)
specifies these contracts at the level of field names. Turning that into schemas
forced a set of smaller choices it did not cover. They are listed here rather
than buried in the schema files, because each one is cheap to change now and
expensive once two implementations depend on it.

## Settled here

**Ids are strings on the wire.** The hub owns monitor, site and heartbeat ids and
stores them as integers. Serialising them as strings avoids an integer/string
mismatch between PHP and TypeScript that would otherwise surface as a silent
lookup miss, and costs nothing: the prober only ever echoes them back.

**Timestamps are UTC with a `Z` suffix and no offset.** ISO-8601 permits `+00:00`
and local offsets; allowing them means two implementations that both "handle
ISO-8601" can still disagree. The schemas pin a single form by pattern.

**The signed string separates timestamp and body with a dot.** "HMAC over
timestamp + body" is ambiguous — a timestamp of `1788660000` and a body of `1`
would otherwise sign identically to `178866000` and `01`. The dot is what makes
the encoding injective. Same construction Stripe uses.

**`served_from_cache` is a flag, not a status.** The design calls a cached
response "a distinct status from up or down", but the hub's seam is
`recordUptimeResult(bool $up, ...)`, so a third status value would have nowhere
to land. It is carried as a boolean alongside `up`: the hub records the check as
normal and flags the misconfiguration separately. If it later wants to treat
these as neither up nor down, the flag is enough to do it without a schema change.

**Clamped intervals are reported in the results payload.** §6a says the clamp is
reported in the next delivery but does not say where. `clamped[]` sits beside
`dropped[]`, carrying the requested interval, the effective one, and which rule
did it — the tenant minimum or the 60-minute floor for a hibernating site.

**A first-ever delivery goes out immediately.** The cadence rule says results are
batched while everything is up, which on a fresh prober would mean an hour before
anything is sent and an hour before an unreachable hub is noticed. The fixtures
make the null-last-delivery case deliver once, so the link is proven at boot.

**Recovery verdicts are delivered even while a site is down.** Every other
heartbeat verdict is suppressed during an outage. `recovered` is not a page — it
is what lets the hub close the heartbeat's own state — so suppressing it would
strand that state until the next ping.

**Schemas are self-contained.** Each file repeats the small shared definitions
(prober, timestamp, id) in its own `$defs` rather than `$ref`-ing a common file.
Cross-file `$ref` resolution is the first thing to break when the same schemas
are loaded by a PHP validator, a TypeScript validator and a CI script that just
wants to read one file. The duplication is a few lines and is checked by
`npm test`.

**A site status goes stale after two minutes.** The site rule probes the site's
critical monitors before judging a heartbeat, but only when what it knows is too
old to be evidence. The design says it probes when the last result "is stale or
was up", which read literally would probe forever — the probe's own result is
also "up". `site_status_fresh_seconds` in the fixture is what breaks that loop:
a status established within it is trusted, anything older is re-probed. Two
minutes is short enough that a site which fell over between the last check and
now is caught, and long enough that a sweep does not re-probe a site it checked
seconds ago.

## Left open

**Ping tokens are unversioned.** A rotated `ingest_token` or heartbeat `token`
takes effect on the next manifest pull, so pings signed with the old one fail in
between. Probably wants a grace period the way tenant secrets have one, but the
shape of that depends on how the hub issues tokens, which is not built yet.

**No pagination on the manifest.** Fine for the tenants in hand. A tenant with
thousands of monitors would want a cursor, and adding one later is a schema
version bump.

**`dropped[]` reports counts, not which results were lost.** Enough for the hub
to show a gap; not enough to say what was in it. That is the intended trade —
the prober is not a history store — but it is worth being explicit that the
information is genuinely gone.
