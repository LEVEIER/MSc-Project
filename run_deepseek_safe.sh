#!/usr/bin/env bash
set -euo pipefail

# 使用方法：
#   scripts/run_deepseek_safe.sh "gsm8k"              # OK
#   scripts/run_deepseek_safe.sh "gsm8k,ceval-valid"  # 会被拦截并提示

TASKS="${1:-gsm8k}"

# 常见需要 loglikelihood 的任务关键词（有就报错）
BAD_TASKS_REGEX='(^|,)(ceval|mmlu|cmmlu|arc_|hellaswag|piqa|boolq|winogrande|openbookqa|lambada|wikitext|ptb|c4)(,|$)'
if [[ "$TASKS" =~ $BAD_TASKS_REGEX ]]; then
  echo "❌ 这些任务需要 loglikelihood，chat-completions 不支持，会触发 NotImplementedError：$TASKS"
  echo "👉 方案：仅保留生成式任务（如 gsm8k），或换本地/能导出 logprobs 的后端（hf/vllm），或使用生成式变体。"
  exit 1
fi

mkdir -p outputs

# 强制走 DeepSeek（避免误用 OpenAI 环境变量）
env -u OPENAI_API_KEY -u OPENAI_API_BASE -u OPENAI_BASE_URL \
OPENAI_API_KEY="${OPENAI_API_KEY:-sk-REPLACE_WITH_YOUR_DEEPSEEK_KEY}" \
OPENAI_API_BASE="https://api.deepseek.com/v1" \
python -m lm_eval \
  --model openai-chat-completions \
  --model_args "model=deepseek-chat,base_url=https://api.deepseek.com/v1/chat/completions,api_base=https://api.deepseek.com/v1/chat/completions,api_key=${OPENAI_API_KEY}" \
  --tasks "$TASKS" \
  --batch_size 1 \
  --apply_chat_template \
  --system_instruction "Solve step by step, and print ONLY the final numeric answer on the last line as: #### <number>." \
  --gen_kwargs "temperature=0,top_p=1,max_new_tokens=256" \
  --seed 42 \
  --output_path "outputs/deepseek_${TASKS//,/}_$(date +%Y%m%d_%H%M%S).json"
