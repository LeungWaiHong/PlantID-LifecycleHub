# 植栽數位編號履歷與生命週期精算系統 (PlantQuest Hub)
## 成員 C 核心演算法與後端 API 模組交付文件

---

### 一、 模組概述與職責分配
本模組主要負責系統後端分析、演算法邏輯計算、微氣候資料快取，以及與成員 B 前端展示層 (index3.html) 之雙向 API 連動。

* **開發環境**：Python 3.10+ / FastAPI / SQLAlchemy / SQLite (la3_plantquest3.db)
* **整合前端**：index3.html (Tailwind CSS, Mermaid.js, FontAwesome)
* **交付目錄**：D:\la3\

---

### 二、 核心功能涵蓋清單

#### 1. 模組三：微氣候感知與出差戰略排程
* **即時氣象快取** (GET /api/weather/forecast)：串接 Open-Meteo API，具備 2 小時本地快取機制，避免高頻重複請求。
* **降雨展延評估** (GET /api/weather/rain-delay-check)：降雨機率達門檻自動推算戶外盆栽澆水順延天數。
* **出差補水檢核表** (POST /api/travel/checklist)：依植物耐旱能力與出差天數，自動產出優先級清單（URGENT 緊急補水標註）。

#### 2. 模組四：資材產銷、盆器流轉與花市評級
* **身價定價估算** (POST /api/pricing/valuation)：考量母株攤提、耗材水電成本與培育天數，以 30% 毛利率反推建議出讓售價與利潤。
* **盆器在役流轉** (POST /api/inventory/pot/transition)：支援「空盆待用」與「在役上盆」之雙向流轉切換。
* **花市比價與評級** (POST /api/market/purchase, GET /api/market/purchases, DELETE /api/market/purchase/{id}, GET /api/market/stall-rating/{stall_name})：記錄購買品項、價格與 1~5 星評等，自動產生全攤位評分排行榜與推薦度。
* **植株來源關聯**：植栽身分證支援直接連結歷史花市採買資料。

#### 3. 模組五：生態堆肥、翻堆日誌與黑金液肥
* **C:N 黃金碳氮比計算** (POST /api/compost/calculate-and-save)：試算落葉木屑與果皮廚餘比例，評估最佳發酵區間（25~30:1）。
* **熟成週期與倒數進度**：支援自訂發酵起始日與預計熟成天數，前端動態繪製進度條。
* **耗材消耗與翻堆筆記**：記錄菌粉、粗糠耗材與翻堆通氣狀態。
* **黑金液肥稀釋試算** (POST /api/fertilizer/log)：依原液收集量 (ml) 與稀釋倍數，精算澆灌所需清水公升數。

#### 4. 資料持久化與安全防護
* **系統備份與還原**：支援完整 JSON 匯出與一鍵匯入覆蓋，防範更換展示電腦或快取清除時資料遺失。

---

### 三、 本機快速啟動步驟

`powershell
# 1. 啟用虛擬環境
cd D:\la3
.\venv\Scripts\Activate.ps1

# 2. 安裝依賴套件 (若在新環境)
pip install -r requirements.txt

# 3. 啟動後端 FastAPI 服務
uvicorn main3:app --reload
`
