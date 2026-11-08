# Bun + TypeScript Justfile Example

# Use bun to run the scripts
set shell := ["bun", "run", "-c"]

# List all recipes
default:
  @just --list

# Install dependencies using bun
install:
  bun install

# Run the project
dev:
  bun src/index.ts

# Run tests with bun's native test runner
test:
  bun test

# Build/Bundle the project
build:
  bun build ./src/index.ts --outdir ./dist

# Example of a TypeScript "shebang" recipe using bun
[doc("Run a complex TS script directly in the justfile")]
ts-task:
  #!/usr/bin/env bun
  const message: string = "Hello from Bun TypeScript!";
  console.log(message);
  console.log("Current Directory:", process.cwd());
