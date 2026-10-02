# RepSafe × FIN-SHIELD

[English](README.md) | [繁體中文](README.zh-TW.md)

從賣家的可疑對話到付款線索，協助電商平台風控分析師用可回查的證據進行人工覆核。

RepSafe 保留賣家貼上對話、截圖讀字及取得回覆草稿的入口。FIN-SHIELD 是同產品內的調查模組，為具有錢包／代收付能力的平台整理交易、客戶資料、已知關聯與示範政策。主要使用者是風控分析師，潛在採購者是風控／營運主管，賣家是受保護者。工作流需求、節省時間與付費意願均待訪談驗證。

## 目前狀態

2026-10-02：已進入平行實作與整合階段；本文件提供可供設定的操作說明，上線驗證待完成。Vercel CLI 已備妥，使用者登入待完成；整合負責人正在加入 Python 3.12、`sin1` 區域的原生 FastAPI 部署設定。Vercel 公開網址待整合負責人提供驗證結果後補上。文件完成不代表部署成功、真 AI 已跑通或 G0–G3 已通過。

- 案例、KYC、政策及付款全部為 Synthetic／Simulated（合成／模擬）；沒有真實轉帳、銀行攔截、帳戶凍結或 AML 通報。
- FIN-SHIELD 預設關閉，模型呼叫上限預設為 0。公開預覽可以展示合成範本；持久化案件操作與人工覆核需要完整後端設定及相應權限。
- `offline_fixture` 是固定、附來源的離線工作流展示，不是真 Gemini、agentic AI 或 G1 通過證據。
- 真 Gemini 補查、Firestore 重啟一致性、完整安全測試與 Vercel 實測仍須依 [QA 計畫](docs/qa/test-plan.md)及 [roadmap](docs/roadmap.md)留下本版結果。
- 專案總預算上限為 USD 100；實際已用、剩餘與帳單幣別待核對，不能把總上限當作餘額。工時限制與安排見 [預算](docs/finance/budget.md)及 roadmap。

## 工作方式

1. 對話線索連到固定合成案件。每筆模擬付款都先由伺服器執行版本化規則；是否看過警示不影響檢查。
2. 命中規則的付款進入 `HOLD_PENDING_REVIEW`；完整檢查且未命中的正常案為 `SIMULATED_PASSED`；付款檢查失敗為 `CHECK_FAILED`。
3. Investigator 只能讀取同案授權的四類來源：交易、客戶／KYC、已知關聯、政策與前例。它整理支持證據、反證、缺失、政策依據與建議；有效引用應能點回來源及工具結果。
4. 授權 reviewer 以獨立操作與理由作出決策，保存案件版本及審核事件。AI、VIP 追問、Dismiss alert 與 Escalate 都不能自行解除 HOLD。

付款狀態與調查狀態分開。調查可能是 `NOT_STARTED`、`RUNNING`、`READY` 或 `INCOMPLETE`；模型或工具失敗須顯示缺失，已暫停的付款維持暫停。`SIMULATED_PASSED` 只表示本次模擬規則通過，並非「安全」或合法性的保證。

## 本機啟動

使用 Python 3.11，在專案根目錄執行。下列預設只啟動既有 RepSafe 離線功能，不需要雲端帳戶。

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
# 僅在尚無 .env 時複製，保留既有本機設定。
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
$env:AGENT_MODE='offline_fixture'
$env:URL_REPUTATION_BACKEND='fixture'
$env:FINSHIELD_ENABLED='false'
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

macOS／Linux 使用 `.venv/bin/python`；環境變數以 `export` 設定。範例設定見 [.env.example](.env.example)。

- [RepSafe 首頁](http://127.0.0.1:8000/)：保留文字／截圖上傳與本機預覽；截圖讀字後先確認內容，不作付款證明鑑偽。本機每張圖片預設上限 10MB，Vercel 原圖上限為 3MB；介面應顯示 `/api/config` 回傳的上限。
- [健康檢查](http://127.0.0.1:8000/health)：既有 `status`、`mode`、`url_reputation` 三欄，不能用來證明 FIN-SHIELD 的模型或持久化已就緒。
- [API 文件](http://127.0.0.1:8000/api/docs)：FIN-SHIELD API 前綴為 `/api/finshield`。
- [FIN-SHIELD](http://127.0.0.1:8000/finshield)：設定後才啟用；預設關閉時回 404 是預期行為。

要操作完整合成案件，請依 [部署說明](docs/engineering/deploy.md)設定來源、Firestore 與 reviewer 授權。即使模型使用離線 fixture，線上案件／覆核仍需要 Firestore。測試注入的本機 fake 不代表可部署的儲存方案；缺憑證時應顯示無法操作，不能靜默改用記憶體或 Vercel 本機 SQLite。

## 模型與環境設定

| 設定 | 用途與預設 |
|---|---|
| `FINSHIELD_ENABLED=false` | 關閉新模組；完成設定後才明確啟用 |
| `FINSHIELD_MODEL_MODE=offline_fixture` | 固定合成工作流；`gemini` 才是使用真模型的模式 |
| `FINSHIELD_LIVE_CALLS_ENABLED=false` | 不允許真模型呼叫；切換模式本身不足以開啟付費呼叫 |
| `FINSHIELD_MODEL_CALL_CAP=0` | 預設零呼叫；獲准實測時才設定有限配額 |
| `FINSHIELD_BUDGET_ID` | 配合持久化呼叫配額識別一次核准試跑；不是每日自動補額 |
| `FINSHIELD_ALLOWED_ORIGIN` | 完整且精確的部署 HTTPS origin，配合 cookie、CSRF 與 Origin 驗證 |
| `AGENT_MODE` / `URL_REPUTATION_BACKEND` | 既有 RepSafe 對話模型／網址查核設定；不會取代 FIN-SHIELD 的模型模式 |
| `MAX_IMAGE_MB` | 本機維持預設 `10`；Vercel 設為 `3`，讓 base64 JSON 編碼後的內容容納於 4.5MB 請求限制。保留上傳與預覽，介面上限以 `/api/config` 為準 |
| `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` / `GEMINI_MODEL` | 真模型所用的伺服器設定；實際可用模型與憑證依部署說明核對 |

reviewer 密鑰、Firestore 與雲端憑證僅存伺服器設定，欄位名稱以整合後的 `.env.example` 和部署說明為準。公開訪客不自動取得 reviewer；有 reviewer 身分也只可處理自己的授權案件。API 的寫入操作還須符合 session、CSRF、Origin、案件版本與冪等要求。

## 兩個合成案例的展示步驟

前置條件：開啟 `/finshield`，確認畫面上的合成／模擬及模型模式標示。未設定儲存或授權時，只展示明確標示的預覽，不能把預覽稱為已建立案件或完成覆核。以下是設定完成後的驗證劇本，並非已通過的結果。

1. 高風險案 `risk-fee`：建立新案件，查看假金流驗證對話與付款來源，再送出模擬付款。檢查規則將本筆設為 `HOLD_PENDING_REVIEW`；執行調查，點開來源並查看支持證據、反證與缺失。追問 VIP 能否放行，確認 HOLD 不變。僅授權 reviewer 可用理由明確執行 Approve held payment、Keep hold、Escalate 或 Cancel payment；檢查審核事件。Dismiss alert 只處理警示，不會放行。
2. 正常案 `normal-invoice`：建立另一筆案件，查看發票及合理商業解釋，送出模擬付款。完整規則未命中時應為 `SIMULATED_PASSED`；檢查調查保留合理反證，不把共享設備直接判為共犯。核對新案件的來源與狀態，不沿用上一案的引用或 reviewer 操作。

離線版可用來排練上述流程。只有取得真 Gemini 依前一步工具結果選擇補查的記錄，才可展示該次真 AI 能力；G1 還須通過其餘全部驗收。30 秒是剪輯／演示目標，不是實測延遲保證。

## Vercel 設定與上線驗證

狀態：可依下列步驟準備設定；Vercel 上線驗證待完成。實際入口、憑證欄位及部署結果以整合負責人的 [部署說明](docs/engineering/deploy.md)為準。歷史 Cloud Run 記錄不代表 Vercel 已上線。

1. 完成 Vercel 使用者登入後匯入 GitHub 專案，根目錄選包含 `app/` 與 `requirements.txt` 的資料夾，使用整合負責人提供的原生 FastAPI、Python 3.12、`sin1` 設定。`/` 保留舊對話功能，`/finshield` 為新頁面。
2. 分別設定 Preview 與 Production 的伺服器環境變數，先維持 `FINSHIELD_MODEL_MODE=offline_fixture`、`FINSHIELD_LIVE_CALLS_ENABLED=false`、`FINSHIELD_MODEL_CALL_CAP=0`；Vercel 設定 `MAX_IMAGE_MB=3`，本機預設仍為 10。需要的既有雲端資源及憑證由部署負責人確認，不自動升級付費方案。
3. 設定可用的 Firestore、精確 HTTPS origin 及 reviewer 密鑰後才啟用完整案件操作。不可用記憶體或 Vercel 本機 SQLite 代替線上持久化，也不可將密鑰放入前端、GitHub 或 `.env.example`。
4. 部署後驗證 `/`、`/health`、`/finshield` 及其靜態檔、截圖上傳／預覽與 `/api/config` 上限，再跑兩案、跨 session 隔離、未授權覆核、CSRF／Origin 拒絕、重送與重啟保存。缺憑證時應有明確失敗／未設定狀態。
5. 真 Gemini 試跑需另有有效憑證、核准配額及完整結果。整合負責人確認部署版本與實測紀錄後，才補公開網址及完成狀態。

## 驗證與資料

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts/run_eval.py --offline --edge
```

第一行是本機測試指令；第二行只驗既有對話的離線流程。列出指令不代表已執行或通過。對話基線、新金融案件評測、Firestore 持久化與真模型結果須分別回報；本機 fake／fixture 不能證明雲端或 agentic 能力。最新結果與缺項見 QA 文件。

公開資料只用合成案例與示範政策；示範政策不是法規。訪談原文、聯絡方式、同意書及工作流筆記只放 `data/private/`；既有經同意且打碼的賣家案例另放被忽略的 `data/real_cases/`。這些私人目錄都不得部署或公開，詳見 [訪談與資料處理](docs/sales/seller-outreach.md)。

## 文件索引

| 文件 | 用途 |
|---|---|
| [PRD](docs/prd.md) · [Roadmap](docs/roadmap.md) | 角色、範圍、狀態與 G0–G3 |
| [架構](docs/engineering/architecture.md) · [部署](docs/engineering/deploy.md) | API、儲存、權限、環境及上線證據 |
| [介面規格](docs/design/ui-spec.md) · [影片分鏡](docs/design/storyboard.md) | 英文介面、證據與模擬標示 |
| [英文講稿](docs/pitch/pitch-script.md) | 產品敘事、展示旁白與 FAQ |
| [訪談範本](docs/sales/seller-outreach.md) · [來源登錄](docs/sales/data-sources.md) | 分析師／採購／賣家驗證、主張界限 |
| [預算](docs/finance/budget.md) | USD 100 上限、成本與待核對事項 |
| [測試計畫](docs/qa/test-plan.md) · [缺陷紀錄](docs/qa/bugs.md) | 測試範圍、實測結果及待解問題 |
| [整合會議](docs/meetings/2026-10-02-FIN-SHIELD整合評估.md) · [工程計畫](docs/superpowers/plans/2026-10-02-finshield-48h-core.md) | 設計依據與歷史決策；現行執行以新版規格為準 |

RepSafe／FIN-SHIELD 均為暫定名稱。既有工具也提供調查摘要與代理能力；「對話線索接續案件證據」是待驗證差異，不是市場首創、成效或付費保證。
