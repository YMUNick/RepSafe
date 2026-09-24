# 部署紀錄（Cloud Run）

> **2026-09-24 已部署（離線模式）**：專案 `repsafe-2026`、服務 `repsafe`（`asia-southeast1`）
> 網址：https://repsafe-195979831646.asia-southeast1.run.app
> 目前是 `AGENT_MODE=offline_fixture`＋`URL_REPUTATION_BACKEND=fixture`：判定來自關鍵字規則，畫面上方有 "Offline test mode" 提示，**不能當正式 demo 或準確率依據**。Vertex AI、Web Risk 已於 9/25 開好（API、權限、模型 ID 已驗證），9/28 切成真 Gemini，網址不變（見下方「切換成真 Gemini」）。

## 目前設定

| 項目 | 值 | 理由 |
|---|---|---|
| GCP 專案 | `repsafe-2026`（與 LineSleuth 分開記帳） | Felix：獨立專案、獨立預算 |
| 區域 | `asia-southeast1`（新加坡） | 評審與決賽在新加坡 |
| 存取 | 公開（`--allow-unauthenticated`） | 評審不用登入就能開 |
| 執行個體 | `--min-instances 0 --max-instances 1` | 沒人用不收費；1 台讓記憶體內的速率限制計數有效 |
| 記憶體 | 512Mi | 截圖上傳上限 10MB |
| 環境變數 | `AGENT_MODE=offline_fixture`、`URL_REPUTATION_BACKEND=fixture`、`SCREENSHOT_ENABLED=true`、`GLOBAL_RATE_LIMIT_PER_HOUR=120`、`GOOGLE_CLOUD_PROJECT=repsafe-2026` | 離線模式，幾乎零費用 |
| 預算警示 | **100 SGD**，50％／90％／100％ 寄信（帳單帳戶幣別是 SGD，2026-09-24 老闆改以 100 SGD 設定） | 警示只寄信、不會停止扣款 |
| 建置權限 | 預設運算服務帳號 `195979831646-compute@developer.gserviceaccount.com` 已授予 `roles/run.builder` | 新專案用 `--source` 部署必須，否則建置時讀不到原始碼 |

## 重新部署

gcloud 裝在 `G:\GoogleCloud\google-cloud-sdk\bin\gcloud.cmd`（不在 PATH，PowerShell 用完整路徑呼叫）。在專案根目錄執行：

```powershell
& "G:\GoogleCloud\google-cloud-sdk\bin\gcloud.cmd" run deploy repsafe --source . --project=repsafe-2026 --region=asia-southeast1 --allow-unauthenticated --min-instances=0 --max-instances=1 --memory=512Mi --set-env-vars="AGENT_MODE=offline_fixture,URL_REPUTATION_BACKEND=fixture,SCREENSHOT_ENABLED=true,GLOBAL_RATE_LIMIT_PER_HOUR=120,GOOGLE_CLOUD_PROJECT=repsafe-2026" --quiet
```

部署後檢查：`/health` 回 200、`/api/config` 的 `mode` 是預期值、首頁能開、貼一則詐騙訊息出紅卡。

## 切換成真 Gemini（9/28 切換）

> 2026-09-25 Eddie 已先做完前 3 步（準備工作）；**線上服務仍是離線模式**，9/28 才做第 4 步。

- [x] 1. 啟用 API：`aiplatform.googleapis.com`、`webrisk.googleapis.com`（9/25 已啟用）。
- [x] 2. 服務帳號權限（`195979831646-compute@developer.gserviceaccount.com`）：
  - Vertex AI：已授予 `roles/aiplatform.user`（專案層級）。
  - Web Risk：`roles/webrisk.user` 在這個專案**不存在、無法授予**（`INVALID_ARGUMENT: Role roles/webrisk.user is not supported`），可授予的角色清單裡也沒有任何 Web Risk 角色。Web Risk 只要求 API 已在專案啟用；這個帳號本來就有 `roles/editor`，不需要再加角色。9/29 Quinn 做「拿掉權限」測試時，拿掉的是 `roles/aiplatform.user`（或暫停 webrisk API），不是 webrisk 角色。
- [x] 3. 模型 ID 已實測：**`GEMINI_MODEL=gemini-3-flash-preview`、`GOOGLE_CLOUD_LOCATION=global`**（和 `.env.example`、程式預設值相同，所以第 4 步其實不用帶 `GEMINI_MODEL`，寫上是為了明確）。9/25 用 gcloud access token 對 `.../locations/global/publishers/google/models/gemini-3-flash-preview:generateContent` 送 "ping"：HTTP 200、`modelVersion=gemini-3-flash-preview`、`trafficType=ON_DEMAND`。注意：輸入 1 token，**思考 token 就用了 13**（上限設 16 所以沒產生文字）。這個模型預設會思考，會增加延遲與費用；9/28 量 token 時要看 log 的 `thinking_tokens`，交給 Felix。
- [x] Web Risk 實測：`uris:search` 查 `http://testsafebrowsing.appspot.com/s/phishing.html` 回 `{"threat": {"threatTypes": ["SOCIAL_ENGINEERING"], ...}}`，格式和 `app/tools/url_reputation.py` 一致；用本機 ADC 跑 `WebRiskReputation.check()` 得到 `status='match', threats=('SOCIAL_ENGINEERING',)`。本機 ADC 要設 `GOOGLE_CLOUD_QUOTA_PROJECT=repsafe-2026`（或 curl 帶 `x-goog-user-project: repsafe-2026`），Cloud Run 上不用。
- [ ] 4. 只改環境變數，網址不變（**9/28**）：
   ```powershell
   & "G:\GoogleCloud\google-cloud-sdk\bin\gcloud.cmd" run services update repsafe --project=repsafe-2026 --region=asia-southeast1 --update-env-vars="AGENT_MODE=gemini,URL_REPUTATION_BACKEND=webrisk,GEMINI_MODEL=gemini-3-flash-preview,GOOGLE_CLOUD_LOCATION=global"
   ```
   切換後看 Cloud Run log 有兩行 `warm_up`（`gemini`、`url_reputation` 都是 `ready`），代表啟動時已建好 client（BUG-008）。
- [ ] 5. 在 Vertex AI 設每日配額上限（Felix 的四道防線之一），再跑 `python scripts/run_eval.py --url https://repsafe-195979831646.asia-southeast1.run.app --repeat 2` 量準確率與熱機延遲。

## 已知限制

- `--min-instances 0`：閒置後第一個請求會冷啟動（離線模式實測首頁約 0.4 秒；真 Gemini 模式待量）。錄影或評審前先開一次 `/health` 暖機。真 Gemini 模式下，容器啟動後會在背景執行緒建好 Gemini 和 Web Risk client（BUG-008，`app/main.py` `warm_up()`，不呼叫模型、不花錢），不擋啟動，首頁和 `/health` 立即回應。本機實測 Web Risk client 初始化約 17 秒、Gemini 約 2 秒；warm-up 完成前送出的第一則分析會等 client 建好（加鎖，只建一次），仍可能較慢或灰卡。注意 Cloud Run 預設只在處理請求時給 CPU，背景 warm-up 在無請求期間可能被降速，所以錄影前仍要「`/health` ＋ 一則假訊息 `/api/analyze`」，並看 log 兩行 `warm_up` 都是 `ready` 再開始（Cloud Run 上實際秒數待 9/29 量）。
- 速率限制計數存在記憶體，實例關閉或重新部署會歸零；硬上限靠 GCP 配額與預算警示。
