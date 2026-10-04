# RepSafe × FIN-SHIELD 架構

- 更新：2026-10-02，Paula（PM，本次架構文件責任）；保留 Eddie 的原對話模組設計基線。
- 依據：[PRD](../prd.md)、[roadmap](../roadmap.md)、[48h 核心工程計畫](../superpowers/plans/2026-10-02-finshield-48h-core.md)與本次平行實作契約。
- 已授權六角色平行實作、GitHub 中英文件及 Vercel 部署；Controller 負責整合、發布與最終驗證。本文件描述目標契約與可核對的原模組，不宣告新功能、真 Gemini、Firestore 重啟或部署已通過。
- 原會議／工程計畫的「僅規劃」及順序執行限制屬歷史授權；本次分工以 roadmap 為準。Paula 不改程式、他人檔案或部署設定。

## English summary

RepSafe keeps its existing stateless conversation and screenshot checks. FIN-SHIELD adds case-scoped synthetic evidence, deterministic payment rules, a bounded investigator and separately authorized human review. The backend remains portable FastAPI, with Vercel as the current deployment target and Firestore as the required durable online store. The original Cloud Run deployment is historical context, not a restriction on the new target.

Session cookies, exact Origin checks, CSRF protection and server-side case grants protect writes. Public case responses expose evidence and review permission, never session/token/key hashes or internal operations. The investigator has four read-only tools and cannot change payment state. Offline fixtures must be labelled deterministic demonstrations; they are not real agentic AI and do not satisfy G1. The feature is disabled by default and the model-call cap is zero.

The integrated synthetic workflow is deployed on Vercel with real Firestore, keyless production-scoped federation, and 255 passing tests. See the [deployment evidence](deploy.md) for the exact revision, hosted checks and remaining gaps; this is not live Gemini or full G1 acceptance. Missing credentials or storage fail closed; a labelled preview cannot claim persisted actions. USD 100 and the historical 25-hour total cap remain constraints with actual usage unresolved.

## 1. 部署拓撲與責任

```text
瀏覽器
  ├─ /                         原 RepSafe 對話／截圖確認
  └─ /finshield                FIN-SHIELD 合成案件／來源／覆核
             │ 同源 HTTP；cookie + Origin + CSRF
             ▼
可攜 FastAPI（app/main.py；本次目標 Vercel）
  ├─ /api/analyze、/api/extract-text、/api/config、/health
  └─ /api/finshield/*
       ├─ session / reviewer grant ─┐
       ├─ 付款規則 / 人工 review ──┼─ Firestore 原子狀態／audit／冪等
       └─ Investigator ────────────┘  lease／呼叫配額
            ├─ offline_fixture：固定合成示範
            └─ gemini：有限 structured-action 迴圈
                 └─ 四個案件範圍 READ 工具 → 已回傳 evidence → 引用驗證
```

前端靜態檔仍由後端提供 `/finshield`、`/finshield.js`、`/finshield.css`；UI/API 採同源部署。Controller 核對 Vercel 的實際路由、執行時間／檔案限制與雲端憑證，將實測寫入部署記錄；不能把可攜設計當成平台已相容的證據，亦未授權升級付費方案。

Firestore 是線上案件及 reviewer session 的必要持久層。記憶體 fake 只供明確本機開發／測試，emulator 只供明確本機驗證；Vercel 不得以本地 SQLite 或記憶體靜默代替 Firestore。缺 credentials、database 或權限時，受保護 API 回失敗並由 UI 明示 unavailable，不能假造建立／覆核／調查成功。

公開未登入頁可顯示固定 Synthetic／Simulated 模板及預覽；preview 不是已落庫案件，也不是 reviewer。持久化流程與人工覆核須滿足後述 session／同案授權條件。

## 2. 原 RepSafe 模組保留

以下為原模組設計與此次讀取程式可核對的邊界；原始 69／98 項歷史測試數不作 FIN-SHIELD 驗收證據。

| 檔案／入口 | 原責任與保留行為 |
|---|---|
| `app/main.py` | 保留 `/`、`/api/analyze`、`/api/config`、條件式 `/api/extract-text`；既有 `/health` 精確三欄 `{status, mode, url_reputation}`。模組旗標放 `/api/config` 的 `finshield_enabled`，不擴張 health |
| `app/config.py` | 原 `AGENT_MODE`、網址後端、截圖及輸入限制；不以原 chat mode 推定新模組 mode |
| `app/analyze.py` | 強制執行工具與注入防護、驗證 Gemini 結構化輸出、請求上限、只記 metadata |
| `app/tools/domain_check.py` | 純程式網域／punycode／同形字／冒用判斷；短網址不展開 |
| `app/tools/url_reputation.py` | Web Risk 或 fixture 介面；只查 URL 聲譽，不提供銀行帳戶或 KYC 判斷，不打開可疑網站 |
| `app/gemini.py`、`app/prompt.py` | 原對話判斷／截圖 JSON schema；新增 investigator adapter 須保留原呼叫相容。評測樣本不得充當 prompt 範例 |
| `app/verdict.py` | 只決定原對話卡 red／grey／amber；FIN-SHIELD 付款另由其規則／service 決定 |
| `app/reply_filter.py` | 程式再次過濾網址、帳號、email、電話／長數字；不只依賴 prompt |
| `app/offline_fixture.py`、`app/screenshot.py` | 保留離線標記、安全回覆範本與截圖讀字確認流程 |

原對話是 tool-augmented Gemini：程式強制執行網域／URL 工具，不宣稱模型自主選工具。新 FIN-SHIELD 的真 AI 補查是獨立流程，不能用原模組的步驟標籤充當其完成證據。

原判定優先序：有任何可驗紅旗 → red；沒有紅旗但模型／工具／配額等未完成 → grey；全部完成且無紅旗 → amber，仍提示不代表安全。Gemini 紅旗引用須能在原訊息中定位；驗證不符不得當有效紅旗。此處不更改原判定行為或 PRD 第 9 節的 33 則對話評測契約。

截圖仍預設開啟，由 `SCREENSHOT_ENABLED` 控制；關閉時原讀字路由為 404。PNG／JPEG／WebP／HEIC／HEIF、10MB 限制沿原契約；先讀字、顯示預覽與文字供使用者確認，再送分析。原圖片／一般私訊不因加入新模組而自動保存，也不宣稱截圖鑑偽。

## 3. FIN-SHIELD 資料與四個工具

新增後端位於 `app/finshield/**`，包含具名資料模型、固定資料、規則、store、service、auth、tools、citations、investigator、settings 與 routes；程式由 Eddie 負責，UI 由 Dana 負責，獨立驗收由 Quinn 負責。

兩個模板為 `risk-fee`／`normal-invoice`，資料版本 `fs-demo-v1`，政策 `DEMO-PAYMENT` v1，皆為合成示範。合成交易使用 SGD 不代表專案預算幣別；專案總預算仍為 USD 100。固定資料複製為每個 session 自有的 case bundle，重綁 case／transaction／source IDs；換版不能令舊案件引用失效，不能讓不同訪客共改同一案件。

| 工具名 | 允許的讀取範圍 |
|---|---|
| `transactions` | 本案當前模擬付款、歷史 settled 交易與程式計算指標 |
| `profile_kyc` | 同案固定合成客戶欄位／片段；缺少則回缺證，不推測身分 |
| `known_relationships` | 有來源與時間的已知帳戶／設備連結；共享設備不等於共犯 |
| `policy_case_history` | 指定版本政策及本案明確允許的合成前例；不是任意查其他案件 |

工具只接受白名單工具名與 record ID，不接受任意 URL、路徑、SQL 或跨案 scope。後端同時驗事件時間及 recorded_at，排除 as_of 之後資料；金額採整數 minor units，current 與歷史分開，按唯一交易 ID 計算，不由 LLM 加總。

引用包含 case／source／record／field／quote／dataset_version／policy_version／call_index，須對得上實際已回傳 evidence；fact_key／fact_value 亦需相符。不存在、跨案、未讀、錯版或錯片段一律拒收，合法 ID 不代表自然語言主張必然正確，語意另以測試及人工核對。

## 4. 付款與調查分離

| 付款起點／事件 | 付款結果 |
|---|---|
| 新案／待檢查 | `PENDING_CHECK`；每筆付款入口均須執行伺服器規則 |
| 完整規則命中 | `HOLD_PENDING_REVIEW` |
| 完整規則未命中 | `SIMULATED_PASSED`，不是安全保證 |
| 必要輸入／policy 缺失或規則失敗 | `CHECK_FAILED`；不可用人工 approve 繞過必要檢查 |
| HOLD + 有效 reviewer `approve` | `SIMULATED_PASSED` |
| HOLD + 有效 reviewer `cancel` | `SIMULATED_CANCELLED` |
| `keep_hold`／`escalate`／`dismiss` | 不解除 HOLD；dismiss 只處理警示記錄 |

調查狀態只使用 `NOT_STARTED`、`RUNNING`、`READY`、`INCOMPLETE`。缺 KYC／工具逾時／無效引用／模型失敗或中斷使調查 INCOMPLETE，不改付款狀態；已依完整規則通過者亦不因此被說成犯罪。HOLD 是暫停本筆模擬付款，不是凍結帳戶或犯罪認定。

LLM 只有四個 READ 工具，不持有付款或 review 寫入介面；VIP 追問、自然語言 approve、prompt injection 均不能改付款。人工操作必須使用獨立 ReviewCommand、有理由、版本與冪等鍵並留下審核。

## 5. Session、覆核授權與公開回應

- Session cookie `fs_session` 採 HttpOnly、Secure、SameSite=Strict、Path=/；服務端只保存 token hash，session 有效期 24h。知道 session ID 或 case ID 不代表有權讀寫。
- Session bootstrap 驗精確 Origin；後續寫入還驗 cookie、JSON Content-Type、`X-CSRF-Token`。不開任意 CORS。HTTP 例外僅限明確的 loopback＋emulator 開發設定。2026-10-04：有效 cookie 重用原 session，不輪替 cookie、不延長24h期限；CSRF 由已驗證的高熵 cookie 加 domain separator 雜湊導出，亦接受原先保存的 CSRF hash 以相容已開啟的分頁。
- Reviewer secret 由操作者另行持有；伺服器核對 hash，再對此 session 已擁有的此案發 15 分鐘 grant。無公開預設 reviewer／secret，grant 不自動涵蓋以後的新案，每次 decision 重讀授權與版本。
- UI 的 `permissions.can_review` 是伺服器回傳的顯示資訊，不是可自行提交的授權憑證。不能信任 body 中的 role／actor，未知欄位拒絕。
- 登入失敗每 session 上限 5 次；secret 不放 URL、靜態檔、localStorage 或 logs。登入後清除表單秘密，422 等錯誤不得回顯 secret。未配置的 reviewer 回503 `reviewer_unavailable`，不消耗密碼失敗次數；仍先驗 session、CSRF及同案存取權。
- 公開 CaseRecord 必含 `case_id`、`version`、`payment_status`、`investigation_status`、`bundle`、`rule_result`、`result`、`events`，以及 `permissions.can_review`、`mode`；不含 session 資訊、token／key hashes、`operations`。
- Findings 巢狀於 `result.report`。來源用 `bundle.sources` 及 `result.trace` 的實際 evidence 定位，前端不猜未回傳片段；無效模型輸出不得直接渲染。工具 trace 不是模型內部推理。

## 6. HTTP 整合契約

全部新 API 使用前綴 `/api/finshield`。下表依工程計畫，公共 CaseRecord 的安全投影及模式欄位依本次執行契約補充；後端／前端有差異須由 Controller 核對實際版本，不能默默更改文件中的狀態或授權要求。

| Method + 相對路徑 | Request → response |
|---|---|
| POST `/sessions` | `{resume_only?: boolean}` → `{csrf_token, cases: [{case_id, template_id}], reviewer_available}`；有效 cookie 只恢復 session，不再設 cookie。無效／到期 cookie 且 resume_only=true 回401，不建立 session／扣配額；預設false才可建立新session。始終驗精確Origin |
| POST `/cases` | `{template_id: 'risk-fee' \| 'normal-invoice'}` + Idempotency-Key → public CaseRecord |
| GET `/cases/{id}` | 驗證 ownership → public CaseRecord；可回復已過期調查 lease |
| POST `/cases/{id}/payment` | `{}` + Idempotency-Key → public CaseRecord，含已落庫規則結果 |
| POST `/cases/{id}/investigation` | `{}` + Idempotency-Key → RunResult；同請求內等完成，UI 可再 GET 案件取得最新公開快照 |
| POST `/review-login` | `{case_id, reviewer_id, secret}` → 204；由 server 授權此 session 的此案 |
| POST `/cases/{id}/review` | ReviewCommand + Idempotency-Key → public CaseRecord |
| POST `/cases/{id}/vip` | `{}` + Idempotency-Key → `{answer}`；一次固定追問，付款狀態不變 |
| GET `/cases/{id}/report` | ownership 驗證 → JSON 案件報告及可定位來源；未完成照實列缺項 |

ReviewCommand 為 `action`（approve／cancel／keep_hold／escalate／dismiss）、`reason`（trim 後 1–500 字元）、`expected_version`（≥0）、`evidence_refs`。可空引用，但理由須說明人工查核／缺證；不能在此 body 覆寫 actor、scope 或政策版本。

冪等鍵長度 8–64、英數／連字號；同 key 同內容回原結果，同 key 異內容／版本衝突拒絕。調查重送且仍 RUNNING 回 409 `investigation_running`，由 GET 查詢；不重啟調查以規避上限。無 cookie 401、無 grant 403、跨案 404、偽造額外欄位 422，Origin／CSRF 不符 403；storage unavailable 回 503。ServiceError 統一 `{"error":{"code":"..."}}`，不帶密鑰或原始來源。

## 7. Firestore 原子性與故障處理

Firestore 保存 session、完整 bundle、案件版本／雙狀態、規則結果、報告、audit、冪等回應、run lease 與共享呼叫配額。Session／case 關係在建案時同一 transaction 寫入；付款／review 的授權、expected_version、狀態變更、audit 及冪等結果同一原子操作處理。LLM 呼叫不能放入可能重跑的 transaction callback。

Firestore 讀取 timeout 3s、retry=None，transaction max_attempts=3；這些是工程計畫邊界，不保證固定端到端耗時。提交 timeout 若結果不確定，以原 key 查回，不換 key 猜測重送。儲存失敗不得 fallback 成功、刪 audit 或重新建案來繞過限制。

每案 operations 最多 32、audit 最多 64，JSON document 最多 256 KiB；超限回 409 `case_capacity_reached`。儲存的冪等 response 不再包含 operations 本身，避免遞迴；對外公開投影完全移除 operations。

2026-10-04：回應快照使用版本化壓縮格式，解壓上限256KiB；旧未壓縮快照仍可精確重播，寫入時可逐步轉換而不丟失事件／hash。HOLD案件在一般操作中保留最終approve/cancel所需operation、audit與bytes容量；不可藉由重複keep_hold或no-op付款消耗最後的解決空間。硬上限不提高，session建立配額也不每日重置。`permissions.reviewer_available`僅是配置可用性，`can_review`才表示目前同案grant，兩者都不是客戶端可提交的授權。

調查使用獨立 HTTP request，在 request 存活期間等待完成；不用 response 後的 memory BackgroundTasks。持久化 lease 過期後於下次存取恢復為 INCOMPLETE，保留 HOLD／audit；晚到模型結果須核對 run_id，不能覆寫新狀態。原對話 warmup 設計不因本模組任意重寫。

記憶體測試不能證明重啟耐久。驗收需獨立 write／read 程序、同一 run-id 與明確 emulator 或 Firestore backend，重查 HOLD／decision／RUNNING 恢復及原冪等請求。Emulator 通過也不能當作真雲端通過。

## 8. 模式、呼叫上限與部署設定邊界

| 設定／邊界 | 契約 |
|---|---|
| `FINSHIELD_ENABLED=false` | 預設關閉；新頁／資產／API 為 404，不因未啟用模組建立 Firestore client |
| `FINSHIELD_MODEL_MODE=offline_fixture\|gemini` | 新模組獨立選擇；與 `AGENT_MODE` 分開，不靜默從真模型降階成 fixture |
| `FINSHIELD_LIVE_CALLS_ENABLED=false`、`FINSHIELD_MODEL_CALL_CAP=0` | 預設禁止真模型呼叫；選 gemini 也不解除預算／授權界限 |
| budget_id／配額 | 真呼叫前由 durable transaction 扣核准額度，跨 session／instance 共用，失敗不退額、不每天自動補額；cap=0／缺 budget_id／耗盡拒絕 |
| 主調查 | 每案僅一次；最多 5 次 model call、4 次 tool call；單模型 9s、tool 1s、總 deadline 45s、lease 60s |
| 輸入／輸出 | retry=0、單次輸出最多 2048 tokens；輸入 JSON ≤32 KiB、每次工具輸出 ≤8 KiB／20 records |
| VIP | 最多再 1 次 model call／9s，不開新工具；先 durable claim，失敗 unavailable，不再扣額重試 |

Offline investigator 產生可回查證據的固定合成流程，必須顯示 `offline_fixture` 及非真 AI 標記；READY 僅表示該示範流程完成，不能計為 AC-03／G1 真 agentic 成果。Gemini 驗收須記錄前次工具結果導致的下一次查詢、模型／mode／耗時與用量；四工具固定全跑或播放 fixture 都不算。

Vercel 上的實際 request 限制須容納上述 bounded loop；若無法滿足，Controller 應回報不相容及未完成項，不延長隱性工作、不削掉驗收或自行升級方案。憑證與 reviewer hashes 只由伺服器環境提供，不能把 Cloud Run 服務帳號自動存在的假設套用到 Vercel。

原對話環境仍使用 `AGENT_MODE`／`URL_REPUTATION_BACKEND`，Cloud Run 的原部署及成本限制見 [部署文件](deploy.md)。原記憶體 rate limiter 為每實例計數，不能當作跨 Vercel instance 的成本硬上限。原 10 秒對話延遲目標與新調查 45 秒 deadline 分開量測；兩者均非本文件宣告實測達標。

## 9. 隱私、驗收與交接

一般對話／截圖不自動入庫，服務 log 僅含必要 metadata／錯誤 code；不記原私訊、KYC、cookie、token、reviewer secret 或原始模型輸出。FIN-SHIELD 持久化的是明標合成的 case bundle、引用與 audit，仍受 session scope 保護。前端呈現來源用文字而非執行內嵌 HTML。

真實案例及密鑰不進公開 repo／影片；沿用 `data/real_cases/`、`data/private/` 的私有資料邊界及忽略設定，不複製私人 .env。安全回覆仍可能濾掉日期／長數字，這是原模組已知取捨，不是新調查引用欄位的規則。

| 驗證層 | 必須保留的證據／限制 |
|---|---|
| 原對話回歸 | 首頁、截圖預覽／讀字確認、判定與安全回覆、精確三欄 health；不以此代替新模組測試 |
| 離線新契約 | 兩案規則、狀態／權限、Origin／CSRF、無效 citation、注入／VIP、冪等／併發及 UI；只能證明對應離線行為 |
| 持久化 | Firestore emulator 與真雲端各自記錄，獨立程序 restart probe；缺真雲端測試列未完成 |
| 真 Gemini | 前一步 evidence 驅動補查 trace、模型／mode／token／耗時；缺憑證或 cap=0 則待測 |
| 線上整合 | Controller 核對 Vercel URL／版本、公開預覽與不可用提示、授權 reviewer 流程、部署設定及中英文件一致性 |

上述均為交接驗收契約，結果由實際命令與執行版本填入，不預寫 G0–G3 全通過。USD 100 為總上限，歷史 25 小時為全專案總工時限制；已用／剩餘尚待核對，原架構的 24／22 小時估算及「餘裕 1 小時」不能視為今日可用額。

角色邊界、時程／LineSleuth 衝突與 G0–G3 定義見 [roadmap](../roadmap.md)，產品需求及 AC-01–11 見 [PRD](../prd.md)。Paula 的文件檢查與離線回歸報告只證明該次檢查，不替其他角色或 Controller 宣告實作完成。
