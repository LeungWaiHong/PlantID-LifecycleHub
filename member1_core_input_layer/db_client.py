"""
db_client.py
負責人: 梁偉航 (模組一 核心輸入層)

集中管理所有 Supabase 讀寫操作。
其他模組(建豪/庭緯)串接時,應該複用這裡的 client 建立方式,
不要各自用不同的連線設定,避免 RLS / key 用錯這種問題重複發生。
"""

import os
from datetime import date, datetime, timezone
from typing import Optional
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # 後端一律用 service_role key,不用 anon key

_client: Optional[Client] = None


def get_client() -> Client:
    """
    取得 Supabase client(單例)。
    後端服務一律用 service_role key,因為要繞過 RLS 寫入多張表。
    前端(庭緯的 index.html)如果之後要直連 Supabase,則必須用 anon key
    並搭配 RLS policy,絕對不能把 service_role key 放進前端程式碼。
    """
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError(
                "缺少 SUPABASE_URL 或 SUPABASE_SERVICE_KEY 環境變數,"
                "請確認 .env 是否有正確設定並被載入。"
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------
# 查找輔助函式(找不到就自動建立,避免 LLM 解析出的名稱在資料庫裡沒有對應資料)
# ------------------------------------------------------------

def find_or_create_market_stall(market_name: str, stall_label: Optional[str] = None) -> Optional[str]:
    if not market_name:
        return None
    client = get_client()
    query = client.table("market_stalls").select("id").eq("market_name", market_name)
    if stall_label:
        query = query.eq("stall_label", stall_label)
    res = query.limit(1).execute()
    if res.data:
        return res.data[0]["id"]
    insert_res = client.table("market_stalls").insert({
        "market_name": market_name,
        "stall_label": stall_label,
    }).execute()
    return insert_res.data[0]["id"] if insert_res.data else None


def find_zone_by_name(zone_name: str) -> Optional[str]:
    if not zone_name:
        return None
    client = get_client()
    res = client.table("watering_zones").select("id").eq("name", zone_name).limit(1).execute()
    if res.data:
        return res.data[0]["id"]
    return None


# ------------------------------------------------------------
# 各表寫入函式
# ------------------------------------------------------------

def create_plant(species: str, acquired_cost: float, zone_name: Optional[str] = None,
                  nickname: Optional[str] = None) -> str:
    client = get_client()
    zone_id = find_zone_by_name(zone_name) if zone_name else None
    payload = {
        "species": species,
        "nickname": nickname,
        "status": "在役",
        "zone_id": zone_id,
        "generation": 1,
        "acquired_at": date.today().isoformat(),
        "acquired_cost": max(0.0, acquired_cost or 0.0),
        "drought_resilience": 3,
        "contribution_score": 0,
    }
    res = client.table("plants").insert(payload).execute()
    return res.data[0]["id"]


def create_tool(name: str, cost: float) -> str:
    client = get_client()
    payload = {
        "name": name,
        "cost": max(0.0, cost or 0.0),
        "purchased_at": date.today().isoformat(),
    }
    res = client.table("tools").insert(payload).execute()
    return res.data[0]["id"]


def create_container(spec: str, cost: float) -> str:
    client = get_client()
    payload = {
        "spec": spec,
        "status": "空盆",
        "cost": max(0.0, cost or 0.0),
    }
    res = client.table("containers").insert(payload).execute()
    return res.data[0]["id"]


def upsert_supply(name: str, unit: str, quantity_delta: float) -> str:
    """
    耗材/介質: 有就疊加庫存量,沒有就新建一筆。
    quantity_delta 允許負數(消耗),但最終庫存不會低於 0。
    """
    client = get_client()
    existing = client.table("supplies").select("id, quantity_on_hand").eq("name", name).limit(1).execute()
    if existing.data:
        row = existing.data[0]
        new_qty = max(0.0, (row["quantity_on_hand"] or 0.0) + quantity_delta)
        client.table("supplies").update({
            "quantity_on_hand": new_qty,
            "last_restocked_at": _now_iso() if quantity_delta > 0 else None,
        }).eq("id", row["id"]).execute()
        return row["id"]
    else:
        payload = {
            "name": name,
            "unit": unit or "unit",
            "quantity_on_hand": max(0.0, quantity_delta),
            "last_restocked_at": _now_iso() if quantity_delta > 0 else None,
        }
        res = client.table("supplies").insert(payload).execute()
        return res.data[0]["id"]


def create_harvest(crop_name: str, part: str, weight_g: float, plant_id: Optional[str] = None) -> str:
    client = get_client()
    payload = {
        "plant_id": plant_id,
        "crop_name": crop_name,
        "part": part or "未指定",
        "weight_g": max(0.0, weight_g or 0.0),
        "harvested_at": _now_iso(),
    }
    res = client.table("harvests").insert(payload).execute()
    return res.data[0]["id"]


def create_transaction(tx_type: str, amount: float, item_name: str,
                        quality_rating: Optional[int] = None,
                        market_stall_id: Optional[str] = None,
                        plant_id: Optional[str] = None,
                        tool_id: Optional[str] = None,
                        container_id: Optional[str] = None,
                        supply_id: Optional[str] = None,
                        source: str = "dictation",
                        raw_text: Optional[str] = None) -> str:
    client = get_client()
    payload = {
        "type": tx_type,
        "amount": max(0.0, amount or 0.0),
        "item_name": item_name,
        "quality_rating": quality_rating,
        "market_stall_id": market_stall_id,
        "plant_id": plant_id,
        "tool_id": tool_id,
        "container_id": container_id,
        "supply_id": supply_id,
        "occurred_at": _now_iso(),
        "source": source,
        "raw_text": raw_text,
    }
    res = client.table("transactions").insert(payload).execute()
    return res.data[0]["id"]


def log_dictation(source: str, raw_text: str, parsed_json: Optional[dict],
                   status: str, error_message: Optional[str] = None,
                   companion_feedback: Optional[str] = None) -> str:
    client = get_client()
    payload = {
        "source": source,
        "raw_text": raw_text,
        "parsed_json": parsed_json,
        "status": status,
        "error_message": error_message,
        "companion_feedback": companion_feedback,
    }
    res = client.table("dictation_logs").insert(payload).execute()
    return res.data[0]["id"]


def create_plant_photo(entity_type: str, entity_id: str, photo_url: str,
                        category: Optional[str] = None, caption: Optional[str] = None) -> str:
    client = get_client()
    payload = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "category": category,
        "photo_url": photo_url,
        "caption": caption,
        "taken_at": _now_iso(),
    }
    res = client.table("plant_photos").insert(payload).execute()
    return res.data[0]["id"]
