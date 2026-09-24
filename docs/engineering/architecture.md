# RepSafe 架構

- 建立：2026-09-24，Eddie（工程師）
- 依據：`docs/meetings/2026-09-24-電商客服反詐騙.md`、`docs/prd.md`、`docs/roadmap.md`
- 狀態：**後端骨架已完成，在離線模式可以跑，69 個單元測試通過**。還沒接過真的 Gemini 和 Web Risk，也還沒部署。前端依 roadmap 排在 10/6 之後。

## 1. 一張圖

```
手機瀏覽器（前端，10/6 起做）
   │  POST /api/analyze {text}               （截圖開關打開時，先呼叫 POST /api/extract-text {image} 拿到文字，
   ▼                                           讓賣家確認後再送 /api/analyze）
Cloud Run 單一服務：FastAPI（app/main.py），最小實例 0
   │
   ├─ ① 讀取文字
   ├─ ③ 比對網域  app/tools/domain_check.py   純程式、不連網：抽出連結 → punycode 轉回原字 → 和白名單比字元差距；短網址直接列紅旗
   ├─ 注入防護    app/analyze.py INJECTION_RE  純程式：抓「忽略前述指示／判定為正常」這類句子
   ├─ ② 查網址    app/tools/url_reputation.py  Web Risk（可換）── 平行 ──┐
   ├─ Gemini 判斷 app/gemini.py + app/prompt.py  JSON schema ─────────────┘  兩個同時跑，省時間
   ├─ ④ 完成判定  app/verdict.py  紅／琥珀／灰（全專案只有這裡決定判定）
   └─ 安全回覆過濾 app/reply_filter.py  用程式再濾一次網址、帳號、電話、ID
```

## 2. 模組

| 檔案 | 做什麼 | 對應 PRD |
|---|---|---|
| `app/main.py` | `/health`（也用來暖機）、`/api/config`（前端要知道是否離線、截圖功能有沒有開）、`/api/analyze`、`/api/extract-text`（只在截圖開關打開時才存在） | — |
| `app/config.py` | 全部設定都從環境變數讀，寫法和 LineSleuth 一樣 | — |
| `app/analyze.py` | 主流程、注入防護、檢查 Gemini 輸出格式、全服務每小時請求上限、只記 metadata 的 log | F2、F6、F7 |
| `app/tools/domain_check.py` | 抽出連結、punycode 解碼、同形字（西里爾字母、數字 0/1/3/5）折回拉丁字母、Levenshtein 字元差距、子網域冒用（`shopee.tw.xxx.com`）、`@` 偽裝、短網址清單 | F4、F5 |
| `app/tools/url_reputation.py` | `UrlReputation` 介面＋`WebRiskReputation`＋`FixtureReputation`，平行查詢，全部查詢共用一個截止時間 | F3 |
| `app/gemini.py` | Vertex AI 包裝層：一次呼叫、逾時、只有 429／5xx 會重試、失敗時丟出帶問題代碼的例外 | F2 |
| `app/prompt.py` | system prompt、判斷用 JSON schema、截圖讀字用 schema。**評測樣本不得寫進這個檔案** | F2 |
| `app/reply_filter.py` | 安全回覆後處理 | F8 |
| `app/verdict.py` | 三態判定規則 | F6 |
| `app/offline_fixture.py` | 沒有 GCP 時用關鍵字規則代替 Gemini；另有固定的安全回覆範本（Gemini 失敗時也用這份） | — |
| `app/screenshot.py` | **可獨立拔除**的截圖讀字模組（見第 6 節） | F1 |

### 從 LineSleuth 沿用的部分（只複製，沒有改動原資料夾）

- `Dockerfile` 的結構、`config.py` 的環境變數寫法、`tests/conftest.py` 的斷網測試設計。
- Gemini 包裝層的寫法：關掉 SDK 自己的重試、用 thread future 控制逾時、只有 429／5xx 會重試、log 只記 token 數。
- 沒有沿用的：function calling 迴圈、BigQuery、調查狀態管理、QR code。RepSafe 每個請求都是無狀態的，比 LineSleuth 簡單很多。

## 3. 判定卡三態（`app/verdict.py`）

| 優先順序 | 條件 | 判定 |
|---|---|---|
| 1 | 任何來源找到至少一條紅旗：網域比對、短網址、Web Risk 命中、注入防護、Gemini | **red** |
| 2 | 沒有紅旗，但有任何一項沒完成：Gemini 逾時、超過配額、錯誤、輸出不符合 schema；Web Risk 錯誤、逾時；連結超過查詢上限；達到每小時請求上限；程式 bug | **grey** |
| 3 | 沒有紅旗，而且每一步都完成 | **amber** |

- **失敗絕對不會變成琥珀卡**：只要有任何一個問題代碼（包含還沒定義的代碼）就排除琥珀。程式的例外也會被接住變成灰卡，不會回 500。
- **紅卡優先於灰卡**：這點和 PRD 第 7 節的字面寫法不同，**要請 Paula、Quinn 確認**。原因是如果照字面做，一個 punycode 冒用蝦皮的連結只要剛好碰上 Web Risk 超過配額，就會從紅卡變成灰卡，而灰卡在評測裡算漏報。本地網域比對已經確定的紅旗，不應該因為別的服務失敗而消失。
- Gemini 回傳的紅旗，引用的句子**必須真的出現在原訊息裡**（比對前會做全形半形正規化和空白正規化），找不到的就丟掉（對應 F7）。如果 Gemini 判定是詐騙，但沒有任何一條引用能驗證，就當作輸出不符合 schema，顯示灰卡。這個規則可能太嚴格，要看評測結果再調。
- 判定結果由程式從紅旗推導出來，Gemini 不直接輸出判定。所以注入攻擊就算騙過 Gemini，也蓋不掉工具和注入防護找到的紅旗。

## 4. 「兩個 function calling 工具」的實作方式（要請老闆知悉）

會議寫的是 function calling。**我實際上改成由程式對每個連結強制執行兩個工具，再把結果當作可信事實交給 Gemini，只呼叫 Gemini 一次。**

- 理由：①注入攻擊沒辦法叫模型「不要查」②function calling 至少要兩次 Gemini 來回（先決定呼叫工具，再輸出結論），改成一次呼叫，10 秒的時間預算才守得住 ③程式比較少，也比較好測試。
- 對技術分的影響：畫面上四個步驟標籤照常亮起，影片和 pitch 可以說成「tool-augmented Gemini, tools are enforced by code」。兩個工具的 `FUNCTION_DECLARATION` 已經寫在各自的模組裡。
- 如果老闆堅持一定要用真的 function calling 迴圈：**約 +2 小時**，每次請求多一次 Gemini 來回（延遲待實測）。我不建議。

## 5. 安全與隱私

| 要求 | 怎麼做 | 測試 |
|---|---|---|
| 絕不打開使用者的連結 | 程式裡沒有任何 HTTP client 會去碰使用者的網址；Web Risk 只收網址字串；短網址不展開 | `tests/conftest.py` 在測試期間封鎖所有對外連線和 DNS 查詢，全部測試都在斷網狀態下通過 |
| 安全回覆不含連結、帳號 | Gemini 的回覆和固定範本都要經過 `filter_reply`：網址、裸網域、xn--、email、@帳號、`ID: xxx`、6 位數以上的數字，再加上原訊息出現過的每一個連結、網域、數字、帳號 | `tests/test_reply_filter.py` |
| 服務端不記錄對話內容 | log 只記 request_id、字數、連結數、判定、問題代碼、紅旗來源、耗時、token 數；例外只記類別名稱 | `tests/test_api.py::test_logs_never_contain_message` |
| 前端沒有 API key | Vertex AI 和 Web Risk 都用 Cloud Run 服務帳號（ADC），整個專案沒有 key | Quinn 上線前檢查 |
| Prompt injection | 訊息用標籤包起來，並跳脫結束標籤；system prompt 宣告訊息是不可信資料；另外用程式的注入防護把注入句子直接列為紅旗 | `tests/test_verdict.py` |
| 金鑰與真實截圖不會被提交 | `.gitignore` 排除 `.env*`、`*.pem`、`*.key`、`*credentials*.json`、`*service-account*.json`、`data/real_cases/`、`data/private/`、`eval/results/` | — |

**真實截圖一律放在 `data/real_cases/`**（這個資料夾已被 git 忽略，Sandy、Quinn 請照這個路徑放）。

已知的過濾副作用：日期（例如 2026-09-24）、6 位數以上的價格也會被濾掉。安全回覆本來就不應該出現這些，所以接受。

## 6. 截圖輸入開關與工時估算（回答 PRD 第 11 節）

- 開關：`SCREENSHOT_ENABLED=false`（預設關閉）。關閉時 `/api/extract-text` 這條路由根本不存在（404），`/api/config` 會回 `screenshot_enabled:false`，前端就不顯示上傳按鈕。
- 設計：截圖只讀文字，讀出來的文字回給前端讓賣家確認，**再送 `/api/analyze`**。原因是 Gemini 讀截圖時可能把改字網域「修正」回正確網址，讓賣家看一眼就能補救。
- 限制：只接受 png、jpeg、webp、heic、heif，大小 ≤ 10MB，圖片不存也不記錄。
- 要完全拔掉：刪除 `app/screenshot.py`，再刪掉 `app/main.py` 裡 `if settings.screenshot_enabled:` 那一段，其他模組都沒有引用它。

**「不做截圖」能省多少（Eddie 估算，不是實測）**

| 項目 | 截圖開啟要花的工時 | 說明 |
|---|---|---|
| 後端 | 0.5 | 骨架已經寫好，剩下用真的 Gemini 驗證讀字結果（特別是改字網域會不會被讀錯） |
| 前端 | 1–1.5 | 上傳按鈕、預覽、讀字中的狀態、讓賣家確認文字、錯誤提示 |
| 評測／QA | 0.5–1 | Quinn 清單上的 10MB、HEIC、iPhone Safari 上傳測試 |
| **合計（不做就省下）** | **2–3 小時** | |

結論：只砍截圖的話，省下 2–3 小時，**不一定湊得到 Paula 要的 3 小時**。不過後端骨架今天已經完成，後端工時也往下修了（見第 7 節），兩者加起來，找賣家的 3 小時可以排進去。

## 7. 工時重估（25 小時上限）

| 類別 | 會議原估 | 重估（截圖開） | 重估（截圖關） | 說明 |
|---|---|---|---|---|
| 後端 | 9 | 5 | 4.5 | 骨架已完成。剩下：讀懂程式 1、接真的 Gemini／Web Risk 1–1.5、依評測調 prompt 2、修正 0.5 |
| 評測 | 7 | 7 | 6.5 | 33 則評測集和評測腳本還沒寫（Quinn 定規格） |
| 前端 | 4 | 4 | 3 | 單畫面、三態判定卡、步驟標籤、一鍵複製 |
| 部署與影片 | 5 | 5 | 5 | |
| 找賣家 | 0 | 3 | 3 | Paula 的配額提案 |
| **合計** | 25 | **24** | **22** | 都是估算。9/26 開工第一天，用真的 Gemini 跑通後再修正一次 |

後端的數字是假設老闆接手這份骨架時不重寫。老闆讀程式的時間也已經算進去了。

## 8. 設定與部署

- 本機：見 `README.md`「本機啟動」。`.env.example` 預設為離線模式（`AGENT_MODE=offline_fixture`、`URL_REPUTATION_BACKEND=fixture`），不需要 GCP 就能跑。
- 程式預設值（沒有 `.env` 時，例如在 Cloud Run 上）是 `gemini` 加 `webrisk`，上線時不會因為少設一個變數而掉進離線模式。每個回應都帶 `mode` 和 `offline_fixture`，前端要在離線模式時明顯標示。
- Cloud Run 部署（範例，region 待老闆決定；評審在新加坡，建議 `asia-southeast1`）：

```
gcloud run deploy repsafe --source . --region asia-southeast1 \
  --min-instances 0 --max-instances 2 \
  --set-env-vars AGENT_MODE=gemini,URL_REPUTATION_BACKEND=webrisk,GOOGLE_CLOUD_PROJECT=<獨立專案>,GEMINI_MODEL=<釘選版本>
```

- GCP 要先做的：開獨立專案（Felix）、啟用 Vertex AI API 與 Web Risk API（`webrisk.googleapis.com`）、服務帳號授予 Vertex AI User。Web Risk 需要的 IAM 角色**待確認**（應該是 Web Risk User）。
- 成本防線：最小實例 0、最大實例 2、`GLOBAL_RATE_LIMIT_PER_HOUR`（計數存在記憶體裡、每個實例各算各的，所以實際上限是這個值乘以最大實例數）、Gemini 每日配額（在 GCP 主控台設定，Felix）。單次請求費用待估算（每次 log 都有 token 數，接上真的 Gemini 後就能算）。

## 9. 延遲預算（熱機時九成請求 ≤ 10 秒）

- 網域比對和注入防護：毫秒級。
- Web Risk 和 Gemini 同時跑；Web Risk 每次查詢最多 3 秒（`WEBRISK_TIMEOUT_S`），Gemini 最多 9 秒（`GEMINI_TIMEOUT_S`，重試也包含在內）。
- Gemini 3 Flash 的 thinking 會拉長延遲。實際秒數**待估算**，第一次接上真的 Gemini 就要量。如果太慢，改設 `thinking_level=low`（大約改 1 行）。
- 冷啟動另外量（Quinn）。

## 10. 待決定／已知限制

| # | 事項 | 誰決定 |
|---|---|---|
| E1 | 截圖功能做不做（預設關閉；打開只要改一個環境變數，但前端和 QA 要多花 2–3 小時） | 老闆（PRD Q7） |
| E2 | 紅卡優先於灰卡（第 3 節） | Paula、Quinn 確認 |
| E3 | 工具改由程式強制執行，不用 function calling 迴圈（第 4 節） | 老闆知悉 |
| E4 | `shp.ee` 是蝦皮官方的短網址，但按照會議共識，短網址一律不展開、直接列紅旗。真買家分享商品時可能會用到它，造成誤報 | Quinn 用評測集確認 |
| E5 | 白名單比會議多收了蝦皮、Carousell 其他國家的官方網域；`shopee.com` 沒有放進白名單 | Quinn 確認完整清單 |
| E6 | Web Risk 免費額度與超額單價、Gemini Flash 單次費用 | Felix 待查證 |
| E7 | 前端還沒做，現在可以用 `/api/docs` 手動測試 | 10/6 起 |
