# Deployment guide / 部署說明

## FIN-SHIELD on Vercel — 2026-10-02

The owner authorized parallel implementation, bilingual GitHub documentation and
Vercel deployment. The existing RepSafe homepage remains at `/`; the analyst
workspace is `/finshield`. **Deployment and live AI verification are separate
gates.** A synthetic offline workflow is not proof of an agentic investigation.

老闆已授權平行開發、GitHub 中英文說明與 Vercel 部署。保留 `/` 原有
RepSafe 對話與截圖預覽，新增 `/finshield` 分析師工作台。離線示範必須明示，
不得當作真 Gemini、準確率或重啟持久性的驗收證據。

### Current deployment evidence / 目前證據

- Vercel project: `repsafe-finshield`, existing Hobby team `hongchelai-5239`.
  Authentication and project linking are complete. Production domain is assigned
  as `repsafe-finshield.vercel.app`; deployment and HTTP/browser checks are pending.
- Existing GCP project: `repsafe-2026` (verified active, independent of LineSleuth).
- Firestore: first `(default)` database created 2026-10-02 in `asia-southeast1`,
  Native / Standard; the creation response confirms `freeTier: true`. This does
  not guarantee zero cost beyond the free allowance.
- APIs enabled: Firestore, IAM Credentials and STS. GCP access from Vercel uses
  narrowly scoped workload identity federation, **not uploaded ADC or SA keys**.
- Dedicated account `finshield-vercel@repsafe-2026.iam.gserviceaccount.com` created
  with `roles/datastore.user` in the dedicated RepSafe project. No downloadable
  key, Owner, Editor or Vertex permission was granted. Workload pool
  `finshield-vercel`, provider `vercel`, trusts only subject
  `owner:hongchelai-5239:project:repsafe-finshield:environment:production`, with
  team issuer `https://oidc.vercel.com/hongchelai-5239` and audience
  `https://vercel.com/hongchelai-5239`. Preview deployments cannot impersonate it.
- Total approved budget: **USD 100**, including existing expenditure and both
  platforms. No paid Vercel tier upgrade is authorized. Remaining balance and
  billing-currency alert conversion must be checked, not assumed.
- Real FIN-SHIELD model calls remain disabled by default; the durable call cap
  defaults to zero. Deployment success does not change these settings.

### Verified integration evidence / 已驗證整合證據

- Current offline suite: **255 passed, 2 skipped, 1 existing warning** (2026-10-02,
  `python -m pytest -q -p no:cacheprovider`). The skips require a local Firestore
  emulator; the warning is the installed Starlette/httpx deprecation. This is a
  working-tree checkpoint, not yet a deployed-commit guarantee.
- Real Firestore probe `fs-20261002-a`: three synthetic cases (held, reviewer
  approved, interrupted investigation), separate write/read processes, **16 checks
  passed**. The official read CLI was rerun successfully after the storage RPC
  deadline changes. During earlier runs there were intermittent unavailable
  results; their cause is not established and remains in the QA ledger.
- Browser + actual HTTP router, explicitly injected local test store: risk HOLD,
  report/source drill-down, VIP cannot release, reviewer login, dismiss keeps
  HOLD, explicit approval, normal invoice counter-evidence, and cleared reviewer
  UI when switching cases. This is **not** hosted or durable browser evidence.
- Two-case offline smoke and eight-case independent fixture evaluation passed
  their offline checks. They deliberately report `g1_pass=false` and
  `g2_pass=false`: live-model adaptation and human semantic assessment remain open.
- Vercel authentication and exact team/project trust configuration are complete.
  Hosted token exchange, deployed URL checks, hosted browser and live Gemini
  validation remain pending. No live model calls were made.

### Runtime and packaging

`vercel.json` selects native FastAPI (`app/main.py`), Singapore `sin1`, and a
60-second function deadline. `.python-version` pins Python 3.12. Runtime
dependencies remain in `requirements.txt`. The investigator finishes within
its request budget; there is no durable background worker on Vercel.

`.vercelignore` excludes `.env*`, secrets, private cases, local team settings,
developer environments, tests and documents from the runtime upload. GitHub
still receives public code, tests and documentation; neither destination receives
`.claude/`, `.agents/`, `.codex/` or `.superpowers/`. Keep `app/static/` and
`app/finshield/fixtures/` in the deployed bundle.

### Environment checklist

Configure server-side values in the authenticated Vercel project. Never put
reviewer secrets, access tokens, session secrets or cloud credentials into public
JavaScript, the README or committed configuration.

| Setting | Initial deployment value / rule |
|---|---|
| `AGENT_MODE` | `offline_fixture`; legacy chat is explicitly labelled |
| `URL_REPUTATION_BACKEND` | `fixture`; no claim of a live Web Risk lookup |
| `SCREENSHOT_ENABLED` | `true`; preserve upload and preview |
| `MAX_IMAGE_MB` | `3` on Vercel, allowing base64 JSON overhead; local default stays 10 |
| `GOOGLE_CLOUD_PROJECT` | `repsafe-2026` |
| `FINSHIELD_ENABLED` | Enable only with durable storage and session configuration |
| `FINSHIELD_MODEL_MODE` | `offline_fixture` until a bounded live run is authorized/configured |
| `FINSHIELD_LIVE_CALLS_ENABLED` | `false` initially |
| `FINSHIELD_MODEL_CALL_CAP` | `0` initially; no automatic increase |
| `FINSHIELD_ALLOWED_ORIGIN` | Exact verified HTTPS production origin; no wildcard |
| `GCP_WORKLOAD_IDENTITY_AUDIENCE` | Exact GCP provider resource, beginning `//iam.googleapis.com/projects/` |
| `GCP_SERVICE_ACCOUNT_EMAIL` | Dedicated demo backend account; not an owner/editor account |

See `.env.example` for the full FIN-SHIELD storage and reviewer configuration.
Each browser receives a private synthetic case instance. Public visitors must not
receive reviewer powers. Missing storage/auth configuration must fail closed;
memory and ephemeral SQLite are not acceptable hosted persistence substitutes.

### Keyless access setup / 無金鑰存取

After confirming the Vercel team and project, create an OIDC workload provider
in `repsafe-2026`. Pin its issuer/audience to that Vercel team and constrain its
attribute condition to the exact deployment project and `production` environment.
Bind `roles/iam.workloadIdentityUser` on the dedicated account to that exact
subject only. Do not bind every member of the pool or trust arbitrary preview
deployments. Set the provider resource and account email as server environment
variables; they are identifiers, not keys.

`app/cloud_identity.py` uses the request's Vercel-injected OIDC token. Google STS
verifies the signed token and narrowly bound subject before granting short-lived
access. No gateway token is returned, logged or used as an analyst login.
Outside Vercel, existing local/Cloud Run ADC is preserved; on Vercel, missing
federation configuration fails closed. Verify the actual exchange on the final
deployment: successful local ADC tests do not prove Vercel federation works.

### Publish and verify

1. Run the full tests and review the exact changed/public file list.
2. Push the reviewed commit to `YMUNick/RepSafe`; do not force-push.
3. Authenticate Vercel and link the intended project. Use the existing tier;
   do not accept a paid upgrade to make deployment work.
4. Deploy the reviewed commit with `vercel deploy --prod`.
5. Verify `/`, `/health`, `/finshield`, static assets and both synthetic cases
   on the returned URL. `/health` intentionally retains the legacy response;
   FIN-SHIELD readiness must be checked through its own workflow.
6. Verify session isolation, CSRF, unauthenticated review rejection, authorized
   review, idempotent replay and durable state after a new process/deployment.
7. Only then record the exact URL, commit, mode and verification evidence here
   and in both READMEs. A local test or mocked store is not hosted evidence.

Recovery: redeploy the last verified Vercel deployment or turn off FIN-SHIELD
while leaving legacy RepSafe available. Do not erase database/audit records as a
rollback step. Keep the existing Cloud Run service unchanged unless separately
needed and explicitly recorded.

Official references: [FastAPI deployment](https://vercel.com/docs/frameworks/backend/fastapi),
[Python runtime](https://vercel.com/docs/functions/runtimes/python),
[keyless GCP access](https://vercel.com/docs/oidc/gcp).

## Historical Cloud Run record / 舊版紀錄

以下為 9 月部署與待辦的歷史紀錄，不代表 10/02 已切換真 AI，也不代表 Vercel
已部署。所有舊預算描述以目前 **USD 100 總額**為準。

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
| 預算警示（歷史） | 曾記錄 **100 SGD**、50％／90％／100％ 寄信；這不是目前授權總額。現行上限 **USD 100**，帳單幣別換算與實際警示值待重新核對 | 警示只寄信、不會停止扣款 |
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
