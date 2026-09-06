// Checks the kit against itself: every schema compiles, every example validates
// against its schema, and every HMAC vector reproduces its stated signature.
//
// This is not the conformance kit — that is what the prober and the hub run.
// It is the guard that stops the kit shipping something that cannot be true.

import { createHmac, timingSafeEqual } from "node:crypto";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import Ajv from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const read = (...parts) => JSON.parse(readFileSync(join(root, ...parts), "utf8"));

const failures = [];
const fail = (what, detail) => failures.push(`${what}: ${detail}`);
let passed = 0;
const pass = () => passed++;

// Each example is named for the schema it must satisfy.
const examples = readdirSync(join(root, "v1", "examples")).filter((f) => f.endsWith(".json"));

const ajv = new Ajv({ strict: true, allErrors: true });
addFormats(ajv);

const compiled = new Map();

for (const file of readdirSync(join(root, "v1", "schema")).filter((f) => f.endsWith(".json"))) {
	const schema = read("v1", "schema", file);
	let validate;
	try {
		validate = ajv.compile(schema);
		compiled.set(file.replace(".schema.json", ""), validate);
		pass();
	} catch (error) {
		fail(file, `does not compile — ${error.message}`);
		continue;
	}

	const exampleFile = file.replace(".schema.json", ".json");
	if (!examples.includes(exampleFile)) {
		fail(file, `has no example at v1/examples/${exampleFile}`);
		continue;
	}

	if (validate(read("v1", "examples", exampleFile))) {
		pass();
	} else {
		for (const e of validate.errors) fail(exampleFile, `${e.instancePath || "/"} ${e.message}`);
	}
}

for (const file of examples) {
	const schemaFile = file.replace(".json", ".schema.json");
	try {
		readFileSync(join(root, "v1", "schema", schemaFile));
	} catch {
		fail(file, `has no schema at v1/schema/${schemaFile}`);
	}
}

// Must-reject cases. Without these a schema that accepts anything would pass.
const invalid = read("v1", "examples-invalid", "cases.json");

for (const c of invalid.cases) {
	const validate = compiled.get(c.schema);
	if (!validate) fail(`must-reject/${c.name}`, `names an unknown schema "${c.schema}"`);
	else if (validate(c.payload)) fail(`must-reject/${c.name}`, "was accepted");
	else pass();
}

// The signing rule, implemented straight from docs/signing.md. If this drifts
// from the vectors, one of the two is wrong and the kit should not ship.
const sign = (secret, timestamp, body) =>
	createHmac("sha256", secret).update(`${timestamp}.${body}`, "utf8").digest("hex");

const equal = (a, b) =>
	a.length === b.length && timingSafeEqual(Buffer.from(a), Buffer.from(b));

const vectors = read("v1", "hmac", "vectors.json");

for (const v of vectors.positive) {
	if (equal(sign(v.secret, v.timestamp, v.body), v.signature)) pass();
	else fail(`hmac/${v.name}`, "recomputed signature does not match the stated one");
}

for (const v of vectors.negative) {
	const matches = equal(sign(v.secret, v.timestamp, v.body), v.signature);
	const withinSkew =
		v.verifier_now === undefined ||
		Math.abs(v.verifier_now - v.timestamp) <= vectors.skew_tolerance_seconds;

	// A negative vector must be refused, but the reason matters: skew-exceeded
	// is the one case where the signature is genuinely valid and the request is
	// refused anyway.
	if (matches && withinSkew) fail(`hmac/${v.name}`, "is accepted but must be refused");
	else pass();
}

// The fixtures describe behaviour no code here implements, so all that can be
// checked is that they are internally coherent.
for (const name of ["delivery-cadence", "heartbeat-site-rule"]) {
	const fixture = read("v1", "fixtures", `${name}.json`);
	const vocabulary = new Set(Object.keys(fixture.reasons ?? fixture.actions));
	const seen = new Set();

	for (const c of fixture.cases) {
		const key = c.expect.reason ?? c.expect.action;
		seen.add(key);
		if (!vocabulary.has(key)) fail(`${name}/${c.name}`, `expects undocumented outcome "${key}"`);
	}

	const unexercised = [...vocabulary].filter((k) => !seen.has(k));
	if (unexercised.length) fail(name, `documents unexercised outcomes: ${unexercised.join(", ")}`);
	else pass();
}

if (failures.length) {
	console.error(`\n${failures.length} problem(s):\n`);
	for (const f of failures) console.error(`  ✗ ${f}`);
	process.exit(1);
}

console.log(`✓ ${passed} checks passed`);
