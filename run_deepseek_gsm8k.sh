#!/usr/bin/env bash
set -euo pipefail

#如果你有 env.sh（里面 export OPENAI_API_KEY 等），自动加载
ENV_SH="$(dirname "$0")/../env.sh"
[[ -f "$ENV_SH" ]] && source "$ENV_SH" || true

# ===== 配置=====
TASKS="${1:-gsm8k}"               # 任务名，默认 gsm8k
BATCH_SIZE="${BATCH_SIZE:-1}"     # chat-completions 不支持批处理，强制 1
SEED="${SEED:-42}"
TEMP="${TEMP:-0}"
TOP_P="${TOP_P:-1}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-128}"
LIMIT="${LIMIT:-}"                # 留空=全量。示例抽样：LIMIT=0.02

# DeepSeek API KEY
: "${OPENAI_API_KEY:?请先 export OPENAI_API_KEY=你的deepseek密钥}"

# 输出目录
OUTDIR="$(dirname "$0")/../outputs"
mkdir -p "$OUTDIR"

# ===== 任务白/黑名单保护 =====
# 这些任务需要 loglikelihood（chat-completions 不支持），会报 NotImplementedError
BAD_TASKS_REGEX='(^|,)(ceval|mmlu|cmmlu|arc_|hellaswag|piqa|boolq|winogrande|openbookqa|lambada|wikitext|ptb|c4)(,|$)'
if [[ "$TASKS" =~ $BAD_TASKS_REGEX ]]; then
  echo "❌ 检测到需要 loglikelihood 的任务：$TASKS"
  echo "👉 请选择生成式任务（如 gsm8k），或换能提供 logprobs 的后端（hf/vllm）。"
  exit 1
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
OUTFILE="$OUTDIR/deepseek_${TASKS//[, ]/_}_${STAMP}.json"

# ===== 开跑 =====
# 清理可能干扰的 OpenAI 环境变量，显式指定 DeepSeek 端点
# 注意：DeepSeek 走 chat-completions 完整路径（base_url & api_base 同指向）
CMD=(python -m lm_eval
  --model openai-chat-completions
  --model_args "model=deepseek-chat,base_url=https://api.deepseek.com/v1/chat/completions,api_base=https://api.deepseek.com/v1/chat/completions,api_key=${OPENAI_API_KEY}"
  --tasks "$TASKS"
  --batch_size "$BATCH_SIZE"
  --seed "$SEED"
  --apply_chat_template
  --gen_kwargs "temperature=${TEMP},top_p=${TOP_P},max_new_tokens=${MAX_NEW_TOKENS}"
  --system_instruction "Solve step by step, and print ONLY the final numeric answer on the last line as: #### <number>."
  --output_path "$OUTFILE"
)

# 如需抽样测试可用 LIMIT（LIMIT=0.02）
if [[ -n "${LIMIT}" ]]; then
  CMD+=(--limit "$LIMIT")
fi

# 避免环境变量把请求发到 openai.com
env -u OPENAI_BASE_URL -u OPENAI_API_BASE -u OPENAI_ORG_ID -u OPENAI_API_TYPE \
  "${CMD[@]}"

echo
echo "✅ 评测完成：$OUTFILE"
