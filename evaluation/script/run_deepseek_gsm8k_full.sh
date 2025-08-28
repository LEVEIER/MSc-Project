#!/usr/bin/env bash
set -euo pipefail

mkdir -p outputs


OPENAI_API_KEY="${OPENAI_API_KEY:-sk-REPLACE_WITH_YOUR_DEEPSEEK_KEY}"

# 清掉可能指向 OpenAI 的环境变量，强制走 DeepSeek
env -u OPENAI_API_KEY -u OPENAI_API_BASE -u OPENAI_BASE_URL \
OPENAI_API_KEY="$OPENAI_API_KEY" \
OPENAI_API_BASE="https://api.deepseek.com/v1" \
python -m lm_eval \
  --model openai-chat-completions \
  --model_args "model=deepseek-chat,base_url=https://api.deepseek.com/v1/chat/completions,api_base=https://api.deepseek.com/v1/chat/completions,api_key=$OPENAI_API_KEY" \
  --tasks gsm8k \
  --batch_size 1 \
  --apply_chat_template \
  --system_instruction "Solve step by step, and print ONLY the final numeric answer on the last line as: #### <number>." \
  --gen_kwargs "temperature=0,top_p=1,max_new_tokens=256" \
  --seed 42 \
  --output_path "outputs/deepseek_gsm8k_full_$(date +%Y%m%d_%H%M%S).json"
