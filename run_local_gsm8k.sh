#!/usr/bin/env bash
set -euo pipefail

# 本地 llama.cpp server 的设置
LOCAL_API_BASE="${LOCAL_API_BASE:-http://127.0.0.1:8000/v1}"
LOCAL_API_KEY="${LOCAL_API_KEY:-sk-local}"
LOCAL_MODEL_ID="${LOCAL_MODEL_ID:-qwen2.5-7b-instruct}"

# 评测配置
TASKS="${1:-gsm8k}"             # 只跑 gsm8k，避免 loglikelihood 报错
BATCH_SIZE=1                    # chat-completions 不支持并发 batch，固定 1
SEED="${SEED:-42}"
TEMP="${TEMP:-0}"
TOP_P="${TOP_P:-1}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-64}"
LIMIT="${LIMIT:-}"              # 比例(0.02/0.1) 或 数字(27/132)。留空=全量

# 输出目录
OUTDIR="$(dirname "$0")/../outputs"
mkdir -p "$OUTDIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUTFILE="$OUTDIR/local_${LOCAL_MODEL_ID//[^a-zA-Z0-9_]/_}_${TASKS//[, ]/_}_${STAMP}.json"

# 先检查本地服务是否在线
if ! curl -sS "${LOCAL_API_BASE}/models" -H "Authorization: Bearer ${LOCAL_API_KEY}" >/dev/null ; then
  echo "❌ 无法连到本地 llama.cpp server: ${LOCAL_API_BASE}"
  echo "👉 请先启动："
  echo "   python -m llama_cpp.server \\"
  echo "     --model /path/to/your.gguf \\"
  echo "     --model_alias ${LOCAL_MODEL_ID} \\"
  echo "     --host 127.0.0.1 --port 8000 \\"
  echo "     --n_ctx 4096 --n_threads \$(nproc) --n_gpu_layers 0"
  exit 1
fi

# 这些任务会触发 loglikelihood（chat-completions 不支持），在本地/DeepSeek都会报错
BAD_TASKS_REGEX='(^|,)(ceval|mmlu|cmmlu|arc_|hellaswag|piqa|boolq|winogrande|openbookqa|lambada|wikitext|ptb|c4)(,|$)'
if [[ "$TASKS" =~ $BAD_TASKS_REGEX ]]; then
  echo "❌ 检测到需要 loglikelihood 的任务：$TASKS"
  echo "👉 请选择生成式任务（如 gsm8k），或改用支持 logprobs 的后端。"
  exit 1
fi

CMD=(python -m lm_eval
  --model openai-chat-completions
  # 明确指定到本地 server 的 chat-completions 完整路径，并提供本地“密钥”
  --model_args "model=${LOCAL_MODEL_ID},base_url=${LOCAL_API_BASE}/chat/completions,api_base=${LOCAL_API_BASE}/chat/completions,api_key=${LOCAL_API_KEY}"
  --tasks "$TASKS"
  --batch_size "$BATCH_SIZE"
  --seed "$SEED"
  --apply_chat_template
  --gen_kwargs "temperature=${TEMP},top_p=${TOP_P},max_new_tokens=${MAX_NEW_TOKENS}"
  --system_instruction "Solve step by step, and print ONLY the final numeric answer on the last line as: #### <number>."
  --output_path "$OUTFILE"
)

# 同量对齐：设置 LIMIT（比例或整数），比如 LIMIT=0.02 / LIMIT=27
if [[ -n "${LIMIT}" ]]; then
  CMD+=(--limit "$LIMIT")
fi

# 解除可能把请求发到 openai.com 的环境变量干扰
env -u OPENAI_BASE_URL -u OPENAI_API_BASE -u OPENAI_API_KEY -u OPENAI_ORG_ID -u OPENAI_API_TYPE \
  "${CMD[@]}"

echo "✅ 已完成：$OUTFILE"
