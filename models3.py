from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

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