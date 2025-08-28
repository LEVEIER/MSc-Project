#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/../env.sh"

TASKS=${1:-"ceval-valid,gsm8k"}
TASKS="${TASKS//_/-}"

OUTDIR="$(dirname "$0")/../outputs"
mkdir -p "$OUTDIR"

python -m lm_eval \
  --model openai-chat-completions \
  --model_args "model=deepseek-chat,base_url=https://api.deepseek.com/v1,api_base=https://api.deepseek.com/v1/chat/completions,api_key=$OPENAI_API_KEY" \
  --tasks "$TASKS" \
  --batch_size 1 \
  --seed 42 \
  --gen_kwargs "temperature=$TEMP,top_p=$TOP_P,max_new_tokens=$MAX_NEW_TOKENS" \
  --apply_chat_template \
  --output_path "$OUTDIR/deepseek_${TASKS//,/}_$(date +%Y%m%d_%H%M%S).json"
