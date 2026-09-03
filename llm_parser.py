"""
llm_parser.py
負責人: 梁偉航 (模組一 核心輸入層)

把使用者的一句話(手動輸入或語音轉文字)丟給 LLM,
用 Structured Output (response_schema) 強制模型回傳固定格式的 JSON,
避免自由文字造成後端解析崩潰。

使用 Google Gemini (免費方案有額度)。
金鑰取得: https://aistudio.google.com/apikey

模型選擇說明 (2026/9):
  gemini-3.5-flash-lite -- 目前最新一代裡最便宜、最快的型號，
  官方定位就是「document parsing / subagent 高頻任務」，這種短句
  拆解記帳的任務完全用不到大模型的推理能力，選這隻最划算
  ($0.30 / $2.50 每百萬 token)。
  如果之後發現複雜複合句解析常常漏掉事件，再考慮換成
  gemini-3.6-flash 或 gemini-3.7-flash（更強、但貴上好幾倍）。

  舊版原本寫的 gemini-2.0-flash 已於 2026/6/1 正式下架，
  現在打會直接收到 404，這是這次最優先要修的問題。

對應驗收標準:
  "輸入包含購買、採收、分區、金額的複合語句,
   系統能於 3 秒內透過 LLM 正確拆解為對應實體欄位並分別寫入資料庫對應表"
"""

import os
import json
from typing import Optional
from google import genai
from google.genai import types

MODEL_NAME = os.getenv("GEMINI_MODEL_NAME") or "gemini-3.5-flash-lite"
# 注意: 用 os.getenv("X", "default") 的寫法在 .env 裡寫 X=（空字串）
# 時不會退回 default，只有完全沒這個 key 才會退回。用 "or" 才能同時
# 涵蓋「沒設定」跟「設定了但是空字串」這兩種情況。

SYSTEM_PROMPT = """你是 PlantQuest 植栽系統的 AI 記帳解析器。
使用者會用口語化的一句中文描述他剛才做的園藝相關行為(可能同時包含買東西、採收、澆水等多件事)。
你的任務是把這句話拆解成結構化事件,並以 JSON 格式回傳。

規則:
- 一句話可能包含多個事件,全部拆出來,不要遺漏也不要合併。
- 金額、重量沒提到就填 0,不要自己編造數字。
- action_type 判斷不出來的花銷歸類到 generic_expense。
- companion_feedback 要像 RPG 遊戲管家的語氣,簡短、生動、正向(不超過 40 字)。
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "description": "拆解出的事件清單,一句話可能包含多個事件",
            "items": {
                "type": "object",
                "properties": {
                    "action_type": {
                        "type": "string",
                        "enum": [
                            "plant_purchase",
                            "tool_purchase",
                            "container_purchase",
                            "supply_purchase",
                            "harvest",
                            "generic_expense",
                        ],
                    },
                    "item_name": {"type": "string", "description": "品項名稱,例如鹿角蕨、修枝剪、赤玉土"},
                    "amount": {"type": "number", "description": "花費金額,沒提到就填 0"},
                    "quality_rating": {"type": "integer", "description": "1-5 的品質評分,沒提到就填 0"},
                    "market_stall_name": {"type": "string", "description": "花市或攤位名稱,例如 花市A3攤"},
                    "zone_name": {"type": "string", "description": "分區名稱,例如 陽台、室內燈養區"},
                    "crop_name": {"type": "string", "description": "採收作物名稱,僅 harvest 使用"},
                    "part": {"type": "string", "description": "採收部位,例如 葉、果實,僅 harvest 使用"},
                    "weight_g": {"type": "number", "description": "採收重量(公克),僅 harvest 使用"},
                    "unit": {"type": "string", "description": "耗材單位,例如 公升、包,僅 supply_purchase 使用"},
                    "quantity": {"type": "number", "description": "耗材數量,僅 supply_purchase 使用"},
                },
                "required": ["action_type"],
            },
        },
        "companion_feedback": {
            "type": "string",
            "description": "用 RPG 園藝管家的口吻,對這次記帳給一句簡短生動的中文回饋(不超過 40 字)",
        },
    },
    "required": ["events", "companion_feedback"],
}


class ParseError(Exception):
    pass


def parse_dictation(raw_text: str, api_key: Optional[str] = None) -> dict:
    """
    呼叫 Gemini 解析一句話,回傳 {"events": [...], "companion_feedback": "..."}。
    """
    if not raw_text or not raw_text.strip():
        raise ParseError("輸入文字為空白")

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ParseError("GEMINI_API_KEY 未設定,請至 https://aistudio.google.com/apikey 申請免費金鑰")

    client = genai.Client(api_key=key)

    last_error = None
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=raw_text,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                    max_output_tokens=1024,
                ),
            )
            result = json.loads(response.text)
            if "events" not in result or "companion_feedback" not in result:
                raise ParseError("LLM 回傳缺少必要欄位")
            return result
        except json.JSONDecodeError as e:
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue

    raise ParseError(f"LLM 解析失敗(已重試): {last_error}")
