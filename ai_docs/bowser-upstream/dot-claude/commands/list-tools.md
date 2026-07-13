---
model: opus
description: List all available tools as TypeScript function prototypes with parameter and purpose comments
---

# Purpose

List all available tools from your system prompt in TypeScript function prototype syntax, with descriptive comments for each tool and parameter.

## Instructions

- Read your own system prompt to identify every tool available to you
- Present each tool as a TypeScript function prototype
- Each function gets a comment above it explaining the tool's purpose
- Each parameter gets a trailing `//` comment explaining what it does
- Put each parameter on its own line for readability
- Use appropriate TypeScript types (`string`, `number`, `boolean`, `string[]`, etc.)
- Mark optional parameters with `?`
- Do NOT execute any tools — this is a reporting task only

## Workflow

1. Inspect your system prompt and enumerate every tool available in this session
2. For each tool, format it as a TypeScript function prototype with comments
3. Now follow the `Report` section to report the completed work
4. Write the results out to TOOLS.md in the root of the project

## Report

Present the tools in this format:

```ts
// [Brief description of what the tool does]
function ToolName(
  param1: string,       // [what param1 is for]
  param2?: number,      // [what param2 is for]
): ReturnType;
```

List every tool, one after another, separated by a blank line. Group related tools together if applicable.
