#!/usr/bin/env bash
set -euo pipefail

# 需要：pip install "lm-eval==0.4.*" llama-cpp-python

TASKS=${1:-"ceval_valid,gsm8k"}
OUTDIR="$(dirname "$0")/../outputs"
mkdir -p "$OUTDIR"

# 直接走 llama-cpp 适配器（不需要HTTP服务器）
# 如果更想走HTTP OpenAI兼容端口，也可以换成 openai-chat-completions + base_url。
lm_eval --model llama-cpp-python \
  --model_args "model=/path/to/Qwen2.5-7B-Instruct.Q4_K_M.gguf,n_threads=8,n_ctx=4096,temperature=0" \
  --tasks "$TASKS" \
  --batch_size 1 \
  --seed 42 \
  --output_path "$OUTDIR/llamacpp_qwen25_${TASKS//,/}_$(date +%Y%m%d_%H%M%S).json"
