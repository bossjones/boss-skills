// Grader: asserts zero FAIL statuses in the output (for positive controls).
// Usage: node check-no-fails.js <output-file>

const fs = require("fs");

const outputFile = process.argv[2] || "output.md";

if (!fs.existsSync(outputFile)) {
    console.log(JSON.stringify({ score: 0.0, details: `Output file not found: ${outputFile}` }));
    process.exit(0);
}

const content = fs.readFileSync(outputFile, "utf-8");
const failCount = (content.match(/\| FAIL/gi) || []).length;

if (failCount === 0) {
    console.log(JSON.stringify({ score: 1.0, details: "No FAIL statuses found — valid project passed all checks" }));
} else {
    console.log(JSON.stringify({ score: 0.0, details: `Found ${failCount} unexpected FAIL statuses` }));
}
