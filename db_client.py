"""
db_client.py
負責人: 梁偉航 (模組一 核心輸入層)

集中管理所有 SQLite 資料庫讀寫操作 (SQLAlchemy)。
其他模組串接時,應該複用這裡的 session 建立方式,
不要各自用不同的連線設定,避免連線管理混亂。
"""

import json
from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from database import SessionLocal
import models3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_session() -> Session:
    return SessionLocal()


# ------------------------------------------------------------
# 查找輔助函式 (找不到就自動建立)
# ------------------------------------------------------------

def find_or_create_market_stall(market_name: str, stall_label: Optional[str] = None) -> Optional[int]:
    if not market_name:
        return None
    session = get_session()
    try:
        query = session.query(models3.MarketStall).filter(models3.MarketStall.market_name == market_name)
        if stall_label:
            query = query.filter(models3.MarketStall.stall_label == stall_label)
        existing = query.first()
        if existing:
            return existing.id
        stall = models3.MarketStall(market_name=market_name, stall_label=stall_label)
        session.add(stall)
        session.commit()
        session.refresh(stall)
        return stall.id
    finally:
        session.close()


def find_zone_by_name(zone_name: str) -> Optional[int]:
    if not zone_name:
        return None
    session = get_session()
    try:
        zone = session.query(models3.WateringZone).filter(models3.WateringZone.name == zone_name).first()
        return zone.id if zone else None
    finally:
        session.close()


# ------------------------------------------------------------
# 各表寫入函式
# ------------------------------------------------------------

def create_plant(species: str, acquired_cost: float, zone_name: Optional[str] = None,
                  nickname: Optional[str] = None) -> str:
    session = get_session()
    try:
        zone_id = find_zone_by_name(zone_name) if zone_name else None
        plant = models3.Plant(
            species=species,
            nickname=nickname,
            status="在役",
            zone_id=zone_id,
            generation=1,
            acquired_at=date.today().isoformat(),
            acquired_cost=max(0.0, acquired_cost or 0.0),
            drought_resilience=3,
            contribution_score=0,
        )
        session.add(plant)
        session.commit()
        session.refresh(plant)
        return str(plant.id)
    finally:
        session.close()


def create_tool(name: str, cost: float) -> str:
    session = get_session()
    try:
        tool = models3.Tool(
            name=name,
            cost=max(0.0, cost or 0.0),
            purchased_at=date.today().isoformat(),
        )
        session.add(tool)
        session.commit()
        session.refresh(tool)
        return str(tool.id)
    finally:
        session.close()


def create_container(spec: str, cost: float) -> str:
    session = get_session()
    try:
        container = models3.Container(
            spec=spec,
            status="空盆",
            cost=max(0.0, cost or 0.0),
        )
        session.add(container)
        session.commit()
        session.refresh(container)
        return str(container.id)
    finally:
        session.close()


def upsert_supply(name: str, unit: str, quantity_delta: float) -> str:
    """耗材/介質: 有就疊加庫存量,沒有就新建一筆。"""
    session = get_session()
    try:
        existing = session.query(models3.Supply).filter(models3.Supply.name == name).first()
        if existing:
            new_qty = max(0.0, (existing.quantity_on_hand or 0.0) + quantity_delta)
            existing.quantity_on_hand = new_qty
            if quantity_delta > 0:
                existing.last_restocked_at = _now_iso()
            session.commit()
            return str(existing.id)
        else:
            supply = models3.Supply(
                name=name,
                unit=unit or "unit",
                quantity_on_hand=max(0.0, quantity_delta),
                last_restocked_at=_now_iso() if quantity_delta > 0 else None,
            )
            session.add(supply)
            session.commit()
            session.refresh(supply)
            return str(supply.id)
    finally:
        session.close()


def create_harvest(crop_name: str, part: str, weight_g: float, plant_id: Optional[str] = None) -> str:
    session = get_session()
    try:
        harvest = models3.Harvest(
            plant_id=int(plant_id) if plant_id else None,
            crop_name=crop_name,
            part=part or "未指定",
            weight_g=max(0.0, weight_g or 0.0),
            harvested_at=_now_iso(),
        )
        session.add(harvest)
        session.commit()
        session.refresh(harvest)
        return str(harvest.id)
    finally:
        session.close()


def create_transaction(tx_type: str, amount: float, item_name: str,
                        quality_rating: Optional[int] = None,
                        market_stall_id: Optional[str] = None,
                        plant_id: Optional[str] = None,
                        tool_id: Optional[str] = None,
                        container_id: Optional[str] = None,
                        supply_id: Optional[str] = None,
                        source: str = "dictation",
                        raw_text: Optional[str] = None) -> str:
    session = get_session()
    try:
        tx = models3.Transaction(
            type=tx_type,
            amount=max(0.0, amount or 0.0),
            item_name=item_name,
            quality_rating=quality_rating,
            market_stall_id=int(market_stall_id) if market_stall_id else None,
            plant_id=int(plant_id) if plant_id else None,
            tool_id=int(tool_id) if tool_id else None,
            container_id=int(container_id) if container_id else None,
            supply_id=int(supply_id) if supply_id else None,
            occurred_at=_now_iso(),
            source=source,
            raw_text=raw_text,
        )
        session.add(tx)
        session.commit()
        session.refresh(tx)
        return str(tx.id)
    finally:
        session.close()


def log_dictation(source: str, raw_text: str, parsed_json: Optional[dict],
                   status: str, error_message: Optional[str] = None,
                   companion_feedback: Optional[str] = None) -> str:
    session = get_session()
    try:
        log = models3.DictationLog(
            source=source,
            raw_text=raw_text,
            parsed_json=json.dumps(parsed_json, ensure_ascii=False) if parsed_json else None,
            status=status,
            error_message=error_message,
            companion_feedback=companion_feedback,
        )
        session.add(log)
        session.commit()
        session.refresh(log)
        return str(log.id)
    finally:
        session.close()


def create_plant_photo(entity_type: str, entity_id: str, photo_url: str,
                        category: Optional[str] = None, caption: Optional[str] = None) -> str:
    session = get_session()
    try:
        photo = models3.PlantPhoto(
            entity_type=entity_type,
            entity_id=entity_id,
            category=category,
            photo_url=photo_url,
            caption=caption,
            taken_at=_now_iso(),
        )
        session.add(photo)
        session.commit()
        session.refresh(photo)
        return str(photo.id)
    finally:
        session.close()


def get_dictation_logs(limit: int = 20) -> list:
    session = get_session()
    try:
        logs = session.query(models3.DictationLog).order_by(
            models3.DictationLog.created_at.desc()
        ).limit(limit).all()
        result = []
        for log in logs:
            result.append({
                "id": log.id,
                "source": log.source,
                "raw_text": log.raw_text,
                "parsed_json": json.loads(log.parsed_json) if log.parsed_json else None,
                "status": log.status,
                "error_message": log.error_message,
                "companion_feedback": log.companion_feedback,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            })
        return result
    finally:
        session.close()
