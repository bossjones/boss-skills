# Multi-Module Project Justfile Example
set allow-duplicate-recipes := true

# Import common tasks
import? 'common.just'

# Compile the project
build:
  @echo "Building project..."
  cargo build

# Release a new version with confirmation
[confirm("Are you sure you want to release?")]
release version: build
  @echo "Releasing version {{version}}..."
  git tag v{{version}}
  git push origin v{{version}}

# Run a command in a specific subdirectory
[no-cd]
sub-task:
  cd sub-dir && ./run-task.sh
