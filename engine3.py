import time
import requests
from typing import Dict, List, Any

# ==================== 模組三：常數與記憶體快取 ====================
WEATHER_CACHE3: Dict[str, Any] = {
    "timestamp": 0,
    "data": None
}
CACHE_TTL_SECONDS3 = 7200  # 2 小時快取 (7200 秒)

# ==================== 模組五：堆肥常數 ====================
COMPOST_CONSTANTS3 = {
    "DRY_CARBON_C_RATIO": 0.50,
    "DRY_CARBON_N_RATIO": 0.01,
    "WET_NITROGEN_C_RATIO": 0.30,
    "WET_NITROGEN_N_RATIO": 0.02,
    "OPTIMAL_MIN": 25.0,
    "OPTIMAL_MAX": 30.0
}

# ==================== 模組三演算法 ====================

def get_weather_forecast3(latitude: float = 24.1477, longitude: float = 120.6736) -> Dict[str, Any]:
    """
    呼叫 Open-Meteo 免費氣象 API，附帶 2 小時快取與斷線 Fallback 機制
    """
    current_time = time.time()
    
    # 1. 命中快取
    if WEATHER_CACHE3["data"] and (current_time - WEATHER_CACHE3["timestamp"] < CACHE_TTL_SECONDS3):
        return {"source": "cache", "data": WEATHER_CACHE3["data"]}
    
    # 2. 請求外部 API
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "precipitation_probability_max,precipitation_sum",
        "timezone": "Asia/Taipei"
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        json_data = response.json()
        WEATHER_CACHE3["timestamp"] = current_time
        WEATHER_CACHE3["data"] = json_data
        return {"source": "api", "data": json_data}
    except Exception as e:
        # Fallback 預設數據，保證系統不崩潰
        fallback_data = {
            "daily": {
                "precipitation_probability_max": [20, 20, 20],
                "precipitation_sum": [0.0, 0.0, 0.0]
            },
            "error_note": f"Weather API offline, fallback triggered: {str(e)}"
        }
        return {"source": "fallback", "data": fallback_data}

def evaluate_rain_delay3(precipitation_prob: float, threshold: float = 60.0) -> Dict[str, Any]:
    """降雨展延評估演算法"""
    prob = max(0.0, min(100.0, float(precipitation_prob or 0.0)))
    should_delay = prob >= threshold
    return {
        "precipitation_probability": prob,
        "delay_outdoor_watering": should_delay,
        "delay_days": 1 if should_delay else 0,
        "indoor_action": "燈養環境恆定，維持正常照護排程"
    }

def generate_travel_watering_checklist3(travel_days: int, plants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """出差戰略補水 Checklist 生成演算法"""
    safe_days = max(1, int(travel_days or 1))
    checklist = []
    
    for p in plants:
        name = p.get("name", "未命名植物")
        zone = p.get("zone", "陽台")
        tolerance = max(1, int(p.get("drought_tolerance", 3)))
        
        is_high_risk = tolerance < safe_days
        if is_high_risk:
            strategy = "【高危險】行前浸盆吸飽水，底盤蓄水或移至遮陰處防蒸散"
            priority = "URGENT"
        else:
            strategy = "【安全】行前正常給水即可平安度過"
            priority = "NORMAL"
            
        checklist.append({
            "plant_name": name,
            "zone": zone,
            "drought_tolerance_days": tolerance,
            "travel_days": safe_days,
            "priority": priority,
            "action_guidance": strategy
        })
    
    checklist.sort(key=lambda x: 0 if x["priority"] == "URGENT" else 1)
    return checklist

# ==================== 模組四演算法 ====================

def calculate_stall_summary3(purchases: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not purchases:
        return {"total_records": 0, "avg_quality": 0.0, "star_rating": 0, "status": "無資料"}
    valid_scores = [max(1, min(5, p.get("quality_score", 3))) for p in purchases]
    avg_score = sum(valid_scores) / len(valid_scores)
    return {
        "total_records": len(purchases),
        "average_quality_score": round(avg_score, 2),
        "star_rating": round(avg_score),
        "recommendation": "優選優質攤位" if avg_score >= 4.0 else ("一般市集攤位" if avg_score >= 3.0 else "列入觀察黑名單")
    }

def estimate_plant_valuation3(mother_cost: float, sub_count: int, materials_cost: float, rearing_days: int, daily_care_rate: float = 2.0, target_margin: float = 0.30) -> Dict[str, float]:
    safe_mother_cost = max(0.0, float(mother_cost or 0.0))
    safe_sub_count = max(1, int(sub_count or 1))
    safe_materials = max(0.0, float(materials_cost or 0.0))
    safe_days = max(0, int(rearing_days or 0))
    safe_margin = max(0.01, min(0.90, float(target_margin or 0.30)))
    mother_share = safe_mother_cost / safe_sub_count
    care_cost = safe_days * daily_care_rate
    total_cost = mother_share + safe_materials + care_cost
    recommended_price = total_cost / (1.0 - safe_margin)
    return {
        "mother_share_cost": round(mother_share, 1),
        "materials_cost": round(safe_materials, 1),
        "care_cost": round(care_cost, 1),
        "total_base_cost": round(total_cost, 1),
        "recommended_price": round(recommended_price, 0),
        "expected_profit": round(recommended_price - total_cost, 0),
        "margin_percentage": round(safe_margin * 100, 1)
    }

# ==================== 模組五演算法 ====================

def calculate_compost_cn_ratio3(dry_carbon_kg: float, wet_nitrogen_kg: float) -> Dict[str, Any]:
    safe_dry = max(0.0, float(dry_carbon_kg or 0.0))
    safe_wet = max(0.0, float(wet_nitrogen_kg or 0.0))
    if safe_dry == 0.0 and safe_wet == 0.0:
        return {"cn_ratio": 0.0, "status": "DATA_INCOMPLETE", "message": "尚未投入任何堆肥材料。"}
    c_mass = (safe_dry * COMPOST_CONSTANTS3["DRY_CARBON_C_RATIO"]) + (safe_wet * COMPOST_CONSTANTS3["WET_NITROGEN_C_RATIO"])
    n_mass = (safe_dry * COMPOST_CONSTANTS3["DRY_CARBON_N_RATIO"]) + (safe_wet * COMPOST_CONSTANTS3["WET_NITROGEN_N_RATIO"])
    if n_mass == 0.0:
        return {"cn_ratio": 0.0, "status": "DATA_INCOMPLETE", "message": "尚未加入含氮材料，無法發酵。"}
    cn_ratio = c_mass / n_mass
    if COMPOST_CONSTANTS3["OPTIMAL_MIN"] <= cn_ratio <= COMPOST_CONSTANTS3["OPTIMAL_MAX"]:
        status, msg = "OPTIMAL", "完美黃金發酵比例 (25~30:1)！"
    elif cn_ratio < COMPOST_CONSTANTS3["OPTIMAL_MIN"]:
        status, msg = "TOO_WET", f"目前比例為 {cn_ratio:.1f}:1，偏濕偏氮，請補乾料。"
    else:
        status, msg = "TOO_DRY", f"目前比例為 {cn_ratio:.1f}:1，偏乾偏碳，請補廚餘。"
    return {"dry_kg": safe_dry, "wet_kg": safe_wet, "cn_ratio": round(cn_ratio, 2), "status": status, "message": msg}

def calculate_fertilizer_water_need3(collected_ml: float, dilution_ratio: int = 500) -> float:
    safe_ml = max(0.0, float(collected_ml or 0.0))
    safe_ratio = max(1, int(dilution_ratio or 500))
    return round((safe_ml * safe_ratio) / 1000.0, 2)
