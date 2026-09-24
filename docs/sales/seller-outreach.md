# 賣家案例徵集計畫（9/25–9/29）

- 建立：2026-09-24，Sandy（業務）
- 依據：`docs/meetings/2026-09-24-電商客服反詐騙.md`、`docs/prd.md`（第 8、9、11 節）、`docs/roadmap.md`（停損點②）、`docs/design/storyboard.md`（鐵則 1–3）、`docs/engineering/architecture.md`（第 5 節）
- 這份是**草稿**：貼文、同意書都由老闆本人修改後自己發、自己收。`[ ]` 內換成實際資訊。
- **這份文件會放上公開 GitHub**：這裡只放範本，不寫任何真實的賣家姓名、帳號、截圖或釣魚網址。真實資料只放在已被 git 忽略的資料夾（見第 4 節「存放位置」）。

## 0. 目標與規則

| 項目 | 內容 |
|---|---|
| 目的 | ①過停損點②：9/29 晚上盤點 **≥ 3 則**合格真實案例 ②驗證「賣家願不願每月付小錢」 ③決定 9/30 開場／demo 用新加坡還是台灣（`docs/prd.md` Q6） |
| 目標 | 合格案例 ≥ 3 則（最低）；訪談 ≥ 3 位（含「每月願付多少」）；至少 1 則新加坡／Carousell 或 Shopee SG 案例（評審在新加坡） |
| 工時 | 找賣家配額 **3 小時**是 Paula 的提案（`docs/prd.md` 第 11 節，待老闆拍板）。發文、私訊、訪談、收同意書、打碼全部記在 `docs/finance/timesheet.csv` 的「找賣家」類 |
| 真實案例用途 | 只當 Quinn 的**盲測**，不拿來調 prompt，也不寫進 `app/prompt.py`（`docs/prd.md` 第 9 節）；經同意可用在比賽影片 |

**「合格案例」的定義**（Sandy 提案，待老闆確認；9/29 盤點照這個算）：

1. 是賣家**本人實際收到**的假買家訊息（截圖或賣家自己貼出的文字都算）；
2. 有**書面同意**（簽名檔、表單回覆，或對方用文字訊息逐字回覆同意內容，都要截圖存證）；
3. **已打碼**並存進 `data/real_cases/`，原圖已刪；
4. 內容至少有一個紅旗：連結、要求站外付款、要求驗證或提供帳密／驗證碼。

Reddit 等公開貼文**本身不算**：公開貼出不等於同意我們使用。要私訊原 PO 取得同意後才算。沒取得同意的公開貼文只能拿來「理解手法」，不能複製內容進任何資料夾。

**安全提醒（老闆本人）**：收到的截圖或文字裡的連結**絕對不要點**，也不要貼到瀏覽器「看一下」。只看、只存檔。

## 1. 五天時程

| 日期 | 做什麼 | 管道 | 預計時間 |
|---|---|---|---|
| 9/25（五） | 朋友接力：傳 LINE 給 5–10 位有開賣場的朋友 | 朋友 | 20 分 |
| 9/25（五） | 查 FB 社團、Dcard 版、r/singapore 的版規；需要先問管理員的先私訊 | FB／Dcard／Reddit | 20 分 |
| 9/26（六） | 版規允許的地方發徵集貼文 | FB／Dcard／Reddit | 20 分 |
| 9/26–9/28 | 回覆私訊、傳同意書、約 20 分鐘訪談（至少 3 場） | 全部 | 訪談 3 × 20 分＋收同意書 |
| 收到當天 | 打碼 → 存檔 → 刪原圖 → 填盤點表 | — | 每則約 5–10 分（待記帳驗證） |
| 9/28（一） | 跟進：3 天沒回的再傳一次（第 2.6 節） | 全部 | 10 分 |
| **9/29（二）晚** | **盤點**（第 7 節），不到 3 則就照停損點②停 | — | 15 分 |

上面的「預計時間」是配額分配，不是實測；總和要守在 3 小時內，實際花多少以工時記帳為準。

**優先順序**：朋友接力（回覆率最高、同意最好拿）> FB 賣家社團 > Dcard > Reddit。前兩天朋友接力就湊到 3 則的話，後面的管道改成只找新加坡案例。

## 2. 徵集貼文範本

共同原則：

- **講清楚用途**：比賽原型、只用來測試與比賽影片、會打碼、可以撤回。
- **不要叫對方把連結直接傳給我們**：請對方傳**截圖**，或把訊息文字貼過來；我們不會點。
- **不承諾任何事**：不說「保證不被騙」「幫你抓詐騙」，只說「在做一個回覆前先檢查的小工具」。
- 不提供金錢報酬（Felix：成本 0 原則）。可以提供的回饋：原型好了先給他試用、把測試結果摘要傳給他。

### 2.1 朋友接力（LINE，中文）

> 嗨[名字]，想請你幫個小忙！
> 我在做一個給網拍賣家用的小工具：收到「買家」訊息時，先貼進去檢查有沒有釣魚連結或詐騙話術，再給一段可以直接回的話。要拿去參加 Google Cloud 贊助的 AI 比賽。
> 想問你開賣場以來，有沒有收過那種「你的賣場沒簽署金流保障，點這裡認證」或是要你去 LINE 私下付款的假買家訊息？
> 如果有，可以傳截圖給我嗎？我會先把名字、帳號、電話全部塗掉，只用在測試和比賽影片，你隨時可以叫我刪掉。我會另外傳一段同意說明給你確認。
> 也想約你 15–20 分鐘聊一下你平常怎麼判斷假買家。
> 另外，你身邊如果有其他開賣場的朋友，可以幫我問問嗎？謝謝！

### 2.2 FB 蝦皮／露天賣家社團（中文）

**先私訊管理員**（版規沒寫清楚能不能徵集時）：

> 管理員您好，我是[老闆名字]。我在做一個幫網拍賣家「回覆前先檢查假買家訊息」的小工具（比賽用的原型，不收費、不賣東西）。想在社團發一篇徵集：請遇過假買家詐騙訊息的賣家提供打碼截圖。不知道社團規定是否允許？不行的話完全理解，謝謝您。

**社團貼文**：

> 【徵求】遇過「假買家」詐騙訊息的賣家，想請你分享截圖（會打碼）
>
> 大家好，我是[老闆名字]，在做一個給小賣家用的工具：收到買家訊息時先貼進去，幫你看有沒有釣魚連結、假冒蝦皮／露天的網址，或叫你去站外付款的話術，再給一段可以直接回的訊息。這是參加 Google Cloud 贊助 AI 比賽的原型，**不收費、不推銷**。
>
> 想徵求：
> - 你實際收到過的假買家訊息截圖（例如「賣場未簽署金流保障」「請先點連結認證才能收款」「加 LINE 私下轉帳」）
> - 願意的話，15–20 分鐘線上聊聊你平常怎麼判斷
>
> 我會做到：
> - 名字、頭像、帳號、電話、賣場名稱、訂單編號**全部塗掉**才使用
> - 只用在測試和比賽影片，不公開原圖，不放上網路
> - 你隨時可以叫我刪除
>
> 有意願請留言「+1」或私訊我，我再傳同意說明給你確認。**請不要把連結直接貼在留言**，截圖就好。謝謝大家！

### 2.3 Dcard 網拍相關看板（中文）

先看版規：禁止徵求、問卷或私訊引流的看板**就不發**，不要硬發。允許的話：

> 標題：[徵求] 網拍賣家：你收過最像真的「假買家」訊息長怎樣？
>
> 想請教有在蝦皮、露天賣東西的卡友：有沒有收過假買家丟「金流保障認證」「賣場未簽署」之類的連結，或要你去 LINE 私下轉帳？
>
> 我在做一個幫賣家「回覆前先檢查」的小工具，要參加 Google Cloud 贊助的 AI 比賽（不收費、不推銷）。如果你願意提供**打碼後**的截圖讓我測試，我會再把個資塗乾淨一次，只用在測試和比賽影片，隨時可以要求刪除。
>
> 不想提供截圖也沒關係，留言分享你怎麼識破的也很有幫助。請不要在留言貼連結。

### 2.4 Reddit r/singapore（English）

Read the subreddit rules first. If self-promotion, surveys or requests are not allowed, **don't post**; message the moderators first, or skip Reddit. Alternative: search existing public posts about Carousell or Shopee buyer scams and send the original poster the private message in 2.5.

> **Title:** Sellers on Carousell / Shopee SG: have you received a "buyer" message with a fake verification link?
>
> Hi all. I'm building a small tool for online sellers: before you reply to a buyer, you paste their message in, it flags phishing links, look-alike marketplace domains and "pay me outside the app" scripts, and gives you a reply you can copy and send. It's a prototype for an AI competition sponsored by Google Cloud. Nothing to sell, and it's free.
>
> I'm looking for sellers who'd share a **screenshot of a real scam message** they received (for example "verify your account for buyer protection" or "click here to receive payment").
>
> - I'll black out names, profile photos, usernames, phone numbers and order numbers before using it.
> - It's only used to test the tool and, with your OK, in the competition video. The original never goes online.
> - You can ask me to delete it at any time.
>
> Comment or DM me if you're open to it, and I'll send a short consent note. **Please don't paste the scam link itself here.** Thanks!

### 2.5 私訊公開貼文的原 PO（English／中文）

> Hi, I saw your post about the fake buyer on [Carousell / Shopee]. Sorry that happened. I'm building a free prototype that helps sellers check a buyer's message before replying, for a Google Cloud-sponsored AI competition. Would you be OK with me using your screenshot, with every name, username and number blacked out, to test it and possibly show it in the competition video? You can say no, or ask me to delete it later. I'd send you a short consent note first.

> 你好，看到你分享遇到假買家的文章，辛苦了。我在做一個幫賣家回覆前先檢查買家訊息的免費原型，要參加 Google Cloud 贊助的 AI 比賽。想問能不能用你的截圖（名字、帳號、數字全部塗掉）來測試，也可能放進比賽影片？不方便也完全沒關係，之後也可以隨時要我刪除。同意的話我會先傳一段同意說明給你確認。

### 2.6 跟進（3 天沒回，只追一次）

> 中文：嗨，再打擾一次～如果你沒收過這類訊息也沒關係，回我一聲就好；或是你身邊有開賣場、可能遇過的朋友，可以幫我轉問嗎？謝謝！
>
> English: Hi, just a quick follow-up. No worries if you haven't had one of these messages. If you know another seller who might have, I'd be grateful if you could pass this on. Thanks!

## 3. 書面同意書範本

使用方式：先把整段文字傳給對方，請對方**逐字回覆「我同意」加上勾選結果**（或用表單、簽名檔）。對方的回覆截圖就是書面同意，存進 `data/private/consent/`（已被 git 忽略）。**同意書原件不放進公開 repo。**

> 這份範本不是法律意見。涉及台灣《個人資料保護法》或新加坡 PDPA 的細節，待老闆確認；有疑慮時一律以「不使用」處理。

### 3.1 中文版

> **RepSafe 真實案例使用同意書**
>
> 提供者稱呼：[　　]　聯絡方式：[　　]　日期：2026/[　]/[　]
> 提供內容：截圖／文字共 [　] 則（說明：[例：9 月收到的假買家訊息]）
>
> 1. **內容說明**：我是[老闆名字]，正在開發原型工具 RepSafe，參加 AI Builder Cup 2026（Google Cloud 贊助）。
> 2. **授權用途**（請勾選，可只勾一部分）：
>    - [ ] A. 內部評測：用來測試工具能不能認出詐騙訊息。測試時，打碼後的文字會送到 Google Cloud 的 Gemini 服務分析。
>    - [ ] B. 比賽影片與簡報：打碼後出現在 3 分鐘比賽影片、評審簡報中（影片會公開在比賽平台或影音網站）。
>    - [ ] C. 引用我的說法：[ ] 匿名（例：「台灣蝦皮賣家」）　[ ] 不引用
> 3. **打碼承諾**：使用前會用實心色塊塗掉雙方的姓名／暱稱、頭像、帳號、電話、email、銀行帳號、地址、訂單編號、賣場名稱，以及可辨識的商品照片。影片中的詐騙連結會改成假的示範網址。打碼後的版本會先傳給你看，你同意後才使用。
> 4. **不會做的事**：不公開未打碼的原圖、不放進公開的程式碼庫、不轉賣或提供給其他人、不拿來做廣告。
> 5. **保存期限**：比賽結束後刪除，最晚 [2026-12-31]（待老闆確認）。
> 6. **隨時撤回**：你可以隨時傳訊息要求撤回，我會在 7 天內刪除檔案，之後不再使用。**限制說明**：已經送出給主辦的比賽影片可能無法撤回，但我會盡力替換或下架我能控制的版本。
> 7. **確認事項**：我已年滿 18 歲；這些訊息是我本人收到的；我有權提供。
>
> 同意請回覆：「我同意，授權 A／B／C（寫出你勾的項目）」。

### 3.2 English version

> **RepSafe: Consent to use a real scam case**
>
> Name you'd like me to use: [　　]　Contact: [　　]　Date: [　　]
> What you're sharing: [ ] screenshot(s) / text, [n] item(s)
>
> 1. **About**: I'm [Your name], building a prototype called RepSafe for AI Builder Cup 2026 (sponsored by Google Cloud).
> 2. **What I may use it for** (tick any):
>    - [ ] A. Internal testing, to check whether the tool recognises scam messages. During testing, the redacted text is sent to Google Cloud's Gemini service for analysis.
>    - [ ] B. The competition video and slides, redacted. The video will be public on the competition platform or a video site.
>    - [ ] C. Quoting what you told me: [ ] anonymously (e.g. "a Carousell seller in Singapore") [ ] don't quote me
> 3. **Redaction**: before any use, I'll cover with solid blocks the names, profile photos, usernames, phone numbers, emails, bank accounts, addresses, order numbers and shop names of both sides, plus any identifiable product photos. Scam links shown in the video will be replaced with a fake demo address. I'll send you the redacted version and only use it after you OK it.
> 4. **What I won't do**: publish the unredacted original, put it in a public code repository, sell or pass it to anyone else, or use it in advertising.
> 5. **How long I keep it**: deleted after the competition, by [2026-12-31] at the latest (to be confirmed).
> 6. **You can withdraw at any time**: message me and I'll delete the files within 7 days and stop using them. **Limit**: a video already submitted to the organiser may not be withdrawable, but I'll replace or remove any copy I control.
> 7. **You confirm**: you're 18 or older, you received these messages yourself, and you're free to share them.
>
> To agree, reply: "I agree to uses A / B / C" (list the ones you ticked).

## 4. 打碼規則

| # | 規則 |
|---|---|
| 1 | **一律用不透明的實心色塊**塗滿。不用馬賽克、模糊、半透明螢光筆（有機會被還原）。 |
| 2 | **雙方都要打碼**：賣家這邊的名字、頭像、賣場名稱；詐騙那邊的暱稱、頭像、帳號、電話（詐騙帳號可能是被盜用的真人帳號）。 |
| 3 | 必塗項目：姓名／暱稱、頭像、帳號／ID、電話、email、銀行或電子錢包帳號、地址、訂單編號、賣場名稱、可辨識的商品照片、手機狀態列的通知內容。 |
| 4 | **平台 logo、App 標題列、商標配色**：入庫的檔案可以保留（盲測要用）；**放進影片前要裁掉**，只留訊息泡泡（`docs/design/storyboard.md` 鐵則 1）。請 Dana 剪輯時再檢查一次。 |
| 5 | **釣魚網址**：入庫的檔案保留原字（盲測要用），但**任何公開文件、issue、commit 訊息都不能寫出真的釣魚網址**；影片裡一律換成 `.example` 示範網域（storyboard 鐵則 3）。 |
| 6 | 打碼後**另存新檔**（重新輸出成 PNG，順便去掉 EXIF 等中繼資料），**刪除原圖**，也清掉手機相簿與通訊軟體裡的原圖。 |
| 7 | 打碼版先傳給提供者確認，對方同意後才用在影片（同意書第 3 條）。 |
| 8 | 檔名不含任何人名：`case-01-tw-text.png`、`case-02-sg-img.png`（編號－地區－格式）。 |

**存放位置**

| 內容 | 放哪裡 | 會進 git 嗎 |
|---|---|---|
| 打碼後的截圖、文字 | `data/real_cases/` | 不會（已被 `.gitignore` 排除） |
| 同意書回覆截圖、提供者聯絡方式 | `data/private/consent/` | 不會（已被排除） |
| 盤點表（第 7 節）填好的版本 | `data/private/inventory.md` | 不會；公開 repo 只保留這份空白格式 |
| 訪談紀錄 | `data/private/interviews/` | 不會 |

每次 commit 前用 `git status` 確認 `data/` 底下沒有任何檔案被加進去。

## 5. 20 分鐘訪談題目

- 原則：問「**最近一次**」的真實經驗，不問「一般來說」；不 demo、不推銷，對方講、我們記。
- 可以線上、電話、或直接用文字訊息來回（很多賣家忙，文字版也可以）。
- 時間不夠時的優先順序：**付費題（第 5 段）> 最近一次經驗（第 2 段）> 同意與引用確認 > 其他**。

| 段落 | 時間 | 必拿到 |
|---|---|---|
| 0. 開場 | 1 分 | 錄音／引用同意 |
| 1. 暖身 | 2 分 | 平台、規模、用什麼回訊息 |
| 2. 最近一次假買家 | 5 分 | 經過、損失、一句原話 |
| 3. 現在怎麼判斷 | 3 分 | 現有做法、用過哪些工具 |
| 4. 聽概念 | 3 分 | 最想要哪一塊、最怕什麼 |
| 5. 付費 | 4 分 | **每月願付多少**、界線 |
| 6. 收尾 | 2 分 | 案例同意書、引用、轉介 |

### 0. 開場（1 分）

> 「謝謝你撥 20 分鐘。我在做一個幫賣家『回覆前先檢查買家訊息』的小工具，還在原型階段，要參加 Google Cloud 贊助的 AI 比賽。今天不推銷，只想聽你的實際經驗。你的賣場名稱、帳號都不會公開。
> 兩件事想先問：一、可以錄音方便我整理嗎？二、如果你講到很有感的一句話，我能不能匿名引用在比賽影片裡？最後我會再跟你確認一次。」

### 1. 暖身（2 分）

1. 「你在哪些平台賣？蝦皮、露天、Carousell、還是自己的 FB／IG？賣多久了？」
2. 「一個月大概幾張訂單？一個人顧還是有幫手？」
3. 「平常用什麼回買家？平台聊天、LINE、手機還是電腦？」

### 2. 最近一次假買家（5 分）— 目標：一句原話

1. 「最近一次遇到『怪怪的買家』是什麼時候？可以從第一則訊息講起嗎？」
2. 「你是在哪一步覺得不對勁的？還是事後才發現？」
3. 「有沒有點連結、照著做、或損失錢／帳號？損失大概多少？」（對方不想講就跳過）
4. 「後來有做什麼嗎？報 165／警方、找平台客服、在社團發文提醒？」
5. 「一個月大概會遇到幾次這種訊息？」（問最近一個月，不問平均）

追問：對方講到情緒字眼（「嚇死」「每次都」「差點」）時停下來：「你剛說『○○』，可以多講一點嗎？」**逐字記下**原話，不改寫。

### 3. 現在怎麼判斷（3 分）

1. 「現在收到可疑訊息，你怎麼判斷？看網址、問朋友、上社團問、還是直接不理？」
2. 「平台聊天裡有跳過防詐提醒嗎？對方把你帶去 LINE 之後呢？」
3. 「有用過 Whoscall、165 查詢或其他防詐工具嗎？有幫到賣家這種情況嗎？」
4. 「有沒有因為太小心、回太兇，結果嚇跑真買家的經驗？」（驗證「誤報會得罪真買家」這個痛點）

### 4. 聽概念（3 分，只講一句，不 demo）

> 「想像一下：收到買家訊息時，你先把對話貼進一個網頁，10 秒內它告訴你哪幾句有問題、為什麼，然後給你一段可以直接複製回給對方的話。」

1. 「這三塊——告訴你有沒有問題、標出哪一句、給你一段回覆——你最想要哪一塊？哪一塊用不到？」
2. 「用這種東西，你最擔心什麼？（判錯、得罪客人、要多一個步驟、資料安全）」
3. 「如果它說『沒發現問題，但付款前請走平台流程』，你會怎麼理解？」（驗證琥珀卡文案會不會被誤讀成「安全」）

### 5. 付費（4 分）— **每月願付多少**

先問現況錨點，再問願付：

1. 「你現在有每月付錢的賣家工具嗎？（例如出貨、記帳、廣告、美圖 App）大概每月多少？」
2. **開放式**：「如果這個工具真的能幫你擋掉一次詐騙，你覺得**每月**付多少是合理的？」先讓對方講數字，**不要先報價**。
3. 對方說不出來時，用選項夾出界線（錨點只是問法，**不是建議價**）：
   - 台灣：「每月 NT$30、NT$99、NT$299，哪個你會願意試？哪個你會直接說太貴？」
   - 新加坡：「S$2, S$5 or S$15 a month: which would you try, and which is too much?」
4. 「你比較想要『每月訂閱』、『用一次付一次』，還是只想用免費版？」
5. **行動測試**（比嘴巴說願付更準）：「10 月中原型做好時，你願意留 LINE／email 讓我通知你試用、並給 5 分鐘回饋嗎？」

記錄方式：記下**原話＋數字**、「願意試」與「直接拒絕」兩條界線、是否願意留聯絡方式。外幣照原幣記，不換算。沒問到就寫「未問到」，pitch 一律寫「待驗證」。

### 6. 收尾（2 分）

1. **案例同意**：「剛剛提到的那則訊息，願意讓我拿截圖做測試嗎？我傳同意說明給你。」
2. **引用確認**：「你剛說『○○』，我可以匿名引用嗎？（例：台灣蝦皮賣家）還是不引用？」以這次的答案為準。
3. **轉介**：「還有沒有其他開賣場、可能遇過的朋友，你覺得我該問問？」
4. **隊友**（只在對方條件符合時問）：對方在電商或金流業**在職、年滿 21 歲、在 JAPAC**，而且有興趣時：「比賽要 2–4 人組隊，你會有興趣一起報名嗎？」隊友資格以主辦回覆為準（`docs/prd.md` Q4）。
5. 致謝，約定會後傳打碼後的截圖給對方確認。

## 6. 訪談紀錄表（每位一份，存 `data/private/interviews/`）

| 項目 | 內容 |
|---|---|
| 編號／日期／時長 | I-01／ ／ |
| 地區、平台 | TW／SG；蝦皮／露天／Carousell／Shopee SG／其他 |
| 規模 | 每月訂單約 ___ 張；一人／有幫手 |
| 回訊息的工具 | |
| 錄音 | 有／無 |
| 引用授權 | 匿名（寫出稱呼）／不引用 |
| 最近一次假買家經過 | |
| 損失 | 無／有（金額或帳號，對方願意講才記） |
| 最近一個月遇到次數 | |
| 痛點原話（逐字） | |
| 現有做法、用過的工具 | |
| 最想要的一塊 | 判定／標出句子／可回的話術 |
| 最大顧慮（原話） | |
| 琥珀卡文案理解 | 正確理解／誤以為安全 |
| 現有每月付費工具與金額 | |
| 開放式願付（原話＋數字） | |
| 願意試的界線／直接拒絕的界線 | |
| 付費偏好 | 月訂閱／按次／只用免費 |
| 行動測試：願意留聯絡方式試用 | 是／否 |
| 提供案例 | 是（對應 case 編號）／否 |
| 轉介名單 | 只寫人數，姓名記在私人筆記 |
| 隊友意願 | 有／無／不符資格 |

## 7. 9/29 晚上盤點表（格式）

填好的版本存 `data/private/inventory.md`，**不進公開 repo**。

### 7.1 案例清單

「手法」照 Quinn 的評測分類，方便對照盲測結果。

| case 編號 | 來源管道 | 地區 | 平台 | 格式 | 手法（可複選） | 同意書（日期） | 授權範圍 | 打碼完成 | 原圖已刪 | 提供者已確認打碼版 | 合格？ | demo 候選？ | 備註 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| case-01 | 朋友／FB／Dcard／Reddit | TW／SG | | 截圖／文字 | 釣魚連結／改字網域／短網址／站外付款／其他 | | A／B／C | 是／否 | 是／否 | 是／否 | 是／否 | 是／否 | |

### 7.2 停損判定

| 項目 | 結果 |
|---|---|
| 合格案例數（照第 0 節定義） | ___ 則 |
| **停損點②**：合格案例 ≥ 3？ | 過／**不過 → 停止開發** |
| 其中新加坡案例 | ___ 則 |
| 其中台灣**截圖**且授權 B（可上影片） | ___ 則 → 給老闆 9/30 決定開場 A／B、Demo-TW／Demo-EN |
| 盲測可用筆數（授權 A） | ___ 則 → 交給 Quinn |

不到 3 則的處理（`docs/roadmap.md`）：停止開發；已收集的案例和付費意願留作商業驗證，同意書的保存期限照舊，到期刪除。

### 7.3 付費意願彙整

| 訪談編號 | 地區 | 每月訂單 | 最近一個月被找上次數 | 開放式願付 | 願意試的界線 | 直接拒絕的界線 | 付費偏好 | 願意留聯絡方式 |
|---|---|---|---|---|---|---|---|---|
| I-01 | | | | | | | | |

總結寫三行就好：幾位受訪、幾位說願付（各多少、原幣）、幾位願意留聯絡方式。**樣本這麼小，只能當方向，不能當定價依據**；pitch 裡一律不放價格。

### 7.4 工時

| 項目 | 結果 |
|---|---|
| 「找賣家」累計工時 | ___ 小時（配額 3 小時，待老闆拍板） |
| 超過配額？ | 是 → 從哪個功能扣，照 `docs/prd.md` 第 11 節 |
