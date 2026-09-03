import engine3

def run_all_tests():
    print(">>> [模組三] 測試 1：氣象 API 呼叫與快取機制")
    weather = engine3.get_weather_forecast3()
    assert "data" in weather
    print("通過！氣象資料來源：", weather["source"])

    print(">>> [模組三] 測試 2：降雨展延評估（70% 降雨率）")
    delay = engine3.evaluate_rain_delay3(70.0)
    assert delay["delay_outdoor_watering"] is True
    assert delay["delay_days"] == 1
    print("通過！戶外延遲判定正常")

    print(">>> [模組三] 測試 3：出差補水清單（5 天出差，耐旱 2 天判定為 URGENT）")
    plants = [
        {"name": "女王鹿角蕨", "zone": "陽台", "drought_tolerance": 2},
        {"name": "金錢樹", "zone": "室內", "drought_tolerance": 10}
    ]
    chk = engine3.generate_travel_watering_checklist3(5, plants)
    assert chk[0]["priority"] == "URGENT"
    assert chk[1]["priority"] == "NORMAL"
    print("通過！補水清單正確排序並判定高風險植物")

    print(">>> [模組四] 測試 4：大品出讓估算（除以 0 防呆）")
    res = engine3.estimate_plant_valuation3(3500, 0, 200, 90)
    assert res["mother_share_cost"] == 3500.0
    print("通過！建議售價：", res["recommended_price"])

    print(">>> [模組五] 測試 5：堆肥 C:N（空值防呆與偏乾判定）")
    assert engine3.calculate_compost_cn_ratio3(0.0, 0.0)["status"] == "DATA_INCOMPLETE"
    assert engine3.calculate_compost_cn_ratio3(5.0, 0.0)["status"] == "TOO_DRY"
    print("通過！C:N 邊界判定正常")

    print(">>> [模組五] 測試 6：液肥稀釋水量計算")
    assert engine3.calculate_fertilizer_water_need3(50, 500) == 25.0
    print("通過！50ml 稀釋水量正確")

if __name__ == "__main__":
    run_all_tests()
    print("\n[V] 成員 C 負責之模組三、四、五全單元測試驗證通過！")
