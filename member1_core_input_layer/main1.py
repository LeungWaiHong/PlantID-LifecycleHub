"""
main1.py
負責人: 梁偉航 (模組一 核心輸入層 - AI 園藝管家互動)

提供:
  POST /api/dictation/parse  -- 手動文字 / 語音轉文字 共用同一入口
  POST /api/photos           -- 拍照綁定植株或攤位(前端已壓縮好圖片並上傳到圖床後,這裡只存 URL)
  GET  /api/dictation/logs   -- 查詢歷史解析紀錄(除錯與管家回饋歷史用)

語音輸入的處理方式:
  瀏覽器端用 Web Speech API 或手機鍵盤語音輸入把語音轉成文字,
  前端拿到文字後一樣打 /api/dictation/parse,只是 source 傳 "voice"。
  後端不處理音訊,只處理文字 -- 這樣可以避開瀏覽器相容性問題,
  也符合技術限制提醒裡「優雅降級為純文字輸入框」的原則。
"""

import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import db_client as db
from llm_parser import parse_dictation, ParseError
from dispatcher import dispatch_all

app = FastAPI(title="PlantQuest - 核心輸入層 (模組一)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 部署時建議收斂成實際網域
    allow_methods=["*"],
    allow_headers=["*"],
)


class DictationRequest(BaseModel):
    raw_text: str = Field(..., description="使用者輸入的原始文字(手動或語音轉文字後皆可)")
    source: str = Field(default="manual", description="manual 或 voice")


class DictationResponse(BaseModel):
    status: str
    companion_feedback: str
    events_result: List[dict]
    dictation_log_id: Optional[str] = None


class PhotoBindRequest(BaseModel):
    entity_type: str = Field(..., description="plants / market_stalls / tools / containers 等")
    entity_id: str
    photo_url: str = Field(..., description="前端已壓縮並上傳到圖床後的公開 URL")
    category: Optional[str] = None
    caption: Optional[str] = None


@app.post("/api/dictation/parse", response_model=DictationResponse)
def parse_and_dispatch(req: DictationRequest):
    """
    對應驗收標準:
    「輸入包含購買、採收、分區、金額的複合語句,系統能於 3 秒內正確拆解
      為對應實體欄位並分別寫入資料庫對應表」
    """
    if req.source not in ("manual", "voice"):
        raise HTTPException(status_code=422, detail="source 必須是 manual 或 voice")

    # 第一層防呆: LLM 解析失敗(逾時/格式錯/API 掛掉)不噴 500,改回傳友善錯誤 + 記錄
    try:
        parsed = parse_dictation(req.raw_text)
    except ParseError as e:
        log_id = None
        try:
            log_id = db.log_dictation(
                source=req.source, raw_text=req.raw_text, parsed_json=None,
                status="failed", error_message=str(e),
                companion_feedback="管家有點聽不清楚,可以再說一次或用打字的嗎?",
            )
        except Exception:
            pass  # 連記錄都存不進去時,至少不要讓使用者連錯誤訊息都拿不到
        return DictationResponse(
            status="failed",
            companion_feedback="管家有點聽不清楚,可以再說一次或用打字的嗎?",
            events_result=[],
            dictation_log_id=log_id,
        )

    # 第二層: 分派寫入各表,單一事件失敗不擋其他事件
    events_result = dispatch_all(parsed["events"], source=req.source, raw_text=req.raw_text)
    overall_status = "ok" if all(r.get("status") == "ok" for r in events_result) else "partial"

    log_id = db.log_dictation(
        source=req.source, raw_text=req.raw_text, parsed_json=parsed,
        status=overall_status, companion_feedback=parsed["companion_feedback"],
    )

    return DictationResponse(
        status=overall_status,
        companion_feedback=parsed["companion_feedback"],
        events_result=events_result,
        dictation_log_id=log_id,
    )


@app.post("/api/photos")
def bind_photo(req: PhotoBindRequest):
    photo_id = db.create_plant_photo(
        entity_type=req.entity_type, entity_id=req.entity_id,
        photo_url=req.photo_url, category=req.category, caption=req.caption,
    )
    return {"id": photo_id, "status": "ok"}


@app.get("/api/dictation/logs")
def get_recent_logs(limit: int = 20):
    client = db.get_client()
    res = client.table("dictation_logs").select("*").order("created_at", desc=True).limit(limit).execute()
    return res.data


@app.get("/api/health")
def health_check():
    return {"status": "ok", "module": "core_input_layer"}
