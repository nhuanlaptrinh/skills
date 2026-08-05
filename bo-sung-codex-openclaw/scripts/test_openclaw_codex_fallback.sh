#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-openai/gpt-5.5}"
PROMPT="Reply exactly: OpenAI fallback OK"

echo "== OpenClaw config validate =="
openclaw config validate

echo
echo "== OpenClaw model status =="
openclaw models status

echo
echo "== OpenClaw auth profiles =="
openclaw models auth list

echo
echo "== OpenAI/Codex fallback inference test: ${MODEL} =="
openclaw infer model run --local --model "${MODEL}" --prompt "${PROMPT}"
