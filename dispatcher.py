"""
dispatcher.py
負責人: 梁偉航 (模組一 核心輸入層)

把 llm_parser 解析出的結構化事件,依 action_type 分派到 db_client 對應的寫入函式。
拆成獨立檔案是為了讓 test1.py 可以直接測試分派邏輯,不需要真的連 LLM 或資料庫。
"""

from typing import Optional
import db_client as db


def dispatch_event(event: dict, source: str, raw_text: str) -> dict:
    """
    處理單一事件,回傳處理結果摘要(方便 API 回應與除錯)。
    刻意不讓單一事件失敗擋住其他事件 -- 呼叫端(main.py)會逐一 try/except。
    """
    action_type = event.get("action_type")
    amount = event.get("amount") or 0

    if action_type == "plant_purchase":
        plant_id = db.create_plant(
            species=event.get("item_name") or "未命名植株",
            acquired_cost=amount,
            zone_name=event.get("zone_name"),
        )
        stall_id = db.find_or_create_market_stall(event.get("market_stall_name")) if event.get("market_stall_name") else None
        db.create_transaction(
            tx_type="plant_purchase", amount=amount, item_name=event.get("item_name"),
            quality_rating=event.get("quality_rating"), market_stall_id=stall_id,
            plant_id=plant_id, source=source, raw_text=raw_text,
        )
        return {"action_type": action_type, "plant_id": plant_id, "status": "ok"}

    elif action_type == "tool_purchase":
        tool_id = db.create_tool(name=event.get("item_name") or "未命名工具", cost=amount)
        db.create_transaction(
            tx_type="tool_purchase", amount=amount, item_name=event.get("item_name"),
            tool_id=tool_id, source=source, raw_text=raw_text,
        )
        return {"action_type": action_type, "tool_id": tool_id, "status": "ok"}

    elif action_type == "container_purchase":
        container_id = db.create_container(spec=event.get("item_name") or "未命名盆器", cost=amount)
        db.create_transaction(
            tx_type="container_purchase", amount=amount, item_name=event.get("item_name"),
            container_id=container_id, source=source, raw_text=raw_text,
        )
        return {"action_type": action_type, "container_id": container_id, "status": "ok"}

    elif action_type == "supply_purchase":
        supply_id = db.upsert_supply(
            name=event.get("item_name") or "未命名耗材",
            unit=event.get("unit") or "unit",
            quantity_delta=event.get("quantity") or 0,
        )
        db.create_transaction(
            tx_type="supply_purchase", amount=amount, item_name=event.get("item_name"),
            supply_id=supply_id, source=source, raw_text=raw_text,
        )
        return {"action_type": action_type, "supply_id": supply_id, "status": "ok"}

    elif action_type == "harvest":
        harvest_id = db.create_harvest(
            crop_name=event.get("crop_name") or event.get("item_name") or "未命名作物",
            part=event.get("part"),
            weight_g=event.get("weight_g") or 0,
        )
        return {"action_type": action_type, "harvest_id": harvest_id, "status": "ok"}

    elif action_type == "generic_expense":
        db.create_transaction(
            tx_type="generic_expense", amount=amount, item_name=event.get("item_name") or "未分類花銷",
            source=source, raw_text=raw_text,
        )
        return {"action_type": action_type, "status": "ok"}

    else:
        return {"action_type": action_type, "status": "skipped", "reason": "未知的 action_type"}


def dispatch_all(events: list, source: str, raw_text: str) -> list:
    results = []
    for event in events:
        try:
            results.append(dispatch_event(event, source, raw_text))
        except Exception as e:
            results.append({
                "action_type": event.get("action_type"),
                "status": "error",
                "reason": str(e),
            })
    return results
