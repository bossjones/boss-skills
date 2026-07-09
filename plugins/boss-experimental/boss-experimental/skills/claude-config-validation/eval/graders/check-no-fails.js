// Grader: asserts zero FAIL statuses in the output (for positive controls).
// Usage: node check-no-fails.js <output-file>

const fs = require("fs");

const outputFile = process.argv[2] || "output.md";

if (!fs.existsSync(outputFile)) {
    console.log(JSON.stringify({ score: 0.0, details: `Output file not found: ${outputFile}` }));
    process.exit(0);
}

const content = fs.readFileSync(outputFile, "utf-8");

// Count FAIL only in the Status column (the 3rd data cell) of table rows.
// A loose `| FAIL` substring match miscounts both ways: it false-FAILs on a
// Details cell like "Failsafe: no code blocks", and it false-PASSes on an
// unpadded or decorated status (|FAIL|, | **FAIL** |, | ❌ FAIL |). Splitting
// the row and inspecting cells[3] classifies the status column directly.
let failCount = 0;
for (const line of content.split("\n")) {
    const cells = line.split("|");
    if (cells.length >= 5 && /\bFAIL\b/i.test(cells[3])) {
        failCount++;
    }
}

if (failCount === 0) {
    console.log(JSON.stringify({ score: 1.0, details: "No FAIL statuses found — valid project passed all checks" }));
} else {
    console.log(JSON.stringify({ score: 0.0, details: `Found ${failCount} unexpected FAIL statuses` }));
}
