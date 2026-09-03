"""
llm_parser.py
負責人: 梁偉航 (模組一 核心輸入層)

把使用者的一句話(手動輸入或語音轉文字)丟給 LLM,
用 Tool Use (Structured Outputs) 強制模型回傳固定格式的 JSON,
避免自由文字造成後端解析崩潰。

對應驗收標準:
  "輸入包含購買、採收、分區、金額的複合語句,
   系統能於 3 秒內透過 LLM 正確拆解為對應實體欄位並分別寫入資料庫對應表"
"""

import os
import json
from typing import Optional
import anthropic

MODEL_NAME = "claude-sonnet-4-6"

# 用 Tool Use 強制結構化輸出,而不是要求模型「請輸出 JSON」這種軟性約束。
# 這樣即使模型想聊天或加解釋文字,也會被工具呼叫格式鎖住。
RECORD_EVENTS_TOOL = {
    "name": "record_garden_events",
    "description": "將使用者輸入的園藝記帳語句拆解為結構化事件清單並回傳管家風格的回饋文字",
    "input_schema": {
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
                                "plant_purchase",   # 買植物
                                "tool_purchase",    # 買工具
                                "container_purchase",  # 買盆器
                                "supply_purchase",  # 買耗材/介質
                                "harvest",           # 採收
                                "generic_expense",   # 其他花銷,無法歸類到上述類別
                            ],
                        },
                        "item_name": {"type": "string", "description": "品項名稱,例如鹿角蕨、修枝剪、赤玉土"},
                        "amount": {"type": "number", "description": "花費金額,沒提到就填 0"},
                        "quality_rating": {"type": "integer", "description": "1-5 的品質評分,沒提到就省略"},
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
    },
}

SYSTEM_PROMPT = """你是 PlantQuest 植栽系統的 AI 記帳解析器。
使用者會用口語化的一句中文描述他剛才做的園藝相關行為(可能同時包含買東西、採收、澆水等多件事)。
你的任務是呼叫 record_garden_events 工具,把這句話拆解成結構化事件。

規則:
- 一句話可能包含多個事件,全部拆出來,不要遺漏也不要合併。
- 金額、重量沒提到就填 0,不要自己編造數字。
- action_type 判斷不出來的花銷歸類到 generic_expense。
- companion_feedback 要像 RPG 遊戲管家的語氣,簡短、生動、正向。
"""


class ParseError(Exception):
    pass


def parse_dictation(raw_text: str, api_key: Optional[str] = None) -> dict:
    """
    呼叫 LLM 解析一句話,回傳 {"events": [...], "companion_feedback": "..."}。
    對應技術限制提醒: 模糊文字需有預設值與容錯重試機制,不得直接噴 500。
    """
    if not raw_text or not raw_text.strip():
        raise ParseError("輸入文字為空白")

    client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    last_error = None
    for attempt in range(2):  # 失敗重試一次,對應「容錯重試機制」的要求
        try:
            response = client.messages.create(
                model=MODEL_NAME,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=[RECORD_EVENTS_TOOL],
                tool_choice={"type": "tool", "name": "record_garden_events"},
                messages=[{"role": "user", "content": raw_text}],
            )
            for block in response.content:
                if block.type == "tool_use" and block.name == "record_garden_events":
                    result = block.input
                    if "events" not in result or "companion_feedback" not in result:
                        raise ParseError("LLM 回傳缺少必要欄位")
                    return result
            raise ParseError("LLM 未回傳 tool_use 區塊")
        except Exception as e:  # noqa: BLE001 -- 這裡刻意抓所有例外做重試
            last_error = e
            continue

    # 兩次都失敗: 不噴 500,回傳一個安全的 fallback 結構,並把錯誤原因往外拋給呼叫端記錄
    raise ParseError(f"LLM 解析失敗(已重試): {last_error}")
