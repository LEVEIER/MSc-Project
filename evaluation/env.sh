#!/usr/bin/env bash
# DeepSeek base URL 必须带 /v1
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
export OPENAI_API_BASE="$OPENAI_BASE_URL"   # 兼容不同库取名

# Key
export OPENAI_API_KEY="YOUR OWN API KEY"

# 评测参数
export TEMP=0
export TOP_P=1.0
export MAX_NEW_TOKENS=128


# Hugging Face API Key

