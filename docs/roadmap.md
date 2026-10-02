# Roadmap：RepSafe × FIN-SHIELD（2026-10-02 執行版）

- 負責：Paula（PM）。依據：[本次會議](meetings/2026-10-02-FIN-SHIELD整合評估.md)、[現行 PRD](prd.md)與使用者本次平行實作、GitHub 中英文件及 Vercel 部署指示。
- 產品方向已定：RepSafe 為對話入口，FIN-SHIELD 為同產品的調查模組；主要使用者為有錢包／代收付能力之電商平台風控分析師，賣家為受保護者。
- 本次已授權六角色平行實作，Controller 負責整合、GitHub 發布、Vercel 部署與最終驗證。[48h 核心工程計畫](superpowers/plans/2026-10-02-finshield-48h-core.md)的介面與驗收仍適用；其中歷史「僅規劃／依序執行」由本次授權取代，實際交付以本版分工為準。文件、程式存在或部署授權均不等於功能已驗收。
- 預算勘誤：使用者指定總上限 USD 100，取代舊文件誤記的 100 SGD；帳單幣別與實際設定未查，本輪不改雲端預算或警示。
- 截止依 10/2 會議所核對的[官網](https://aibuildercup.com/index.html)：10/18；目標 10/17 提交留緩衝。[提交要求](https://aibuildercup.com/themes.html)含英文材料、3 分鐘影片與可運作雲端原型。
- 以下完成度以關卡證據判定；日期到達、文件完成或既有單元測試數都不代表新模組完成。

## English summary

Six roles are authorized to implement in parallel with explicit file ownership. The Controller owns integration, bilingual GitHub publishing and Vercel deployment. FastAPI remains portable; Firestore is required for durable online case and reviewer state. Missing credentials must leave protected operations unavailable. A labelled offline synthetic preview is permitted, but it cannot count as real Gemini investigation or G1 acceptance.

Execution authorization is settled; implementation, tests, cloud availability and G0–G3 acceptance require separate evidence. The USD 100 total budget and historical 25-hour total effort cap remain in force. Actual spending, hours used, remaining capacity and the LineSleuth schedule conflict are unresolved; parallel work does not create a new allocation or reduce summed person-hours.

## 1. 現況與資源帳

10/2 基線為 c12f390；六角色平行交付已整合成 `2d9c92e` 並推至 GitHub main。現有 FastAPI、文字／截圖與模型介面保留，新增分析師工作台已在 [Vercel](https://repsafe-finshield.vercel.app/finshield) 以明標 offline fixture 上線。255 tests passed、2 emulator skips；真 Firestore 兩程序 16 checks、線上 HTTP 含重新部署持久化 27 checks passed。私人 production reviewer 尚未配置；真 AI／人工語意與 G0–G3 未驗收。詳見 [部署證據](engineering/deploy.md)，不填造工時、帳單或省時數字。

| 資源 | 已知約束 | G0 須補的證據 |
|---|---|---|
| 人時 | 原總上限 25 小時，包含找案例；不是新版另有 25 小時 | 實際已用、剩餘與可投入時段；規劃、測試、訪談、文件、錄影均核算，不沿用舊「約 1 小時餘裕」 |
| 新增工程估算 | Eddie 拆項：48h 核心 24–36 人時，內含 6–10 人時整合／安全驗收；加 G0 1–2 與 G2 4–6 共 29–44 人時，另計訪談／提交材料／影片等 | 取代會議 24–40 粗估作為本版工程規劃；仍不是已批准配額，須與既有已用工時合計，不重複加測試。核心本身已與原25小時總限明顯衝突 |
| 預算 | 總上限 USD 100；舊 100 SGD 為誤記；已用及餘額未知 | 核對帳單幣別、已支出與實際設定。若以 SGD 計價，另核對換算依據；未核對前不換算推估餘額，也不將總額視為全數可用 |
| 警示 | 舊文件記載 50／90／100%，實際設定待核對；警示不是自動停止扣款 | 本次不改門檻、不新增付費資源；核對其金額／幣別是否符合 USD 100 上限，原停損保護不取消，不能以舊 SGD 數字當已確認設定 |
| LineSleuth | 原 10/12 起交還時間未解除 | 與英文材料／影片時段核對；未確認前不得佔用或默認延期 |

本次實作授權已成立，資源核對仍未完成。若量測顯示必要核心無法納入剩餘資源，按第 5 節縮案並回報具體缺口；不得把已授權解讀成可超支／超時。付費試跑及資源擴張不能由工作角色自行啟動。單案成本與回本目前待估，不能用獎金或未驗證省時抵算。

### 1.1 平行實作與檔案責任

各角色只直接編輯自己的路徑；同一 worktree 的他人改動須保留。工作角色不開子代理、不 commit／push／deploy；整合與發布統一由 Controller 執行。每位角色另交自己的實作／測試報告，不能以角色口頭完成取代 Controller 驗證。

| 角色 | 本次擁有的交付路徑 | 整合責任 |
|---|---|---|
| Paula | `docs/prd.md`、`docs/roadmap.md`、`docs/engineering/architecture.md` | 產品範圍、執行授權、共同架構與驗收狀態；不寫程式 |
| Eddie | `app/finshield/**`、`app/gemini.py`、`app/main.py`、`requirements.txt`、`.env.example`、`tests/conftest.py`、`tests/finshield_fakes.py`；資料／規則、狀態、store emulator、access、citations、investigator、API 與 Gemini limits 測試 | 後端契約、Firestore、身分／狀態與模型界限 |
| Dana | `app/static/finshield.html`、`finshield.js`、`finshield.css`、`app/static/index.html`（僅入口連結）、`docs/design/ui-spec.md`、`docs/design/storyboard.md`、`tests/test_finshield_frontend.py` | 英文雙狀態介面、引用與明確覆核操作 |
| Sandy | `README.md`、`README.zh-TW.md`、`docs/pitch/pitch-script.md`、`docs/sales/seller-outreach.md`、`docs/sales/data-sources.md` | 中英公開說明、pitch 與市場證據邊界 |
| Felix | `docs/finance/budget.md` | 資源核算欄位與限制；無資料不補填實際支出／工時 |
| Quinn | `docs/qa/test-plan.md`、`docs/qa/bugs.md`、`tests/test_finshield_acceptance.py`、`tests/test_finshield_eval.py`、`scripts/finshield_smoke.py`、`scripts/finshield_restart_probe.py`、`scripts/finshield_ui_smoke.py`、`scripts/eval_finshield.py`、`eval/finshield/g2-v1.json` | 獨立驗收／評測及最後唯讀檢查 |
| Controller | 部署設定、`.gitignore`／`.vercelignore`、`docs/engineering/deploy.md`、依賴環境 | 契約整合、版本／測試核對、GitHub 發布、Vercel 部署與線上驗證 |

平行的是實作工作，資料／API 契約及驗收依賴仍存在。測試遇到同時編輯造成的缺檔或不一致，記錄實際失敗供整合，不能弱化測試求過關。

### 1.2 部署與證據狀態

| 項目 | 現行要求／待補證據 |
|---|---|
| Vercel + 可攜 FastAPI | `2d9c92e` 已部署，首頁／工作台／資源 200；Python 3.12、sin1、Hobby。27 項線上 HTTP 通過；不等於真 AI 或完整覆核驗收 |
| Firestore | 無金鑰 production-only federation 已在線上讀寫驗證；兩程序 16 checks、重新部署兩案 payload／付款重送保持一致。先前間歇無法存取原因未定，QA-001 保留 |
| 模式與配額 | `FINSHIELD_MODEL_MODE=offline_fixture\|gemini` 獨立於原聊天模式；功能預設關閉、model-call cap 預設 0。offline fixture 可示範證據流程，不能計入 G1 真 AI |
| 公開預覽與覆核 | 可公開明標 Synthetic／Simulated 模板；viewer 不自動有 review 權。缺 Firestore／憑證時明示不可用，不偽裝操作成功 |
| GitHub 中英文件 | 中英 README、六角色文件、程式與測試已推 main；團隊設定、秘密及私人資料排除。後續 docs-only 提交記錄實際部署證據 |
| 驗收真實來源 | 實作版本、實際測試命令／結果、live Gemini trace、Firestore 重啟證據、雲端 UI／API 核對須可對應；未執行項目明列待測 |

## 2. G0–G3 完成關卡

目前 G0–G3 均未驗收。各關卡需保存版本、執行結果與必要證據；只改文件不構成關卡通過。

| 關卡 | 範圍／需求 | 完成條件 | 未過時 |
|---|---|---|---|
| G0：資源／連線驗證 | 原資源核對；FS-02/04/05 的資料、政策及調查邊界 | 實作授權已成立；仍須核對剩餘人時／預算與時段、核心估算是否可容納。固定兩案、共同 ID、政策版本、規則與 reviewer 方案；記錄步數、逾時、呼叫上限。於獲准試跑範圍驗證一次真 Gemini 結構化呼叫，記錄 model／mode／用量及首頁回歸 | 可執行已授權的平行實作，G0 仍標未驗收；不得自行啟用付費呼叫、擴張資源或宣稱連線通過。真 Web Risk 另列結果 |
| G1：兩案核心 | FS-01–10；PRD AC-01–11 | 兩案從對話線索、每筆規則、HOLD／模擬通過，到真 Gemini 依前步結果補查、有效引用／反證／缺失、人工 decision 與案件記錄跑通。AC-01–11 全有結果，包含來源限制、注入、無權 review、重送／並行、重啟及首頁回歸。只用 fixture 不達標 | 修阻斷問題或依剩餘資源縮案；任何核心條件未過，不標「48h 核心完成」 |
| G2：新案件測試 | FS-11；獨立調查評測與回歸 | 凍結獨立於兩個展示案及 prompt 範例的新案件集，涵蓋高風險、正常、合理反證、缺 KYC／歷史、正常共享設備、注入、工具故障及越權／重送／重啟。逐案記預期與實際；定義的關鍵狀態／權限／無效引用測試不得失敗，正常案不可全擋。對話基線另測另報，延遲／用量／成本有實測或明列缺項 | 失敗項留明細、修復再驗；缺必要測試不能靠日期或舊 33 則補成通過 |
| G3：英文材料／影片 | 已驗證的同產品原型與提交材料 | 英文介面／問題陳述／社會效益／pitch／3 分鐘影片完成；影片與可運作雲端原型的版本、合成標記、能力敘述和實測數一致；雲端入口與核心流程再次核對，資格／表單待辦清楚，10/17 目標提交前逐項核對官方要求 | 材料可先起草；G1/G2 不足不能寫成通過。與 LineSleuth 衝突未解不默認延長工時 |

關卡依賴為 G0 → G1 → G2 → G3 驗收。程式、獨立測試集、UI 與中英材料可依本次授權平行準備，最終通過宣稱仍按依賴核定。Vercel 上能開啟預覽不代表 G1，離線測試也不等於真 Gemini 或 Firestore 跨程序驗證。G1 的兩案驗證只支持合成原型可行，不代表市場需求或生產能力已證明。

## 3. Eddie 的 48h 核心拆解輸入

工程拆解已寫入 [48h 核心計畫](superpowers/plans/2026-10-02-finshield-48h-core.md)，含六個工作包、介面、測試步驟與 FS→Task→AC 對照；以下是產品整合依賴，不是要求各角色排隊。工程計畫第 6B 屬 G2，其素材／測試可平行實作，但 G2 驗收不混入 G1 成果。

48 小時是連續日曆窗口，不是 48 人時。本次已進入授權實作；精確 T0 與各角色實際投入由 Controller 記錄，本文件不回填不存在的時間帳。G0 證據仍須補齊，窗口內總投入受剩餘人時限制；T0 + 48h 依證據盤點通過／失敗／未完成。

| 順序 | Eddie 拆解的工作包 | 驗收對照／必要輸出 |
|---|---|---|
| 1 | 凍結兩案共同 ID 合成資料、版本政策、工具範圍與合理反證 | FS-02/04；兩案預期結果、工具可讀範圍、來源可回查，無任意上傳 |
| 2 | 每筆付款規則與狀態、持久化、最小 reviewer 權限／審核／冪等 | FS-03/07/08；先能獨立於 LLM 判定及審核；無權限者不能改狀態，重啟不丟 HOLD |
| 3 | 真 Gemini 有限補查、citation 驗證與失敗處理 | FS-05/06/09；至少一次根據前步觀察選擇補查，缺證停止，不把模型接到付款寫入 |
| 4 | 最小英文案件視圖、來源、一次受限追問與明確 decision | FS-01/10；保留首頁／對話；Escalate 與 Dismiss 不放行；HTML／JSON 摘要足夠 |
| 5 | 兩案及其故障／安全變體驗收，記錄實際投入與用量 | FS-11、AC-01–11；結果可重現、未通過誠實列出，交 G1 判定 |

Eddie 已在工程計畫列明依賴、估算人時、驗收 ID、必要／可延後；與剩餘資源是否相容仍由 G0 核對。上述不預填各包完成或保證工時；畫面可平行製作，整合驗收不可略過權限與記錄。

## 4. 候選日程與交付衝突

10/2 的實作授權已成立，10/2–10/4 保留為候選 48h 驗收窗口；是否達標取決於 G0/G1 證據與實際 T0。若實際開始較晚，按 T0 重排並重新檢查截止可行性，不壓縮必要驗收或自動擠占 LineSleuth。

| 候選日期 | 工作重點 | 條件／限制 |
|---|---|---|
| 10/2–10/4 | 平行實作、G0 證據與 G1 兩案核心 | 已授權實作；截止仍為候選，期末核對真 AI、全部核心驗收、實際工時／費用 |
| 10/5–10/8 | G2 新案例、必要證據介面修整 | G1 通過且剩餘資源足夠；不加入四獨立 agents、任意文件上傳或完整圖 |
| 10/9–10/11 | G2 回歸、故障及部署驗證 | 沿用原 10/9 功能凍結約束；之後只做驗收與阻斷缺陷修正，不追加功能 |
| 10/12–10/16 | G3 英文材料、3 分鐘影片 | 與原 10/12 交還 LineSleuth 衝突，日期待安排；可前移或精簡製作，不視為已承諾占用 |
| 10/17 | 目標提交／緩衝 | 以 G3 與實際提交核對為準，不等於已送出 |
| 10/18 | 官網截止 | 不因內部關卡或排程重估而順延 |

兩週原型是否可行，須用 G0 剩餘資源與 G1 實際投入更新估算；新版核心 24–36 人時（加 G0、G2 為 29–44）與原 25 小時總限的衝突目前尚未解決。

## 5. 縮 scope 優先順序

1. 先移除額外展示成本：複雜圖動畫、裝飾面板、影片特效、PDF 匯出；影片採實機操作加英文字幕。
2. 延後非核心廣度：任意 KYC 上傳、完整關係圖／PDF 庫、外部案件整合、四獨立 agents、完整會員產品。這些本來就不在 48h，不能假稱移除即可省下既已排定的核心工時。
3. 核心 UI 只保留固定兩案、最小來源視圖、一次受限追問及明確人工操作；報告用 HTML／JSON。保留首頁與既有文字／截圖，不以關掉原功能換時間。
4. 仍不夠則回報「G1 未達標」，提出純調查草稿的降階方案供後續決定；不得偷偷刪掉核心驗收、延長投入或將離線展示稱為真 AI 核心完成。

不可縮掉：真 AI 依證據補查、兩案中正常不全擋、可回查證據與反證、受限資料來源、付款規則與 AI 分權、伺服器人工覆核／審核、缺證策略、冪等／重啟一致性與對應安全測試。不放寬原對話基線換取新版「通過」。

## 6. 未決事項（實作授權已成立）

| 未決 | 對後續的影響／處理 |
|---|---|
| 真實案例不足：原「不足 3 則停工」與「情境改寫繼續」相衝突 | 本次已授權固定合成資料的技術實作；市場驗證門檻仍待釐清，不能把合成案當客戶實證或宣稱商業關卡通過 |
| 已用工時／費用未知，新增估算可能超出餘額 | G0 核對後縮案；追加資源須另有授權，不能預填餘額或調高上限 |
| LineSleuth 10/12 交還與錄影日期衝突 | 保留原優先事項；安排前移／精簡或另取得明確調整，不默認延期 |
| 主辦多作品／隊友重疊／資格及原型維持期限 | 依正式回覆與提交表單核對；本模組不是自動新增第三件作品。主辦未回覆時的繼續條件仍未決 |
| 先前 LineSleuth 主流程未通則停的判準 | 依該專案實況與既有安排核對；本次不宣稱其已通過或移除保護條件 |
| 商業需求與效果 | 建議訪談 2 位分析師、1 位採購主管，取得工作流／每案時間／現用工具／願付條件；未執行，不把詐騙總量當客戶需求 |
| 原對話誤判上限／一致性提議 | 保留 PRD 歷史基線：正常誤判最多 1；放寬至 2、兩次不一致最多 3 則均未採用，與新案件指標分開 |

產品角色、同產品模組方向、平行實作、GitHub 中英文件發布及 Vercel 部署均已授權，不列為再次確認事項。尚待處理的是資源缺口、環境可用性、實際驗收結果與上述外部限制。

## 7. 歷史區段：9/24–9/25 舊時程與停損沿革

本節僅供追溯，不是目前完成狀態或新的執行命令。舊表格中的「今天」、寄信／查帳／切換日期不能當作已執行證據。

| 舊紀錄 | 本版如何解讀 |
|---|---|
| 約六成完成；9/28 切真 Gemini | 歷史估計／計畫。10/2 已知仍 offline_fixture／fixture，真 AI 完成度以 G0/G1 證據取代百分比 |
| 9/30–10/4 跑 33 則對話 ×2，另加 5 則 injection | 保留為對話基線計畫，條件完整列於 PRD 第 9 節；不是新案件評測成果 |
| 9/28 切換失敗就縮成 20 則 | 舊縮減提議不自動套用；本版不減對話契約或新核心驗收 |
| 不做新 UI／平台／登入／歷史 | 舊單頁產品限制；新版已授權實作最小調查視圖、受限合成資料、reviewer 授權和案件記錄，仍不接真金流 |
| 10/9 凍結、10/10–10/16 影片、10/17 緩衝 | 凍結約束與提交緩衝保留；影片排程與 LineSleuth 衝突未解，不把歷史日期當現行承諾 |
| 後端 5／評測 7／前端 4／部署影片 5／找賣家 3，共 24、餘裕 1 小時 | 舊估算不是實際已用／剩餘帳；總上限仍 25，G0 重新核對，原找賣家配額不視為可任意挪用 |
| 舊文件誤記 100 SGD，並記載 50／90／100% 警示 | 金額已更正為 USD 100；帳單幣別與實際設定未核對。舊 50／80／90 替代提議未採用，本次不改雲端、不推估餘額 |
| 主辦不允許多作品、案例不足、LineSleuth 未通、工時超限、費用達線等停損 | 未被本次文件默默取消；案例與主流程判準衝突列第 6 節，資源硬限及 LineSleuth 保護仍適用 |

舊版賣家訪談、案例同意／打碼與對話測試仍有價值，但不能代替平台分析師／採購驗證。實際進度只回報可查證的完成項，不重用舊「六成」或示意「80%」。
