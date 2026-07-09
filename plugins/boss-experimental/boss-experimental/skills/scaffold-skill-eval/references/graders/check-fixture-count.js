// Grader: verifies that at least N fixture directories were created.
// Usage: node check-fixture-count.js <min-count> <eval-dir>

const fs = require("fs");
const path = require("path");

const minCount = parseInt(process.argv[2], 10) || 1;
const evalDir = process.argv[3] || "eval";
const fixturesDir = path.join(evalDir, "test-fixtures");

if (!fs.existsSync(fixturesDir)) {
    console.log(JSON.stringify({ score: 0.0, details: "No test-fixtures directory found" }));
    process.exit(0);
}

const fixtures = fs.readdirSync(fixturesDir).filter(f => fs.statSync(path.join(fixturesDir, f)).isDirectory());

if (fixtures.length >= minCount) {
    console.log(JSON.stringify({ score: 1.0, details: `Found ${fixtures.length} fixtures (minimum: ${minCount})` }));
} else {
    console.log(
        JSON.stringify({ score: 0.0, details: `Found ${fixtures.length} fixtures, expected at least ${minCount}` })
    );
}
