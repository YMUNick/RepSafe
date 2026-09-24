# RepSafe（暫定名）

> Reply safe. Keep your rep.

幫蝦皮、Carousell 小賣家在回覆前看出假買家的釣魚連結與話術，並直接給一段可以複製的安全回覆。

- 比賽：AI Builder Cup 2026，BFSI 賽道（備案 Retail & Commerce），繳交截止 10/18
- 形式：手機直向單畫面、英文介面；Gemini Flash 結構化輸出＋兩個 function calling 工具（Web Risk 網址信譽查詢、網域冒用比對）；部署在 Cloud Run
- 定位：老闆的第二件作品。工時上限 25 小時，10/11 前完成，10/12 起交還姊妹專案 LineSleuth
- 名稱：Rep 同時讀作 Reply 與 Reputation。商標與網域待查

## 狀態

**尚未開工**（2026-09-24）。要先過兩道關卡：主辦允許交兩件（9/30）、9/29 晚上盤點到 ≥ 3 則真實案例。詳見 `docs/roadmap.md`。

後端骨架已先備好（屬於 roadmap「停了也不虧」的部分）：離線模式可以跑，單元測試通過；還沒接真的 Gemini、Web Risk，也還沒部署。前端還沒做。

## 本機啟動

需要 Python 3.11。離線模式不需要 GCP（`.env.example` 的預設值）；判斷結果來自關鍵字規則，每個回應都會標 `offline_fixture`，**不能拿來 demo 或評測**。

```
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux：source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env            # macOS/Linux：cp .env.example .env
uvicorn app.main:app --reload
```

- 健康檢查（也用來暖機）：http://127.0.0.1:8000/health
- 手動測試分析 API：http://127.0.0.1:8000/api/docs → `POST /api/analyze`，body 為 `{"text": "..."}`
- 跑測試：`pytest -q`（測試期間會封鎖對外連線，任何開連結的行為都會讓測試失敗）
- 接真的 Gemini 和 Web Risk：先執行 `gcloud auth application-default login`，再在 `.env` 設定 `AGENT_MODE=gemini`、`URL_REPUTATION_BACKEND=webrisk`、`GOOGLE_CLOUD_PROJECT`。整個專案不使用 API key。
- 截圖輸入：`SCREENSHOT_ENABLED=true` 才會開啟，預設關閉（待老闆拍板，見 `docs/prd.md` 第 11 節）
- 真實截圖只能放在 `data/real_cases/`（已被 git 忽略），並且要先取得書面同意、打碼

## 文件索引

| 文件 | 內容 | 負責 |
|---|---|---|
| `docs/prd.md` | 產品需求：定位、MVP 做／不做、判定卡三態、驗收門檻、demo 劇本、找賣家工時方案 | Paula |
| `docs/roadmap.md` | 9/24–10/11 時程、停損點、老闆必做事項 | Paula |
| `docs/meetings/2026-09-24-電商客服反詐騙.md` | 立案會議紀錄 | — |
| `docs/engineering/architecture.md` | 架構、模組、判定三態規則、安全設計、截圖開關省下的工時、工時重估、部署設定、待決定事項 | Eddie |
| `docs/design/ui-spec.md` | 手機單畫面規格：版面、色彩與字體 token、輸入區兩種版本（截圖開關）、四步驟標籤、判定卡三態、英文 UI 文案定稿、各狀態、API JSON 欄位對照、給 Eddie 的前端掛載交接 | Dana |
| `docs/design/storyboard.md` | 3 分鐘影片分鏡：時間碼、畫面、英文旁白與字幕；開場 A 新加坡／B 台灣兩版（待老闆拍板）、demo 用訊息、錄影前檢查清單 | Dana |
| `app/static/index.html` | 單檔靜態前端（純 HTML/CSS/JS、沒有建置步驟），呼叫 `/api/config`、`/api/analyze`、`/api/extract-text`；要等後端加上 `/` 路由才打得開（見 `ui-spec.md` 第 9 節） | Dana |
| `docs/sales/seller-outreach.md` | 9/25–9/29 真實案例徵集：各管道中英文貼文範本、書面同意書範本（中英）、打碼規則與存放位置、20 分鐘訪談題目（含每月願付多少）、9/29 盤點表格式 | Sandy |
| `docs/sales/data-sources.md` | 影片與 pitch 需要的公開統計清單（新加坡、台灣、區域）、建議查找的官方來源、使用規則、找不到時的備用說法；目前全部「待驗證」 | Sandy |
| `docs/pitch/pitch-script.md` | Pitch 三句英文定稿＋中文對照、3 分鐘真人講稿（對齊分鏡格 ①–⑥）、競品與常見質疑的一句話回應、紅線、排練清單 | Sandy |
| `docs/finance/budget.md` | 獨立 GCP 專案、預算上限算法（金額待老闆拍板）、50／90／100% 警示設定步驟、警示不會停止扣款的四道防線、成本項目清單（單價全部待查證）、單次分析成本公式、各期間呼叫次數估算、25 小時工時兩方案與上限檢查 | Felix |
| `docs/finance/timesheet.csv` | 工時記帳表格式（五類：後端／評測／前端／部署影片／找賣家）；實際記帳建議放 `data/private/`，不 commit | Felix |
| `docs/qa/test-plan.md` | 測試策略、33 則評測集組成、判定規則（灰卡算漏報、失敗 fallback）、驗收門檻、盲測規則、熱機／冷啟動量測、E2／E4 的 QA 裁決、上線前檢查清單 | Quinn |
| `docs/qa/bugs.md` | Bug 與改善建議清單（交給 Eddie），對應 `tests/test_qa_adversarial.py` 的 strict xfail | Quinn |
| `docs/qa/organizer-inquiry-draft.md` | 寄主辦的英文詢問信草稿（交兩件、隊友重疊、原型開到何時、第三方 API、打碼截圖）＋回覆後的決策表 | Quinn |
| `eval/cases.jsonl`、`eval/edge_cases.jsonl` | 33 則合成評測集（20 詐騙／10 正常／3 injection）＋8 則不計分邊緣集；網址全部 defang（`hxxps://`）、只用保留網域 | Quinn |
| `scripts/run_eval.py` | 評測腳本：`--offline`（只驗流程與程式工具，不是 Gemini 準確率）、預設真 Gemini、`--url` 打 Cloud Run 量熱機延遲；結果寫到 `eval/results/`（不進 git） | Quinn |

其他成員的文件完成後，會補進這張表。
