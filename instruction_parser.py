# instruction_parser.py

import edge_tts
import re, json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


from openai import OpenAI


import requests
import json
import re

base_url  = "https://api.deepseek.com"  
API_KEY = "YOUR OWN API KEY"  
# -----


def chat_with_deepseek(prompt):
    system_prompt = (
        "你是一个自动驾驶语音助手，请只提取起点和终点，"
        "返回格式为严格的 JSON: {\"start\": \"...\", \"end\": \"...\"}。\n"
        "可选地点（必须从这些中选，输出英文）:\n"
        "home, school, hospital, market, shoppingMall, office, officeParking, parking, railway, highspeed。\n"
        "不要输出中文，不要解释说明。"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"从{prompt}出发"}
    ]

    payload = {
        "model": "deepseek-chat",  
        "messages": messages,
        "max_tokens": 128,
        "temperature": 0.7
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(f"{base_url}/v1/chat/completions", headers=headers, json=payload)
    if response.status_code != 200:
        print(f"API调用失败: {response.status_code} - {response.text}")
        return {"start": "current", "end": "home"}

    result = response.json()
 
    text_response = result['choices'][0]['message']['content']
    print(f"DeepSeek返回原始文本: {text_response}")

    try:
        json_text = re.search(r"\{.*?\}", text_response, re.DOTALL).group()
        location_info = json.loads(json_text.replace("'", '"'))
        return location_info
    except Exception as e:
        print(f"解析JSON失败: {e}, 默认使用 start='current', end='home'")
        return {"start": "current", "end": "home"}


#  ========== 地点名称归一化 ==========
alias_map = {
        "家": "home", "home": "home",
        "医院": "hospital", "hospital": "hospital",
        "学校": "school", "school": "school",
        "市场": "market", "超市": "market", "market": "market",
        "商场": "shoppingMall", "shopping mall": "shoppingMall", "购物中心": "shoppingMall",
        "办公楼": "office", "公司": "office", "office": "office",
        "公司停车场": "officeParking", "办公楼停车场": "officeParking",
        "停车场": "parking", "停车位": "parking",
        "车站": "railway", "railway": "railway",
        "高速": "highspeed", "highway": "highspeed", "highspeed": "highspeed"
}

def normalize_place_name(name):
    if not name:
        return None
    name = name.strip().lower() 
    
    return alias_map.get(name, name)


# ========== TTS 语音合成 ==========
async def speak(text, voice="zh-CN-XiaoxiaoNeural"):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save("reply.mp3")
    from playsound import playsound
    playsound("reply.mp3")

