# PlantQuest Hub（建豪模組）— 從零部署指南

這份是看完建豪交的 `PlantQuest_MemberC_Final.zip` 之後，實際跑過程式碼、
修掉兩個會讓它「在別人的電腦上打不開」的問題後，整理出來的完整部署步驟。

## 先講重要的：這包東西的真實架構，跟我之前規劃的不一樣

我原本規劃的是 Next.js + Supabase（雲端資料庫，所有人共用同一份資料，
我上次已經實際建好 Supabase 專案）。但打開這個 zip 之後發現，庭緯和建豪
實際做出來的是**完全獨立的另一套架構**：

```
index3.html（庭緯的前端，純 HTML+JS，沒有用 Next.js）
    ↓ fetch() 呼叫
main3.py（建豪的 FastAPI 後端）
    ↓
SQLite 本機資料庫檔案（la3_plantquest3.db）
```

而且更關鍵的是，**不是所有資料都走後端**。打開 index3.html 的原始碼會
看到：

- **植物身分證、族譜、採收記錄、耗材庫存、堆肥批次** → 存在瀏覽器的
  `localStorage`，根本沒送到後端，也沒進 SQLite。
- **花市購買記錄、盆器在役/庫存切換、堆肥計算存檔、液肥日誌、天氣、
  出差清單** → 這些才是真的打 `main3.py` 的 API，存進 SQLite。

這代表什麼：**現在這個工具是「單一瀏覽器 = 單一份資料」**。同一個人
換一台電腦、換一個瀏覽器，或不小心清瀏覽器快取，植物身分證跟族譜資料
就會不見（這就是為什麼建豪的 README 特別提到「系統備份與還原」——
JSON 匯出/匯入是他們拿來補這個洞的方式，不是真的解決，是繞過）。

我之前做的 Supabase 資料庫、AI 語音記帳（模組一）目前完全沒有接進
這個系統——這包東西裡面完全沒有語音輸入或 AI 解析的程式碼。

**這不是誰做錯了**，比較像是三人在時間壓力下各自選了當下最快能動的做法：
我規劃雲端多人共用架構，庭緯/建豪則做了一個能獨立在單一瀏覽器跑起來的
本機 Demo。這兩條路都合理，只是現在需要決定要用哪一條走到最後。

## 我先幫你把「能不能給別人用」這件事修好了

打開程式碼後發現兩個問題，會讓別人根本無法啟動這個工具，我已經修好：

1. **`requirements.txt` 編碼錯誤**：這個檔案是 Windows PowerShell
   用 `pip freeze > requirements.txt` 產生的，預設編碼是 UTF-16，
   在 Windows 以外的環境（Mac、Linux、雲端主機）`pip install` 會直接
   讀不懂整個檔案報錯。已轉成標準 UTF-8。
2. **前端寫死 `http://127.0.0.1:8000`**：`index3.html` 裡 API 網址
   寫死指向本機，只有在「前端跟後端開在同一台電腦」才會動，別人打開
   你分享的網址會整個空白、什麼都載入不出來。已經改成自動抓目前網域
   （`window.location.origin`），並且讓後端順便把前端也服務出去，
   兩者變成同一個網域，這樣不管本機測試還是部署到雲端都不用再手動改。

修好的完整檔案在下面會附給你，`requirements.txt` / `main3.py` /
`index3.html` 這三個有改動，其他檔案原封不動。

⚠️ 這個環境沒有對外網路權限，我沒辦法實際 `pip install` 跑一次驗證
（試了會直接連不到 PyPI），只做了 Python 語法檢查（`py_compile` 全過）
跟人工比對程式碼邏輯。麻煩你或建豪在自己電腦上實際跑一次「本機啟動」
那段確認沒問題。

## 給別人用，你有兩條路可以選

### 路線 A：先求能展示，最快上線（建議：如果快到期限了）

把 `main3.py` + `models3.py` + `engine3.py` + `index3.html` +
`requirements.txt` 這五個檔案部署到 Render（免費方案），變成一個
所有人都能打開的網址。

**步驟：**

1. 把這個資料夾（`plantquest-member-c-deploy`）推到一個新的 GitHub repo
2. 到 [Render](https://render.com) 用 GitHub 帳號登入 → New → Web Service
3. 選你剛推上去的 repo，Render 會自動讀到附上的 `render.yaml`：
   - Build Command：`pip install -r requirements.txt`
   - Start Command：`uvicorn main3:app --host 0.0.0.0 --port $PORT`
4. 部署完成後，Render 會給你一個網址，例如
   `https://plantquest-member-c.onrender.com`，直接分享這個網址，
   別人打開就是完整的工具畫面（因為前端已經改成後端順便服務）。

**這條路的限制，要跟大家講清楚：**
- 免費方案的 SQLite 檔案**不保證長期保存**——Render 免費 Web Service
  沒有掛載持久化磁碟，重新部署（例如你們之後又 push 新程式碼）很可能
  把 `la3_plantquest3.db` 重置成空的。展示前一天再重新輸入一次測試資料，
  或展示當天別重新部署，就不會有問題；但不要拿它存長期真實資料。
- 植物身分證/族譜/採收/庫存/堆肥資料還是 `localStorage`——**每個人
  打開這個網址，看到的都是自己瀏覽器裡的空白初始狀態**，不會是你
  自己輸入過的資料。如果是要「給老師/評審看你已經輸入好的成果」，
  你要用**自己的瀏覽器**打開這個網址展示，不能請別人用他們的電腦打開
  期待看到你的資料。

### 路線 B：真的接回我做的雲端資料庫（建議：如果你們還有時間）

把植物/族譜/採收/庫存/堆肥這幾塊資料，從 `localStorage` 改成呼叫
Supabase（我上次已經建好、有 13 張表的那個資料庫），這樣資料才是
「不管誰用哪台裝置打開都看到同一份」，也才能真的把我的 AI 語音記帳
接進去（模組一目前完全沒接，這個工具現在打不了字就自動記帳）。

這條路工作量不小，主要是：
1. 把 `index3.html` 裡讀寫 `localStorage` 的地方，改成 fetch 我的
   Supabase REST API（或者透過我之前寫的 Next.js API Route）
2. `engine3.py` 裡的純計算函式（C:N 比值、身價估算、補水清單）不用動，
   邏輯是對的，只是最後「存資料」的地方要換成 Supabase
3. 把 `main3.py` 的 SQLite 相關表（`market_purchases3` 等）對應到我
   `schema.sql` 裡已經建好的 `market_stalls` / `transactions` /
   `compost_batches` 等表

這個如果要走，建議三人開個會對一下，不是我能自己默默改掉建豪的後端。

## 本機啟動（給建豪或任何人在自己電腦測試用，已修成跨平台可用）

```bash
# 1. 建立虛擬環境
python -m venv venv

# 2. 啟用虛擬環境
# Windows PowerShell：
.\venv\Scripts\Activate.ps1
# Mac / Linux：
source venv/bin/activate

# 3. 安裝套件（現在編碼已修好，任何系統都能裝）
pip install -r requirements.txt

# 4. 啟動服務（前後端一起，開一個網址就好）
uvicorn main3:app --reload
```

啟動後打開 `http://127.0.0.1:8000` 就會看到完整前端畫面，不用再另外
用瀏覽器開 `index3.html` 那個檔案了。

## 這次順便修掉、但不影響任何功能的小地方

- `.env.example` 裡的氣象 API 設定（`OPEN_METEO_BASE_URL` 等）目前
  `engine3.py` 並沒有真的讀取這幾個環境變數，是直接寫死在函式裡。
  功能上沒問題（反正值一樣），但如果之後要換氣象供應商或改預設座標，
  記得要改的是 `engine3.py` 裡面，不是改 `.env`，這點先跟建豪說一聲，
  免得他以為改 `.env` 就會生效。
