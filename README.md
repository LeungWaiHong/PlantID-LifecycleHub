# PlantQuest Hub - 植栽數位編號履歷與生命週期精算系統

## 系統簡介

一套整合 AI 語音記帳、植物履歷管理、環境養護排程、資材產銷與生態堆肥的植栽生命週期管理工具。

## 三人模組分工

| 成員 | 負責模組 | 主要檔案 |
| :--- | :--- | :--- |
| 梁偉航 (架構/AI/DB) | 模組一: 核心輸入層 (AI 園藝管家) | `main.py` (API 端點), `db_client.py`, `dispatcher.py`, `llm_parser.py`, `database.py`, `models3.py` (模組一表) |
| 林庭緯 (前端/履歷) | 模組二: 植物履歷與繁育 | `index3.html` (前端 UI) |
| 蘇建豪 (演算法/環境/堆肥) | 模組三~五: 環境出差、資材產銷、生態堆肥 | `engine3.py`, `main.py` (模組三~五 API), `models3.py` (模組三~五表) |

## 技術架構

```
index3.html (前端 - 林庭緯)
    ↓ fetch() 呼叫
main.py (統一 FastAPI 後端)
    ↓
SQLite 資料庫 (la3_plantquest3.db)
    ↓ SQLAlchemy ORM
models3.py (全部資料表定義)
```

- **後端框架**: FastAPI + SQLAlchemy
- **資料庫**: SQLite (本機檔案 `la3_plantquest3.db`)
- **AI 解析**: Anthropic Claude (Tool Use 結構化輸出)
- **前端**: 純 HTML + Tailwind CSS + Mermaid.js + browser-image-compression

## 檔案結構

| 檔案 | 用途 |
| :--- | :--- |
| `main.py` | 統一 FastAPI 入口,合併模組一至五所有 API 端點 |
| `models3.py` | SQLAlchemy 資料表定義 (模組一至五全部表) |
| `database.py` | SQLAlchemy 引擎與 Session 工廠 (統一連線管理) |
| `db_client.py` | 模組一資料庫讀寫函式 (SQLite 版) |
| `dispatcher.py` | LLM 解析結果分派邏輯 |
| `llm_parser.py` | Anthropic Tool Use 結構化輸出解析 |
| `engine3.py` | 模組三~五純計算演算法 (氣象、身價、堆肥) |
| `test1.py` | 模組一離線單元測試 (mock DB 與 LLM) |
| `test3.py` | 模組三~五單元測試 |
| `index3.html` | 前端 UI (模組二 + 全系統介面) |
| `requirements.txt` | Python 依賴套件清單 |
| `.env.example` | 環境變數範本 |
| `render.yaml` | Render 部署設定 |

## 本機啟動

```bash
# 1. 建立虛擬環境
python -m venv venv

# 2. 啟用虛擬環境
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Mac / Linux:
source venv/bin/activate

# 3. 安裝套件
pip install -r requirements.txt

# 4. 設定環境變數
cp .env.example .env
# 編輯 .env 填入 ANTHROPIC_API_KEY

# 5. 啟動服務 (前後端一起,開一個網址就好)
uvicorn main:app --reload
```

啟動後打開 `http://127.0.0.1:8000` 就會看到完整前端畫面。

## 執行測試

```bash
# 模組一測試 (不需要 API 金鑰,使用 mock)
python test1.py

# 模組三~五測試
python test3.py
```

## 部署到 Render

1. 把整個專案推到 GitHub repo
2. 到 [Render](https://render.com) → New → Web Service
3. 選擇 repo,Render 會自動讀取 `render.yaml`
4. 在 Render 環境變數中設定 `ANTHROPIC_API_KEY`
5. 部署完成後分享 Render 給的網址即可
