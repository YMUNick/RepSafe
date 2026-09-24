# 部署紀錄（Cloud Run）

> **2026-09-24 已部署（離線模式）**：專案 `repsafe-2026`、服務 `repsafe`（`asia-southeast1`）
> 網址：https://repsafe-195979831646.asia-southeast1.run.app
> 目前是 `AGENT_MODE=offline_fixture`＋`URL_REPUTATION_BACKEND=fixture`：判定來自關鍵字規則，畫面上方有 "Offline test mode" 提示，**不能當正式 demo 或準確率依據**。9/26 開好 Vertex AI、Web Risk 後切成真 Gemini，網址不變（見下方「切換成真 Gemini」）。

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

## 切換成真 Gemini（9/26 之後）

1. 啟用 API：`aiplatform.googleapis.com`、`webrisk.googleapis.com`。
2. 讓 Cloud Run 的服務帳號能呼叫 Vertex AI（`roles/aiplatform.user`）與 Web Risk（`roles/webrisk.user`）。
3. 在 Vertex AI Model Garden 確認目前的 Flash 模型 ID，填進 `GEMINI_MODEL`。
4. 只改環境變數，網址不變：
   ```powershell
   & "G:\GoogleCloud\google-cloud-sdk\bin\gcloud.cmd" run services update repsafe --project=repsafe-2026 --region=asia-southeast1 --update-env-vars="AGENT_MODE=gemini,URL_REPUTATION_BACKEND=webrisk,GEMINI_MODEL=<確認後的模型 ID>"
   ```
5. 在 Vertex AI 設每日配額上限（Felix 的四道防線之一），再跑 `python scripts/run_eval.py --url https://repsafe-195979831646.asia-southeast1.run.app --repeat 3` 量準確率與熱機延遲。

## 已知限制

- `--min-instances 0`：閒置後第一個請求會冷啟動（離線模式實測首頁約 0.4 秒；真 Gemini 模式待量）。錄影或評審前先開一次 `/health` 暖機。
- 速率限制計數存在記憶體，實例關閉或重新部署會歸零；硬上限靠 GCP 配額與預算警示。
