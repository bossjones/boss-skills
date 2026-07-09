// Grader: verifies the skill stopped early for invalid input (negative controls).
// Checks that no eval files were created and the agent reported the problem.
// Usage: node check-stopped-early.js <eval-dir> <output-file>

const fs = require("fs");

const evalDir = process.argv[2] || "eval";
const outputFile = process.argv[3] || "output.md";

// The skill should NOT have created an eval.yaml
if (fs.existsSync(`${evalDir}/eval.yaml`)) {
    console.log(JSON.stringify({ score: 0.0, details: "Skill should have stopped but created eval files" }));
    process.exit(0);
}

// Check that the agent reported the problem
if (fs.existsSync(outputFile)) {
    const content = fs.readFileSync(outputFile, "utf-8");
    if (/stop|missing|error|not found|no\s+(skill|description|frontmatter)/i.test(content)) {
        console.log(JSON.stringify({ score: 1.0, details: "Correctly stopped and reported the issue" }));
    } else {
        console.log(
            JSON.stringify({ score: 0.5, details: "No eval created (correct) but no clear error report found" })
        );
    }
} else {
    console.log(JSON.stringify({ score: 0.5, details: "No eval created (correct) but no clear error report found" }));
}
