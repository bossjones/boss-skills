// Grader: verifies that a complete eval suite was scaffolded.
// Checks for required files: eval.yaml, run_eval.sh, README.md,
// at least one grader, and at least one fixture.
// Usage: node check-eval-structure.js <eval-dir>

const fs = require("fs");
const path = require("path");

const evalDir = process.argv[2] || "eval";
const missing = [];

for (const f of ["eval.yaml", "run_eval.sh", "README.md"]) {
    if (!fs.existsSync(path.join(evalDir, f))) missing.push(f);
}

const gradersDir = path.join(evalDir, "graders");
const graderCount = fs.existsSync(gradersDir) ? fs.readdirSync(gradersDir).filter(f => f.endsWith(".js")).length : 0;
if (graderCount === 0) missing.push("graders/*.js (none found)");

const fixturesDir = path.join(evalDir, "test-fixtures");
const fixtureCount = fs.existsSync(fixturesDir)
    ? fs.readdirSync(fixturesDir).filter(f => fs.statSync(path.join(fixturesDir, f)).isDirectory()).length
    : 0;
if (fixtureCount === 0) missing.push("test-fixtures/ (no fixtures)");

if (missing.length === 0) {
    console.log(
        JSON.stringify({ score: 1.0, details: `Complete eval suite: ${graderCount} graders, ${fixtureCount} fixtures` })
    );
} else {
    console.log(JSON.stringify({ score: 0.0, details: `Missing: ${missing.join(", ")}` }));
}
