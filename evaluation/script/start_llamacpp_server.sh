#!/usr/bin/env bash
set -euo pipefail

# 先编译好 llama.cpp，并把GGUF路径改成自己的
MODEL_PATH="/path/to/Qwen2.5-7B-Instruct.Q4_K_M.gguf"
HOST="127.0.0.1"
PORT="8080"
CTX=4096
THREADS=8
NGL=35   # 4070上可调；不确定就删掉该参数让其自动

# server 会启动一个 OpenAI 兼容接口（/v1）
# 新版llama.cpp支持 --api-key，若需要可加：--api-key test
./server -m "$MODEL_PATH" -c $CTX -t $THREADS --host $HOST --port $PORT -ngl $NGL
