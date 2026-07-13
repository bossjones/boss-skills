# Node.js + Docker Justfile Example
set dotenv-load := true

# List all recipes
default:
  @just --list

# Install dependencies
install:
  npm install

# Run the dev server
dev:
  npm run dev

# Run tests
test:
  npm test

# Build docker image
build-docker version='latest':
  docker build -t my-app:{{version}} .

# Prune docker system
prune:
  docker system prune -f
