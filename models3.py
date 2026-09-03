from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

# ==================== 模組二~五原有表 (成員 C) ====================

class MarketPurchase3(Base):
    __tablename__ = "market_purchases3"
    id = Column(Integer, primary_key=True, index=True)
    stall_name = Column(String, index=True)
    item_name = Column(String)
    price = Column(Float)
    quality_score = Column(Integer, default=5)
    note = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PotMaterialInventory3(Base):
    __tablename__ = "pot_material_inventories3"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String)
    name = Column(String)
    unit_cost = Column(Float, default=0.0)
    stock_qty = Column(Integer, default=0)
    in_use_qty = Column(Integer, default=0)

class CompostBatchLog3(Base):
    __tablename__ = "compost_batch_logs3"
    id = Column(Integer, primary_key=True, index=True)
    batch_name = Column(String)
    dry_carbon_kg = Column(Float)
    wet_nitrogen_kg = Column(Float)
    calculated_cn = Column(Float)
    status = Column(String)
    start_date = Column(String, default=lambda: datetime.date.today().isoformat())
    ferment_days = Column(Integer, default=30)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LiquidFertilizerLog3(Base):
    __tablename__ = "liquid_fertilizer_logs3"
    id = Column(Integer, primary_key=True, index=True)
    collected_ml = Column(Float)
    dilution_ratio = Column(Integer, default=500)
    water_needed_liters = Column(Float)
    target_zone = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# ==================== 模組一新增表 (梁偉航 - 核心輸入層) ====================

class WateringZone(Base):
    __tablename__ = "watering_zones"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class MarketStall(Base):
    __tablename__ = "market_stalls"
    id = Column(Integer, primary_key=True, index=True)
    market_name = Column(String, index=True)
    stall_label = Column(String, nullable=True)

class Plant(Base):
    __tablename__ = "plants"
    id = Column(Integer, primary_key=True, index=True)
    species = Column(String)
    nickname = Column(String, nullable=True)
    status = Column(String, default="在役")
    zone_id = Column(Integer, nullable=True)
    generation = Column(Integer, default=1)
    acquired_at = Column(String)
    acquired_cost = Column(Float, default=0.0)
    drought_resilience = Column(Integer, default=3)
    contribution_score = Column(Integer, default=0)
    mother_id = Column(Integer, nullable=True)
    father_id = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True)

class Tool(Base):
    __tablename__ = "tools"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    cost = Column(Float, default=0.0)
    purchased_at = Column(String)

class Container(Base):
    __tablename__ = "containers"
    id = Column(Integer, primary_key=True, index=True)
    spec = Column(String)
    status = Column(String, default="空盆")
    cost = Column(Float, default=0.0)

class Supply(Base):
    __tablename__ = "supplies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    unit = Column(String, default="unit")
    quantity_on_hand = Column(Float, default=0.0)
    last_restocked_at = Column(String, nullable=True)

class Harvest(Base):
    __tablename__ = "harvests"
    id = Column(Integer, primary_key=True, index=True)
    plant_id = Column(Integer, nullable=True)
    crop_name = Column(String)
    part = Column(String, default="未指定")
    weight_g = Column(Float, default=0.0)
    harvested_at = Column(String)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    amount = Column(Float, default=0.0)
    item_name = Column(String)
    quality_rating = Column(Integer, nullable=True)
    market_stall_id = Column(Integer, nullable=True)
    plant_id = Column(Integer, nullable=True)
    tool_id = Column(Integer, nullable=True)
    container_id = Column(Integer, nullable=True)
    supply_id = Column(Integer, nullable=True)
    occurred_at = Column(String)
    source = Column(String, default="dictation")
    raw_text = Column(String, nullable=True)

class DictationLog(Base):
    __tablename__ = "dictation_logs"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String)
    raw_text = Column(String)
    parsed_json = Column(Text, nullable=True)
    status = Column(String, index=True)
    error_message = Column(String, nullable=True)
    companion_feedback = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PlantPhoto(Base):
    __tablename__ = "plant_photos"
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String)
    entity_id = Column(String)
    category = Column(String, nullable=True)
    photo_url = Column(String)
    caption = Column(String, nullable=True)
    taken_at = Column(String)
