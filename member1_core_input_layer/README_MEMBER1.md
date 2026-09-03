# 模組一：核心輸入層 (梁偉航)

## 檔案說明

| 檔案 | 用途 |
| --- | --- |
| `db_client.py` | 所有 Supabase 讀寫集中管理,其他人串接時應複用而非各自寫連線 |
| `llm_parser.py` | 用 Anthropic Tool Use 強制結構化輸出解析一句話,含失敗重試 |
| `dispatcher.py` | 把解析出的事件分派寫入對應資料表,單一事件失敗不擋其他事件 |
| `main1.py` | FastAPI 入口,提供 `/api/dictation/parse`、`/api/photos` 等端點 |
| `test1.py` | 離線單元測試(mock 掉 DB 與 LLM),5 個測試全過 |
| `sql/01_schema_fixes.sql` | 修正先前 Schema 審查發現的 3 個問題(需先在 Supabase 執行) |

## 本機測試方式

```bash
pip install -r requirements.txt --break-system-packages
python3 test1.py                    # 離線測試,不需要任何金鑰
cp .env.example .env                # 填入真的 SUPABASE_URL / SERVICE_KEY / ANTHROPIC_API_KEY
uvicorn main1:app --reload          # 啟動後打 http://127.0.0.1:8000/docs 測試
```

## 語音輸入的實作方式

沒有在後端處理音訊。前端用瀏覽器 Web Speech API(或手機鍵盤自帶語音輸入,
這是主要路徑)把語音轉成文字後,一樣打 `POST /api/dictation/parse`,
差別只在 `source` 欄位傳 `"voice"` 而不是 `"manual"`。這樣可以避開
iOS Safari 對 Web Speech API 支援度不一致的問題 —— 不支援就自動降級成
純文字輸入框,體驗一致。

## 待辦(依賴其他人)

- `dispatcher.py` 目前只處理 `plants / tools / containers / supplies / harvests / transactions`
  這幾張表。等庭緯的族譜、相簿前端串接進來後,`plant_purchase` 事件裡
  的 `mother_id` / `father_id` 需要再擴充解析欄位。
