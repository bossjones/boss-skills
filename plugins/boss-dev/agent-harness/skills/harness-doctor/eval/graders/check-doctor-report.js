const fs = require("fs");

const outputPath = process.argv[2] || "output.md";
const expected = process.argv[3] || "clean";

if (!fs.existsSync(outputPath)) {
  console.log(JSON.stringify({ score: 0.0, details: `Output file not found: ${outputPath}` }));
  process.exit(0);
}

try {
  const report = JSON.parse(fs.readFileSync(outputPath, "utf8"));
  const storage = report.harness_root && report.harness_root.storage;
  const stale = report.stale_artifacts;
  const valid = report.advisory === true
    && storage
    && ["logs", "data", "cache"].every((name) => Object.hasOwn(storage, name))
    && stale
    && stale.logs
    && stale.claude_data;
  const expectedStale = expected !== "stale" || stale.logs.exists || stale.claude_data.exists;
  console.log(JSON.stringify({
    score: valid && expectedStale ? 1.0 : 0.0,
    details: valid && expectedStale
      ? `Doctor report has expected ${expected} artifact state`
      : `Doctor report is missing required ${expected} state`,
  }));
} catch (error) {
  console.log(JSON.stringify({ score: 0.0, details: `Invalid JSON report: ${error.message}` }));
}
