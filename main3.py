from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, Field
from typing import Optional, List
import datetime
import os
import models3
import engine3

DATABASE_URL = "sqlite:///./la3_plantquest3.db"
db_engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
models3.Base.metadata.create_all(bind=db_engine)

app = FastAPI(title="PlantQuest Hub - Member C (完整功能與刪除支援版)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------
# 讓後端順便把前端 index3.html 服務出去，這樣整個工具只有「一個網址」，
# 不用另外找地方放前端、也不會遇到 API_BASE 指錯網域的問題。
# ---------------------------------------------------------------------
FRONTEND_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index3.html")

@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_PATH)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Schemas
class PlantCareItem3(BaseModel):
    name: str
    zone: str = "陽台"
    drought_tolerance: int = 3

class TravelChecklistRequest3(BaseModel):
    travel_days: int = Field(default=3, ge=1)
    plants: List[PlantCareItem3]

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

class MaterialConsumeRequest3(BaseModel):
    material_name: str
    used_qty: float
    purpose: str = "堆肥製作"

class CompostRequest3(BaseModel):
    batch_name: str
    dry_carbon_kg: float
    wet_nitrogen_kg: float

class FertilizerCreate3(BaseModel):
    collected_ml: float
    dilution_ratio: int = 500
    target_zone: str

# 模組三
@app.get("/api/weather/forecast")
def get_weather(lat: float = 24.1477, lon: float = 120.6736):
    return engine3.get_weather_forecast3(latitude=lat, longitude=lon)

@app.get("/api/weather/rain-delay-check")
def check_rain_delay(precipitation_prob: float = Query(..., ge=0, le=100)):
    return engine3.evaluate_rain_delay3(precipitation_prob=precipitation_prob)

@app.post("/api/travel/checklist")
def create_travel_checklist(payload: TravelChecklistRequest3):
    plants_data = [p.dict() for p in payload.plants]
    checklist = engine3.generate_travel_watering_checklist3(payload.travel_days, plants_data)
    return {
        "travel_days": payload.travel_days,
        "total_plants": len(checklist),
        "urgent_count": sum(1 for c in checklist if c["priority"] == "URGENT"),
        "checklist": checklist
    }

# 模組四：花市與產銷 (支援刪除)
@app.post("/api/market/purchase")
def create_market_purchase(payload: MarketPurchaseCreate3, db: Session = Depends(get_db)):
    item = models3.MarketPurchase3(**payload.dict())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"status": "success", "data": item}

@app.get("/api/market/purchases")
def list_market_purchases(db: Session = Depends(get_db)):
    return db.query(models3.MarketPurchase3).order_by(models3.MarketPurchase3.id.desc()).all()

@app.delete("/api/market/purchase/{purchase_id}")
def delete_market_purchase(purchase_id: int, db: Session = Depends(get_db)):
    item = db.query(models3.MarketPurchase3).filter(models3.MarketPurchase3.id == purchase_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="查無此筆採買紀錄")
    db.delete(item)
    db.commit()
    return {"status": "success", "deleted_id": purchase_id}

@app.get("/api/market/stall-rating/{stall_name}")
def get_stall_rating(stall_name: str, db: Session = Depends(get_db)):
    records = db.query(models3.MarketPurchase3).filter(models3.MarketPurchase3.stall_name == stall_name).all()
    summary = engine3.calculate_stall_summary3([{"quality_score": r.quality_score} for r in records])
    return {"stall_name": stall_name, "summary": summary}

@app.post("/api/pricing/valuation")
def calculate_valuation(payload: ValuationRequest3):
    return engine3.estimate_plant_valuation3(
        payload.mother_cost, payload.sub_count, payload.materials_cost,
        payload.rearing_days, payload.daily_care_rate, payload.target_margin
    )

@app.get("/api/inventory/materials")
def list_materials(db: Session = Depends(get_db)):
    return db.query(models3.PotMaterialInventory3).all()

@app.post("/api/inventory/pot/transition")
def pot_transition(payload: PotTransitionRequest3, db: Session = Depends(get_db)):
    pot = db.query(models3.PotMaterialInventory3).filter(models3.PotMaterialInventory3.id == payload.pot_id).first()
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
    db.commit()
    return {"status": "success", "stock_qty": pot.stock_qty, "in_use_qty": pot.in_use_qty}

# 模組五
@app.post("/api/compost/calculate-and-save")
def compost_calc(payload: CompostRequest3, db: Session = Depends(get_db)):
    calc = engine3.calculate_compost_cn_ratio3(payload.dry_carbon_kg, payload.wet_nitrogen_kg)
    log = models3.CompostBatchLog3(
        batch_name=payload.batch_name,
        dry_carbon_kg=payload.dry_carbon_kg,
        wet_nitrogen_kg=payload.wet_nitrogen_kg,
        calculated_cn=calc["cn_ratio"],
        status=calc["status"]
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"batch_id": log.id, "calculation": calc}

@app.post("/api/fertilizer/log")
def fertilizer_log(payload: FertilizerCreate3, db: Session = Depends(get_db)):
    water = engine3.calculate_fertilizer_water_need3(payload.collected_ml, payload.dilution_ratio)
    log = models3.LiquidFertilizerLog3(
        collected_ml=payload.collected_ml,
        dilution_ratio=payload.dilution_ratio,
        water_needed_liters=water,
        target_zone=payload.target_zone
    )
    db.add(log)
    db.commit()
    return {"status": "success", "water_needed_liters": water}
