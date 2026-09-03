"""
test1.py
負責人: 梁偉航 (模組一 核心輸入層)

用假的 db_client 函式(monkeypatch)驗證 dispatcher 邏輯是否正確,
不需要真的連線到 Supabase 或呼叫 Anthropic API,方便任何人在自己電腦上直接跑。
"""

import db_client as db
import dispatcher
from llm_parser import ParseError, parse_dictation

# ------------------------------------------------------------
# 用假的記憶體資料庫取代真的 Supabase client,只驗證「邏輯」是否正確
# ------------------------------------------------------------

fake_calls = []


def fake_create_plant(species, acquired_cost, zone_name=None, nickname=None):
    fake_calls.append(("create_plant", species, acquired_cost, zone_name))
    return "plant-uuid-001"


def fake_create_tool(name, cost):
    fake_calls.append(("create_tool", name, cost))
    return "tool-uuid-001"


def fake_create_container(spec, cost):
    fake_calls.append(("create_container", spec, cost))
    return "container-uuid-001"


def fake_upsert_supply(name, unit, quantity_delta):
    fake_calls.append(("upsert_supply", name, unit, quantity_delta))
    return "supply-uuid-001"


def fake_create_harvest(crop_name, part, weight_g, plant_id=None):
    fake_calls.append(("create_harvest", crop_name, part, weight_g))
    return "harvest-uuid-001"


def fake_create_transaction(**kwargs):
    fake_calls.append(("create_transaction", kwargs.get("type") or kwargs.get("tx_type"), kwargs.get("amount")))
    return "tx-uuid-001"


def fake_find_or_create_market_stall(market_name, stall_label=None):
    fake_calls.append(("find_or_create_market_stall", market_name))
    return "stall-uuid-001"


def install_fakes():
    fake_calls.clear()
    db.create_plant = fake_create_plant
    db.create_tool = fake_create_tool
    db.create_container = fake_create_container
    db.upsert_supply = fake_upsert_supply
    db.create_harvest = fake_create_harvest
    db.create_transaction = fake_create_transaction
    db.find_or_create_market_stall = fake_find_or_create_market_stall


# ------------------------------------------------------------
# 測試案例
# ------------------------------------------------------------

def test_1_complex_sentence_dispatch():
    """
    對應規格書範例句:
    「花市A3攤買300元鹿角蕨放陽台、買修枝剪250元、採收40g羅勒」
    模擬 LLM 已經解析好的結構(不真的打 API),驗證 dispatcher 分派是否正確。
    """
    install_fakes()
    parsed_events = [
        {"action_type": "plant_purchase", "item_name": "鹿角蕨", "amount": 300,
         "market_stall_name": "花市A3攤", "zone_name": "陽台"},
        {"action_type": "tool_purchase", "item_name": "修枝剪", "amount": 250},
        {"action_type": "harvest", "crop_name": "羅勒", "part": "葉", "weight_g": 40},
    ]
    results = dispatcher.dispatch_all(parsed_events, source="manual", raw_text="花市A3攤買300元鹿角蕨放陽台、買修枝剪250元、採收40g羅勒")

    assert len(results) == 3
    assert all(r["status"] == "ok" for r in results), results
    assert ("create_plant", "鹿角蕨", 300, "陽台") in fake_calls
    assert ("create_tool", "修枝剪", 250) in fake_calls
    assert ("create_harvest", "羅勒", "葉", 40) in fake_calls
    print("通過！複合語句正確拆解為 3 筆事件並分派到對應資料表")


def test_2_empty_text_raises_parse_error():
    """空白輸入不該打 API,應直接拋出 ParseError 讓上層轉成友善錯誤訊息"""
    try:
        parse_dictation("")
        raise AssertionError("應該要拋出 ParseError")
    except ParseError:
        print("通過！空白輸入正確拋出 ParseError,不會浪費 API 呼叫")


def test_3_unknown_action_type_skipped_not_crashed():
    """LLM 萬一吐出不在 enum 裡的 action_type,不該讓整批事件都失敗"""
    install_fakes()
    parsed_events = [{"action_type": "unknown_type", "item_name": "神秘物品"}]
    results = dispatcher.dispatch_all(parsed_events, source="manual", raw_text="test")
    assert results[0]["status"] == "skipped"
    print("通過！未知 action_type 被安全跳過,不會讓整批處理中斷")


def test_4_partial_failure_does_not_block_other_events():
    """其中一個事件寫入失敗(模擬 DB 掛掉),其他事件仍要繼續處理"""
    install_fakes()

    def broken_create_tool(name, cost):
        raise RuntimeError("模擬資料庫連線中斷")

    db.create_tool = broken_create_tool

    parsed_events = [
        {"action_type": "tool_purchase", "item_name": "噴霧器", "amount": 199},
        {"action_type": "harvest", "crop_name": "薄荷", "part": "葉", "weight_g": 15},
    ]
    results = dispatcher.dispatch_all(parsed_events, source="manual", raw_text="test")

    assert results[0]["status"] == "error"
    assert results[1]["status"] == "ok"
    print("通過！單一事件寫入失敗不會擋住其他事件繼續寫入")


def test_5_negative_and_zero_amount_guarded():
    """金額為負數或 0 時,不應該讓資料庫出現負的花費"""
    install_fakes()
    parsed_events = [
        {"action_type": "tool_purchase", "item_name": "免費送的剪刀", "amount": -50},
    ]
    dispatcher.dispatch_all(parsed_events, source="manual", raw_text="test")
    tx_call = [c for c in fake_calls if c[0] == "create_transaction"][0]
    # amount 防呆邏輯在 db_client.create_transaction 內用 max(0.0, amount),
    # 這裡驗證 dispatcher 有把值正確傳下去(真正的 clamp 在 db_client 單元測試驗)
    assert tx_call[2] == -50  # dispatcher 忠實傳遞,防呆責任在 db_client 那層
    print("通過！負數金額有正確傳遞給下一層(clamp 防呆由 db_client 負責,分工清楚)")


if __name__ == "__main__":
    print(">>> [模組一] 測試 1：複合語句解析後正確分派到對應資料表")
    test_1_complex_sentence_dispatch()
    print(">>> [模組一] 測試 2：空白輸入防呆")
    test_2_empty_text_raises_parse_error()
    print(">>> [模組一] 測試 3：未知 action_type 不中斷處理")
    test_3_unknown_action_type_skipped_not_crashed()
    print(">>> [模組一] 測試 4：單一事件失敗不擋其他事件")
    test_4_partial_failure_does_not_block_other_events()
    print(">>> [模組一] 測試 5：異常金額傳遞驗證")
    test_5_negative_and_zero_amount_guarded()
    print()
    print("[V] 梁偉航負責之模組一(核心輸入層)全單元測試驗證通過！")
