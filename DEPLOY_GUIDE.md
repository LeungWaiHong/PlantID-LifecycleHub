# PlantQuest Hub - 部署指南

## 架構說明

本系統使用 SQLite 作為資料庫 (本機檔案 `la3_plantquest3.db`),所有模組共用同一個資料庫。
前後端整合在同一個 FastAPI 服務中,前端 `index3.html` 由後端一併服務,前後端同源。

### 資料流

```
index3.html (前端)
    ↓ fetch() 呼叫同源 API
main.py (FastAPI 統一入口)
    ├── 模組一: /api/dictation/*, /api/photos (AI 語音/文字記帳)
    ├── 模組三: /api/weather/*, /api/travel/* (氣象與出差排程)
    ├── 模組四: /api/market/*, /api/pricing/*, /api/inventory/* (資材產銷)
    └── 模組五: /api/compost/*, /api/fertilizer/* (堆肥與液肥)
    ↓
SQLite (la3_plantquest3.db) via SQLAlchemy ORM
```

### 模組一 (AI 園藝管家) 的運作方式

使用者在前端輸入一句話 (手動打字或手機語音轉文字),前端把文字送到
`POST /api/dictation/parse`,後端呼叫 Anthropic Claude 用 Tool Use 結構化輸出
解析為事件清單,再透過 dispatcher 分派寫入 SQLite 各對應表。

語音輸入不在後端處理音訊,而是由瀏覽器 Web Speech API 或手機鍵盤自帶語音輸入
轉成文字後送出,避開瀏覽器相容性問題。

## 本機啟動

```bash
python -m venv venv

# Windows
.\venv\Scripts\Activate.ps1
# Mac / Linux
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# 編輯 .env 填入 ANTHROPIC_API_KEY

uvicorn main:app --reload
```

打開 `http://127.0.0.1:8000` 即可看到完整前端畫面。

## 部署到 Render

1. 推到 GitHub repo
2. 到 Render → New → Web Service → 選擇 repo
3. Render 會自動讀取 `render.yaml`:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. 在 Render 環境變數中設定 `ANTHROPIC_API_KEY`
5. 部署完成後分享網址

### Render 免費方案限制

- SQLite 檔案不保證長期保存,重新部署可能重置資料庫
- 植物身分證/族譜/採收/庫存/堆肥等資料存在瀏覽器 localStorage,每個使用者看到的是自己瀏覽器的資料
- 花市採買、盆器流轉、堆肥計算、液肥日誌、天氣、出差清單會存入 SQLite

## 執行測試

```bash
# 模組一 (離線,不需 API 金鑰)
python test1.py

# 模組三~五
python test3.py
```
