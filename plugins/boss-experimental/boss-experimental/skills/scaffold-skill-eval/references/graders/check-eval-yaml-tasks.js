// Grader: validates eval.yaml structure and minimum task count.
// Usage: node check-eval-yaml-tasks.js <min-tasks> <eval-dir>

const fs = require("fs");
const path = require("path");

const minTasks = parseInt(process.argv[2], 10) || 1;
const evalDir = process.argv[3] || "eval";
const yamlPath = path.join(evalDir, "eval.yaml");

if (!fs.existsSync(yamlPath)) {
    console.log(JSON.stringify({ score: 0.0, details: `eval.yaml not found at ${yamlPath}` }));
    process.exit(0);
}

const content = fs.readFileSync(yamlPath, "utf-8");
const issues = [];

// Check version field
if (!/^version:\s*"1"/m.test(content)) {
    issues.push('missing or wrong version (expected "1")');
}

// Check defaults block
if (!/^defaults:/m.test(content)) {
    issues.push("missing defaults block");
}

// Count tasks by counting "- name:" entries
const taskMatches = content.match(/^\s+- name:/gm) || [];
const taskCount = taskMatches.length;

if (taskCount < minTasks) {
    issues.push(`expected at least ${minTasks} tasks, found ${taskCount}`);
}

// Check each task has graders
const taskSections = content.split(/^\s+- name:/m).slice(1);
for (let i = 0; i < taskSections.length; i++) {
    if (!/graders:/m.test(taskSections[i])) {
        issues.push(`task ${i + 1} missing graders`);
    }
    if (!/instruction:/m.test(taskSections[i])) {
        issues.push(`task ${i + 1} missing instruction`);
    }
}

if (issues.length === 0) {
    console.log(JSON.stringify({ score: 1.0, details: `Valid eval.yaml with ${taskCount} tasks` }));
} else {
    console.log(JSON.stringify({ score: 0.0, details: `Issues: ${issues.join("; ")}` }));
}
