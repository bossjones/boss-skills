#!/usr/bin/env bash
# Eval runner for Claude Code skills.
#
# Delegates to skillgrade when available (CI), otherwise directs users
# to /run-skill-eval for local development.
#
# Environment variables:
#   EVAL_PRESET    smoke | reliable | regression  (default: smoke)
#   EVAL_FILTER    comma-separated task names      (default: all)
#   EVAL_THRESHOLD minimum pass rate for CI        (default: 0.8)
#   ANTHROPIC_API_KEY  required for skillgrade
#
# Usage:
#   ./run_eval.sh                          # auto-detect
#   ./run_eval.sh --smoke                  # explicit preset
#   ./run_eval.sh --regression             # 30-trial regression
#   EVAL_FILTER=valid-project ./run_eval.sh  # run single task

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# --------------- Parse arguments ---------------
PRESET="${EVAL_PRESET:-smoke}"
FILTER="${EVAL_FILTER:-}"
THRESHOLD="${EVAL_THRESHOLD:-0.8}"
CI_MODE=false

for arg in "$@"; do
  case "$arg" in
    --smoke)      PRESET="smoke" ;;
    --reliable)   PRESET="reliable" ;;
    --regression) PRESET="regression" ;;
    --ci)         CI_MODE=true ;;
    --eval=*)     FILTER="${arg#--eval=}" ;;
  esac
done

SKILL_NAME="$(basename "$(cd "$SCRIPT_DIR/.." && pwd)")"

# --------------- Delegate to skillgrade if available ---------------
if command -v skillgrade &>/dev/null && [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "=== Skill Eval: $SKILL_NAME ==="
  echo "Provider: skillgrade | Preset: $PRESET"
  echo ""
  ARGS="--${PRESET} --provider=local"
  [ "$CI_MODE" = true ] && ARGS="$ARGS --ci --threshold=$THRESHOLD"
  [ -n "$FILTER" ] && ARGS="$ARGS --eval=$FILTER"
  # shellcheck disable=SC2086
  exec skillgrade $ARGS
fi

# --------------- No skillgrade — guide the user ---------------
echo "=== Skill Eval: $SKILL_NAME ==="
echo ""
echo "For local development, run evals interactively inside Claude Code:"
echo ""
echo "  /run-skill-eval plugins/boss-experimental/boss-experimental/skills/$SKILL_NAME"
echo ""
echo "This runs all tasks (deterministic + llm_rubric graders) using your"
echo "current Claude Code session — no API key or extra setup needed."
echo ""
echo "For CI or headless execution, install skillgrade and set ANTHROPIC_API_KEY:"
echo ""
echo "  npm i -g skillgrade      # or: npx skillgrade ..."
echo "  export ANTHROPIC_API_KEY=sk-ant-..."
echo "  ./run_eval.sh --smoke --ci"
echo ""
