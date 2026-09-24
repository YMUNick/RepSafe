# Pitch 講稿：RepSafe（3 分鐘）

> Reply safe. Keep your rep.

- 建立：2026-09-24，Sandy（業務）
- 依據：`docs/meetings/2026-09-24-電商客服反詐騙.md`（Pitch 三句、差異化、商業模式）、`docs/prd.md`（第 2、6、10 節）、`docs/design/storyboard.md`（分鏡與旁白）、`docs/design/ui-spec.md`（文案紅線、第 4 節說法統一）
- 搭配：`docs/sales/data-sources.md`（所有數字的來源）、`docs/sales/seller-outreach.md`（賣家原話與願付價格）
- **分工**：3 分鐘**影片**的旁白以 Dana 的 `storyboard.md` 為準（她的旁白是定稿）。這份是**真人上台版**（決賽 12/4、或任何要真人講 3 分鐘的場合），段落與時間碼和分鏡一格一格對齊，畫面就是分鏡那一套（現場 demo 或播影片）。兩份不一致的地方列在第 4 節，由 Dana 決定影片要不要跟著改。
- 2026-09-25 更新（依 `docs/meetings/2026-09-24-剩餘工作盤點.md`）：新增第 7 節「定價區間」（數字全部待估算，10/2–10/3 填）與第 8 節「評審 FAQ 草稿」。格①跟著分鏡改：開場已定新加坡、不放 SPF 數字，改放有書面同意的匿名賣家引言（見格①下方註記）。
- 語速：每秒約 2.5 個英文字（和分鏡一樣），3 分鐘上限約 450 字；本稿約 400 字，留時間給畫面切換。

## 標記說明（不要唸出來）

| 標記 | 意思 | 規則 |
|---|---|---|
| `{x}` | 待評測 | 只能填 Quinn 最後一次評測結果檔的數字，不能挑數字 |
| `[待驗證 S#]` | 待查公開來源 | 對照 `docs/sales/data-sources.md` 的 ID；沒來源就用該段的備用句 |
| `[待訪談]` | 待賣家訪談 | 只能用有引用授權的逐字原話或訪談數字 |

## 1. Pitch 三句（英文定稿＋中文對照）

會議版的三句（`docs/meetings/…` 共識）照原意定稿，只做兩個調整，理由寫在表下。

| # | English（定稿） | 中文對照 |
|---|---|---|
| 1 | **Small sellers on Shopee and Carousell get fake buyers who send phishing links, and once the chat moves to WhatsApp, LINE or Facebook, the platform's scam warnings can't follow.** | 蝦皮、Carousell 的小賣家常遇到假買家丟釣魚連結；對話一被帶到 WhatsApp、LINE、FB，平台的防詐警告就管不到。 |
| 2 | **The seller pastes the chat into RepSafe. Gemini, backed by Google Web Risk and a look-alike domain check that run on every link, flags the risky lines and writes a reply the seller can copy and send.** | 賣家把對話貼進 RepSafe。Gemini 搭配「每個連結都一定會跑」的 Google Web Risk 網址信譽查詢與冒用網域比對，標出可疑句子，並寫好一段可以直接複製送出的回覆。 |
| 3 | **We're on the seller's side, we work with any chat app, and we stop the scam ten seconds before the reply.** | 我們站在賣家這邊，任何聊天軟體都能用，在回覆前 10 秒就把詐騙擋下來。 |

調整理由：

- **第 1 句**：會議版寫「LINE、FB、Carousell」，但 Carousell 本身就是平台。改成「平台＝Shopee、Carousell；站外＝WhatsApp、LINE、Facebook」，並加上 WhatsApp，因為評審在新加坡，那裡賣家被帶去的通常不是 LINE。旁白可以講這些 App 名稱，畫面上不放它們的 logo（分鏡鐵則 1）。
- **第 2 句**：照 `ui-spec.md` 第 4 節統一說法，強調「工具由程式強制執行」，**不說 function calling**（Eddie 的實作決定①）。也不說 "detect"、"safe"、"guaranteed"。
- **第 3 句的「ten seconds」有條件**：熱機 P90 ≤ 10 秒才能講（`{s}` 待評測）。超過就改成 `and we stop the scam before the reply.`（和分鏡格 ⑥ 備註一致）。

**一句話版**（電梯、表單欄位、影片說明欄用）：
`RepSafe checks a buyer's message before a small seller replies, flags phishing links and scam scripts, and gives a reply that's safe to send.`
（中文：RepSafe 在小賣家回覆前檢查買家訊息，標出釣魚連結與詐騙話術，並給一段可以放心送出的回覆。）這裡的 "safe to send" 講的是**回覆**，不是判定，和分鏡格 ② 旁白同一個用法。

## 2. 3 分鐘講稿（與分鏡格 ①–⑥ 對齊）

| 格 | 時間 | 秒數 | 內容 | 三句出現在哪 |
|---|---|---|---|---|
| ① | 0:00–0:20 | 20 | 痛點開場（A 新加坡／B 台灣，待老闆拍板） | 第 1 句 |
| ② | 0:20–0:28 | 8 | 片名＋一句話 | 第 2 句（前半） |
| ③ | 0:28–1:30 | 62 | 改字網域釣魚 demo | 第 2 句（技術） |
| ④ | 1:30–1:55 | 25 | 複製安全回覆 | 第 2 句（後半） |
| ⑤ | 1:55–2:25 | 30 | 正常買家＋ prompt injection | — |
| ⑥ | 2:25–3:00 | 35 | 評測數字、差異化、收尾 | 第 3 句 |

### 格 ①　痛點開場（0:00–0:20）

**版本 A：新加坡（建議）**

> Small sellers on Carousell and Shopee get messages like this. A "buyer" sends a link to "verify" your account before they pay. `[待驗證 S1：Singapore Police recorded {N} e-commerce scam cases in {year}.]` And once the chat moves to WhatsApp, LINE or Facebook, the platform's scam warnings can't follow.

- **2026-09-25 起**：影片格①已拿掉警方數字（`storyboard.md` 格①）。真人版也照做：警方那句先不講，改成 `One seller told us: "[賣家原話英文翻譯]."`（`[待訪談]`，要有書面授權 B＋C，見 `seller-outreach.md` 第 7.2 節）；沒有真實引言就整句不講，**不在真人版唸情境改寫句冒充原話**。
- S1 找不到：刪掉警方那句（`data-sources.md` 第 4 節），其他照講。
- S2 找到的話（警方有針對「假買家對賣家」的警示），用它換掉 S1 那句，更貼題：`Police have warned sellers about exactly this.`（依原文調整）。

**版本 B：台灣**

> In Taiwan, small sellers get this: "Your shop hasn't signed the payment guarantee. Verify here first." It looks like the platform. It isn't. And once the chat moves to LINE or Facebook, the platform's scam warnings can't follow.

- 選 B 時，格 ⑥ 一定要有東南亞的來源（S1 或 S6），避免被看成台灣本地題。

### 格 ②　RepSafe 是什麼（0:20–0:28）

> This is RepSafe. Paste the chat. It flags the risky lines and writes a reply you can copy and send.

### 格 ③　Demo：改字網域釣魚（0:28–1:30）

| 時間 | 講稿 |
|---|---|
| 0:28–0:38 | *The seller copies the whole chat, pastes it in, and taps one button.* |
| 0:38–0:52 | *Code runs two checks on every link: Google Web Risk, and a look-alike domain check. The AI can't skip them. Then Gemini reads the whole message, with those results as trusted facts.* |
| 0:52–1:05 | *Red card. Scam red flags found.*（停頓，讓評審看畫面） |
| 1:05–1:30 | *Look at the link. It's not shopee dot t-w. It only borrows the name. And "your shop hasn't signed the payment guarantee" is a known scam script* `[待驗證 S4／S5]`*. Every red flag shows the exact line, the reason, and which check caught it.* |

- 現場 demo 時照實等結果，不要趕；等超過 10 秒就補一句 `This is live, not sped up.`
- 用 Demo-EN（Carousell）時，把 `shopee dot t-w` 換成 `carousell`，把話術那句換成 `"verify your account for buyer protection"`。

### 格 ④　複製安全回覆（1:30–1:55）

> Now the part sellers actually need: what to say back. One tap to copy. A polite reply that keeps the deal inside the platform. Links, numbers and account IDs are stripped out by code, not just by the prompt.

### 格 ⑤　不亂報警、不被操控（1:55–2:25）

> A real buyer, with a real Shopee link. No alarm. And it never says "safe". It says no red flags found, and keep the payment on the platform.
>
> Some scammers now write to the AI itself: "ignore previous instructions". RepSafe flags that too, because the verdict comes from code, not from the message.

### 格 ⑥　數字、差異化、收尾（2:25–3:00）

> We tested it on thirty-three messages we wrote before tuning, and on real seller cases we never tuned on. `{x}` of twenty scams caught, `{y}` false alarms on ten real buyers, `{z}` of three injections blocked.
>
> Consumers already have scam-call apps. Sellers had nothing. RepSafe is free for sellers. Later, marketplaces and payment providers can license it as an API.
>
> We're on the seller's side, we work with any chat app, and we stop the scam ten seconds before the reply. Reply safe. Keep your rep.

- 評測數字**照實講**，沒達標的也講（例：`two false alarms, which we're still working on`）。
- 盲測筆數太少時補一句 `small sample`，不要省略。
- 有賣家授權的匿名原話 `[待訪談]` 時，可以換掉「Consumers already have…」那兩句：`One seller told us: "[原話]."`
- 超時時**先砍商業模式那兩句**（影片版本來就沒有）。

## 3. 競品與常見質疑：一句話回應

原則：尊重對方、講互補，不說別人不好。對方功能的描述**只照對方官網自己的說法**，細節待查證（`data-sources.md` S9）。評審席可能有人和這些單位有合作。

| 被問到 | English（一句話） | 中文對照 |
|---|---|---|
| **Whoscall** | Whoscall protects people from scam calls and texts. RepSafe works inside the buyer chat a seller is already in, and gives them the words to reply. | Whoscall 幫大家擋詐騙電話和簡訊；RepSafe 用在賣家正在回的那段買家對話裡，還直接給他可以回的話。 |
| **Gogolook** | Gogolook builds anti-scam data at scale `[待驗證 S9]`. We're a small tool on the seller's side, so a scam-data provider like them is a potential partner, not a rival. | Gogolook 做的是大規模的防詐資料；我們是站在賣家這邊的小工具，像他們這樣的資料商比較像未來的合作夥伴，不是對手。 |
| **ScamShield** | ScamShield helps the public block and check scam calls and messages `[待驗證 S9]`. RepSafe covers a different moment: a seller about to reply to a buyer, on any marketplace. | ScamShield 幫民眾擋下、查詢詐騙電話與訊息；RepSafe 管的是另一個時刻：賣家正要回買家訊息的那一刻，不限平台。 |
| **平台站內警告** | Marketplaces warn inside their own chat, and scammers know it, so they move the chat out. RepSafe works on any text a seller pastes, from any app. | 平台只在自己的聊天室跳警告，詐騙集團知道，所以把人帶出去；RepSafe 看的是賣家貼進來的任何文字，哪個 App 來的都行。 |
| 「直接問 Gemini／ChatGPT 不就好了？」 | A chatbot can be talked out of it by the scam message itself. Our link checks run in code on every link, the verdict comes from code, and the reply is filtered for links and IDs. | 一般聊天機器人可能被詐騙訊息本身操控；我們的連結檢查由程式對每個連結強制執行，判定由程式決定，回覆也會被程式過濾掉連結和帳號。 |
| 「網址查不到就代表安全嗎？」 | No, and we never say "safe". New phishing domains often aren't listed yet, so the best we say is "no red flags found", and we still tell you to pay on the platform. | 不代表，而且我們從來不說「安全」。新註冊的釣魚網域常常還沒被收錄，所以最多只說「未發現紅旗」，並提醒走平台內付款。 |
| 「誰付錢？」 | Free for individual sellers. Longer term, marketplaces and payment providers license it as an API. Right now we're only validating whether sellers would pay a small monthly fee `[待訪談]`. | 個人賣家免費；長期把 API 授權給開店平台與金流商。現階段只驗證賣家願不願每月付一點小錢。 |
| 「為什麼不賣給銀行？」 | Bank sales cycles and compliance are too heavy for a team our size today. Marketplaces and payment providers feel this pain first. | 銀行的銷售週期和合規成本，以我們現在的規模扛不起；最先痛的是開店平台和金流商。 |

「誰付錢？」那一題：訪談若有數字，只講「幾位裡有幾位願付」這種事實；價格只能照第 7 節、兩項輸入都到齊後以**區間**講，不講單一價格（樣本太小，`seller-outreach.md` 第 7.3 節）。

## 4. 和分鏡旁白的差異（給 Dana 決定）

| 格 | 分鏡旁白 | 本稿 | 建議 |
|---|---|---|---|
| ① A | `second-hand sellers get messages like this every day` | 拿掉 `every day` | `every day` 是頻率宣稱，目前沒有來源（`data-sources.md` 第 4 節），建議影片也拿掉 |
| ① A／B | `once the chat moves to another app` | 點名 WhatsApp、LINE、Facebook | 和 pitch 第 1 句一致；可選 |
| ③ | `marketplaces never ask sellers to verify through a link` | `is a known scam script` | 絕對說法要有平台官方原文（S5）；找不到就用本稿說法 |
| ⑥ | 無商業模式句 | 有 | 只放真人版；影片不用加 |

## 5. 紅線（講稿、影片、Q&A 都適用）

- 不說 "detect fake screenshots"、"verify payment proof"、"fake transfer"（`ui-spec.md` 第 3 節）。
- 不把 "safe" 當判定講；"safe reply" 指的是回覆本身可以用。
- 不說 "guaranteed"、"100% accurate"、"catches every scam"。
- 不說 "function calling"；統一說 "tools enforced by code"。
- 沒有來源的數字不講；賣家原話沒有引用授權不講；價格只在第 7 節區間定案後、於 Q&A 或真人版講，影片不放價格。
- 不說「賣給銀行」（會議已收回這個講法）。
- 畫面上不放平台 logo；口頭可以講平台名稱。

## 6. 排練清單

- [ ] 老闆已拍板開場 A 或 B（9/30），講稿格 ① 只留選定版本。
- [ ] 所有 `{x}` 換成最後一次評測的數字；所有 `[待驗證 S#]` 換成有來源的句子，或改用備用句。
- [ ] `ten seconds` 只在熱機 P90 ≤ 10 秒時講。
- [ ] 計時完整跑三次，每次 ≤ 3:00；超時先砍格 ⑥ 商業模式句。
- [ ] 現場 demo 前打一次 `/health` 暖機；頁首沒有 `Offline test mode` 提示條。
- [ ] 第 3 節的競品回應，對照 S9 官網說法確認過一次。
- [ ] 第 7 節定價區間兩項輸入都到齊才講；任一項待估算，就用第 7.4 節的「還在驗證」講法。
- [ ] 第 8 節 FAQ 所有 `{…}`、`[待訪談]`、`[待驗證]` 都已填好或換成備用答案。

## 7. 定價區間（預留，數字全部待估算）

- 時程：Felix **10/1** 交單次分析成本下限（`docs/finance/budget.md`）→ Sandy **10/2** 寫區間 → **10/3** 定稿給 Dana 對語氣。
- 用途：只用在真人版 Q&A 和本文件第 8 節「誰付錢」類題目；**影片不放價格**。
- 商業模式不變：個人賣家有免費版；長期是平台與金流商的 API 授權。這裡的區間只回答「如果個人賣家要付費，大概落在哪」。

### 7.1 兩項輸入

| # | 輸入 | 來源 | 誰給 | 期限 | 目前 |
|---|---|---|---|---|---|
| 1 | 單次分析成本下限（含截圖讀字的那一次呼叫另算） | 33 則評測紀錄的 token 數，取平均與最大值 | Felix | 10/1 | 待估算 |
| 2 | 每月願付（願意試的界線、直接拒絕的界線） | 訪談匿名彙總（`seller-outreach.md` 第 7.3 節） | Sandy | 9/30 | 待訪談 |
| 輔 | 每位賣家每月大約會檢查幾次 | 訪談「最近一個月被找上次數」 | Sandy | 9/30 | 待訪談 |

### 7.2 怎麼算（方法先定，數字之後填）

- **下限（成本面）**＝單次成本下限 ×每月檢查次數 ×（1＋緩衝）。緩衝比例由 Felix 定，待估算。
- **上限（客戶面）**＝受訪者「願意試的界線」，照原幣分開列（SGD、TWD 不互相換算）。
- 下限 ≤ 上限：區間成立，寫成「每月 {下限}–{上限} {幣別}」。
- 下限 > 上限，或願付的人少於一半：**個人付費不成立**，Q&A 只講「個人免費、平台與金流商授權」，不硬給價格。

### 7.3 區間表（10/2 填）

| 市場 | 成本下限／月 | 願意試的界線 | 直接拒絕的界線 | 區間 | 樣本 |
|---|---|---|---|---|---|
| 新加坡（SGD） | 待估算 | 待訪談 | 待訪談 | 待估算 | ___ 位 |
| 台灣（TWD） | 待估算 | 待訪談 | 待訪談 | 待估算 | ___ 位 |

### 7.4 講法（English，Q&A 用）

- 區間成立時：`Individual sellers get a free tier. In interviews, {M} of {N} sellers said they'd try a paid plan at around {range} a month, and that's above our cost per check. Small sample, so we treat it as a direction, not a price.`
- 還在驗證（任一輸入待估算，或區間不成立）：`Individual sellers get a free tier. We're still validating whether sellers would pay a small monthly fee; the longer-term model is licensing to marketplaces and payment providers.`

## 8. 評審 FAQ 草稿（10/3 定稿）

規則：答案**不能編造數字**。`{x}` 類只能填 Quinn 最後一次評測結果檔；`[待訪談]` 只能填匿名彙總；`[待驗證 S#]` 照 `data-sources.md`。沒有數字時用「備用答案」。第 3 節已有的競品題不重複。

| # | 評審可能問 | 回答（English） | 數字從哪來／沒有數字時 |
|---|---|---|---|
| 1 | How accurate is it? | `On thirty-three messages we wrote before tuning: {x} of 20 scams caught, {y} false alarms on 10 real buyers, {z} of 3 injections blocked. On real seller cases we never tuned on: {k} of {m}. Small sample.` | `docs/qa/test-plan.md` 評測結果檔。沒跑完就說 `We're running the evaluation now`，不給估計值 |
| 2 | What if it flags a real buyer? | `That's the error we watch most, because a rude reply loses a sale. In our test it happened {y} times out of 10. And for clean messages we never say "safe"; we say no red flags found and keep payment on the platform.` | 同上 `{y}` |
| 3 | What happens to the chats and screenshots sellers paste in? | `We never open the links, and we don't save the messages. The screenshot preview stays on the seller's device; only the text goes to Gemini for the check.` | 依據 `ui-spec.md` 隱私小字與 `architecture.md` 第 5 節；上線前請 Eddie 確認仍成立 |
| 4 | What if Gemini or Web Risk is down? | `It shows a grey "Can't determine" card and asks the seller to try again. It never falls back to "no red flags".` | 灰卡備用錄影（`storyboard.md` 格⑤備註）；Quinn 降級實測 |
| 5 | Can scammers trick the AI itself? | `They try. Messages like "ignore previous instructions" are flagged by an injection guard in code, and the verdict is set by code, not by the message. In our test, {z} of 3 injection attempts were blocked.` | `{z}` 來自評測 |
| 6 | How much does one check cost you? | `About {cost} per check at current Gemini pricing, measured from our evaluation logs.` | Felix 10/1 的成本下限。沒有時：`We're measuring it from our evaluation logs; it's capped by a fixed budget and an hourly limit.` |
| 7 | Do sellers actually want this? Would they pay? | `We talked to {N} sellers. {M} had lost money or time to a fake buyer, and {P} said they'd try a paid plan.` 可加一句有授權的原話 | `[待訪談]` 匿名彙總（`data-sources.md` 9/30 更新）。沒有訪談結果時：`We're interviewing sellers now; so far the evidence is the scam scripts themselves.`，不說「很多賣家說」 |
| 8 | How do you reach sellers? | `Seller groups and communities where these scams are already being shared, then marketplaces and payment providers who want fewer disputes.` | 不需要數字；不講用戶數、下載數等還沒有的數字 |

- 第 1、2、5 題的數字要和影片格⑥字卡**逐字一致**（Quinn 10/5 對）。
- 第 3 題如果 Eddie 的實作有變（例如開始記訊息內容），這題要改，並通知 Dana 改隱私小字。
