#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-}"
if [[ "$MODEL" != */* ]]; then
  echo "Usage: $0 <verified-provider>/GPT-6-terra" >&2
  exit 2
fi
case "${MODEL##*/}" in
  GPT-6.1-sol|GPT-6-terra|GPT-6-luna|GPT-6-astra) ;;
  *) echo "Unsupported model. Choose GPT-6.1-sol, GPT-6-terra, GPT-6-luna, or GPT-6-astra." >&2; exit 2 ;;
esac
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
