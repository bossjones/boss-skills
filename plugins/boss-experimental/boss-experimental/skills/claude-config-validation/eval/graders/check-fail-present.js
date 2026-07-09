// Grader: asserts FAIL appears for a named check pattern.
// Usage: node check-fail-present.js <pattern> <output-file>

const fs = require("fs");

const pattern = process.argv[2];
const outputFile = process.argv[3] || "output.md";

if (!fs.existsSync(outputFile)) {
    console.log(JSON.stringify({ score: 0.0, details: `Output file not found: ${outputFile}` }));
    process.exit(0);
}

const content = fs.readFileSync(outputFile, "utf-8");
// Escape regex metacharacters — check names contain `.`, `(`, `[` etc. and are
// interpolated into the pattern; an unescaped metachar throws SyntaxError.
const esc = pattern.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const regex = new RegExp(`FAIL.*${esc}|${esc}.*FAIL`, "i");

if (regex.test(content)) {
    console.log(JSON.stringify({ score: 1.0, details: `Correctly reported FAIL for: ${pattern}` }));
} else {
    console.log(JSON.stringify({ score: 0.0, details: `Expected FAIL for '${pattern}' but not found in output` }));
}
