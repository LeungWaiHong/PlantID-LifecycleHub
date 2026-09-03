"""
main.py
植栽數位編號履歷與生命週期精算系統 (PlantQuest Hub)

合併三人模組的統一 FastAPI 入口:
  模組一 (梁偉航): AI 園藝管家互動 - 語音/文字記帳解析
  模組三 (蘇建豪): 環境與出差養護 - 氣象連動與補水排程
  模組四 (蘇建豪): 資材產銷 - 花市比價、盆器流轉、身價估算
  模組五 (蘇建豪): 生態堆肥 - C:N 比試算與液肥日誌

前端 index3.html (林庭緯) 由後端一併服務,前後端同源。
資料庫使用 SQLite (la3_plantquest3.db)。
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import os

import models3
import engine3
from database import SessionLocal
import db_client as db
from llm_parser import parse_dictation, ParseError
from dispatcher import dispatch_all

app = FastAPI(title="PlantQuest Hub - 植栽數位編號履歷與生命週期精算系統")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index3.html")


@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_PATH)


def get_db():
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


# ==================== 模組一: 核心輸入層 (AI 園藝管家) ====================

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
    """AI 雙模極速記帳: 手動文字 / 語音轉文字共用同一入口"""
    if req.source not in ("manual", "voice"):
        raise HTTPException(status_code=422, detail="source 必須是 manual 或 voice")

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
            pass
        return DictationResponse(
            status="failed",
            companion_feedback="管家有點聽不清楚,可以再說一次或用打字的嗎?",
            events_result=[],
            dictation_log_id=log_id,
        )

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
    return db.get_dictation_logs(limit=limit)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "module": "all", "db": "sqlite"}


# ==================== 模組三: 環境與出差養護 ====================

class PlantCareItem3(BaseModel):
    name: str
    zone: str = "陽台"
    drought_tolerance: int = 3


class TravelChecklistRequest3(BaseModel):
    travel_days: int = Field(default=3, ge=1)
    plants: List[PlantCareItem3]


@app.get("/api/weather/forecast")
def get_weather(lat: float = 24.1477, lon: float = 120.6736):
    return engine3.get_weather_forecast3(latitude=lat, longitude=lon)


@app.get("/api/weather/rain-delay-check")
def check_rain_delay(precipitation_prob: float = Query(..., ge=0, le=100)):
    return engine3.evaluate_rain_delay3(precipitation_prob=precipitation_prob)


@app.post("/api/travel/checklist")
def create_travel_checklist(payload: TravelChecklistRequest3):
    plants_data = [p.model_dump() for p in payload.plants]
    checklist = engine3.generate_travel_watering_checklist3(payload.travel_days, plants_data)
    return {
        "travel_days": payload.travel_days,
        "total_plants": len(checklist),
        "urgent_count": sum(1 for c in checklist if c["priority"] == "URGENT"),
        "checklist": checklist
    }


# ==================== 模組四: 資材產銷與花市比價 ====================

class MarketPurchaseCreate3(BaseModel):
    stall_name: str
    item_name: str
    price: float
    quality_score: int = Field(default=5, ge=1, le=5)
    note: Optional[str] = None


class ValuationRequest3(BaseModel):
    mother_cost: float
    sub_count: int = 1
    materials_cost: float = 150.0
    rearing_days: int
    daily_care_rate: float = 2.0
    target_margin: float = 0.30


class PotTransitionRequest3(BaseModel):
    pot_id: int
    action: str
    qty: float = 1.0


@app.post("/api/market/purchase")
def create_market_purchase(payload: MarketPurchaseCreate3, db_session: Session = Depends(get_db)):
    item = models3.MarketPurchase3(**payload.model_dump())
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return {"status": "success", "data": item}


@app.get("/api/market/purchases")
def list_market_purchases(db_session: Session = Depends(get_db)):
    return db_session.query(models3.MarketPurchase3).order_by(models3.MarketPurchase3.id.desc()).all()


@app.delete("/api/market/purchase/{purchase_id}")
def delete_market_purchase(purchase_id: int, db_session: Session = Depends(get_db)):
    item = db_session.query(models3.MarketPurchase3).filter(models3.MarketPurchase3.id == purchase_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="查無此筆採買紀錄")
    db_session.delete(item)
    db_session.commit()
    return {"status": "success", "deleted_id": purchase_id}


@app.get("/api/market/stall-rating/{stall_name}")
def get_stall_rating(stall_name: str, db_session: Session = Depends(get_db)):
    records = db_session.query(models3.MarketPurchase3).filter(models3.MarketPurchase3.stall_name == stall_name).all()
    summary = engine3.calculate_stall_summary3([{"quality_score": r.quality_score} for r in records])
    return {"stall_name": stall_name, "summary": summary}


@app.post("/api/pricing/valuation")
def calculate_valuation(payload: ValuationRequest3):
    return engine3.estimate_plant_valuation3(
        payload.mother_cost, payload.sub_count, payload.materials_cost,
        payload.rearing_days, payload.daily_care_rate, payload.target_margin
    )


@app.get("/api/inventory/materials")
def list_materials(db_session: Session = Depends(get_db)):
    return db_session.query(models3.PotMaterialInventory3).all()


@app.post("/api/inventory/pot/transition")
def pot_transition(payload: PotTransitionRequest3, db_session: Session = Depends(get_db)):
    pot = db_session.query(models3.PotMaterialInventory3).filter(models3.PotMaterialInventory3.id == payload.pot_id).first()
    if not pot:
        raise HTTPException(status_code=404, detail="找不到指定盆器品項")
    if payload.action == "use":
        if pot.stock_qty < payload.qty:
            raise HTTPException(status_code=400, detail="空盆庫存不足！")
        pot.stock_qty -= payload.qty
        pot.in_use_qty += payload.qty
    elif payload.action == "release":
        if pot.in_use_qty < payload.qty:
            raise HTTPException(status_code=400, detail="在役數量不足！")
        pot.in_use_qty -= payload.qty
        pot.stock_qty += payload.qty
    db_session.commit()
    return {"status": "success", "stock_qty": pot.stock_qty, "in_use_qty": pot.in_use_qty}


# ==================== 模組五: 生態堆肥與液肥 ====================

class CompostRequest3(BaseModel):
    batch_name: str
    dry_carbon_kg: float
    wet_nitrogen_kg: float


class FertilizerCreate3(BaseModel):
    collected_ml: float
    dilution_ratio: int = 500
    target_zone: str


@app.post("/api/compost/calculate-and-save")
def compost_calc(payload: CompostRequest3, db_session: Session = Depends(get_db)):
    calc = engine3.calculate_compost_cn_ratio3(payload.dry_carbon_kg, payload.wet_nitrogen_kg)
    log = models3.CompostBatchLog3(
        batch_name=payload.batch_name,
        dry_carbon_kg=payload.dry_carbon_kg,
        wet_nitrogen_kg=payload.wet_nitrogen_kg,
        calculated_cn=calc["cn_ratio"],
        status=calc["status"]
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    return {"batch_id": log.id, "calculation": calc}


@app.post("/api/fertilizer/log")
def fertilizer_log(payload: FertilizerCreate3, db_session: Session = Depends(get_db)):
    water = engine3.calculate_fertilizer_water_need3(payload.collected_ml, payload.dilution_ratio)
    log = models3.LiquidFertilizerLog3(
        collected_ml=payload.collected_ml,
        dilution_ratio=payload.dilution_ratio,
        water_needed_liters=water,
        target_zone=payload.target_zone
    )
    db_session.add(log)
    db_session.commit()
    return {"status": "success", "water_needed_liters": water}
