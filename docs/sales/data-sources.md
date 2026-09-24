# 公開數據來源清單（待查證）

- 建立：2026-09-24，Sandy（業務）
- 依據：`docs/meetings/2026-09-24-電商客服反詐騙.md`（分歧 4、主要風險 6）、`docs/design/storyboard.md`（格 ①、③、⑥ 的「待驗證」）、`docs/pitch/pitch-script.md`
- 回應 Dana：分鏡裡標「待驗證」的警方數字與社會效益數字，要找的來源都列在這裡（對照見第 2 節）。

## 0. 先講清楚

- **這份文件裡沒有任何數字。** 撰寫時沒辦法上網查證，所以每一項都是「待驗證」，只列出要找什麼、建議去哪個機構或報告找。
- 下面的報告名稱是「建議查找的方向」，**名稱本身也要查證**（機構可能改版或改名）。找不到就照第 4 節的備用說法處理，**不能用記憶或新聞轉述的數字頂替**。
- 誰查：老闆（Sandy 沒辦法上網）。建議配額 1 小時，工時記在哪一類請 Felix 定。
- 期限：**10/9 功能凍結前**找齊；找不到的在 10/10 錄影前一律刪句。

## 1. 使用規則

1. **只用一手來源**：政府機關、警方、平台官方說明、有方法說明的年度報告。新聞只能拿來找線索，要追到原始出處才能用。
2. **定義要對得上**：警方的「電商詐騙」「網購詐騙」大多是**買家**被騙；除非來源有拆出「賣家受害」，否則**不能說成「賣家損失了 X」**。字卡寫法要照來源原本的分類名稱（例：`E-commerce scams: {N} cases in {year}, source: {agency}`）。
3. 每個數字都要有：年份／期間、單位、幣別、來源機構、報告名稱、網址、查閱日期。
4. 片中字卡一律加小字來源，例：`Source: {agency}, {report}, {year}`。
5. 數字、pitch、評審 Q&A 三處用同一個版本，改一處就同步改三處。
6. 公開文件（這份會進 GitHub）只能寫公開來源的數字，不能寫訪談得來的私人數字。

## 2. 需要的數字清單

狀態欄一律是「待驗證」，找到後改成「已查證」並填第 3 節的紀錄表。

| ID | 要找的數字或事實 | 用在哪裡 | 建議查找的來源（名稱待確認） | 注意事項 | 狀態 |
|---|---|---|---|---|---|
| S1 | 新加坡**電商詐騙**的年度案件數與損失金額（最近一個完整年度，或最新半年） | 分鏡格 ① 版本 A 大字卡 `{SPF 數字}`；格 ⑥ 社會效益字卡 | Singapore Police Force（SPF）每年、每半年發布的詐騙與網路犯罪統計簡報（例如 Annual／Mid-Year Scams and Cybercrime Brief 之類的名稱）；SPF 新聞稿 | 「e-commerce scams」多半是買家受害；只寫案件數與損失總額，不說成賣家損失 | 待驗證 |
| S2 | 新加坡是否有官方警示提到「**假買家對賣家**丟釣魚連結」（例：假的收款、驗證、買家保障連結） | 格 ① 版本 A 旁白的佐證；評審 Q&A「賣家真的會被騙嗎」 | SPF 新聞稿或警示（Police advisory）；National Crime Prevention Council 的 ScamAlert.sg 手法說明 | 找到的話是開場最有力的一句，因為直接講賣家端；找不到就不要暗示「警方說過」 | 待驗證 |
| S3 | 台灣**網購相關詐騙**的受理件數與財損（假網拍、假買家等分類，看來源怎麼分） | 格 ⑥ 社會效益字卡（選版本 B 時特別需要）；pitch 格 ⑥ | 內政部警政署 165 全民防騙網（詐騙手法排行、統計專區、打詐儀表板之類的公開頁面）；內政部警政署警政統計通報 | 分類名稱照原文翻譯；「假網拍」是買家受害，不能拿來講賣家 | 待驗證 |
| S4 | 「**賣場未簽署金流保障／認證才能收款**」這類假買家手法的官方說明 | 格 ① 版本 B 旁白；格 ③ 旁白「is a script」的佐證 | 165 全民防騙網的手法說明或宣導；蝦皮台灣、露天拍賣官方公告或幫助中心的防詐頁面 | 只需要「官方有點名這個手法」，不一定要數字 | 待驗證 |
| S5 | 平台官方說明：**平台不會要求賣家透過連結驗證或簽署金流服務**；官方網域清單 | 格 ③ 旁白 `marketplaces never ask sellers to verify through a link`；網域白名單的說法 | Shopee 台灣、Shopee 新加坡、Carousell、露天的幫助中心（Help Centre）或安全中心頁面 | 這句在分鏡裡是**絕對說法**，找不到官方原文就要改句（第 4 節） | 待驗證 |
| S6 | 亞洲或東南亞的詐騙總損失（區域性，證明不是台灣本地題） | 格 ⑥ 社會效益字卡（備選）；評審 Q&A | Global Anti-Scam Alliance（GASA）的年度詐騙報告（例如 Global State of Scams 之類的名稱）；其亞洲區版本 | 這類報告常是問卷推估，字卡要寫清楚是「推估」與樣本來源；能用警方數字就優先用 S1／S3 | 待驗證 |
| S7 | 東南亞電商市場規模（GMV） | pitch 商業願景一句話（可不放）；評審 Q&A「市場多大」 | Google、Temasek、Bain & Company 合作的年度 e-Conomy SEA 報告 | Google 是賽事贊助方，引用這份報告很自然；只放一個數字 | 待驗證 |
| S8 | 平台賣家規模（Shopee、Carousell 的賣家或刊登數） | 評審 Q&A「目標客群有多少人」（不放影片） | Sea Limited 年報（美國 SEC 20-F）或季報；Carousell 官方新聞稿 | 公司揭露的定義常變，照原文寫 | 待驗證 |
| S9 | 競品功能的官方描述：Whoscall（Gogolook）、Gogolook 的企業／政府防詐服務、ScamShield | `docs/pitch/pitch-script.md` 第 3 節的競品回應 | Whoscall 與 Gogolook 官網；ScamShield 官網（新加坡政府相關單位推出，推出單位名稱待確認） | 只描述對方**自己宣稱**的功能，不評論好壞；評審席可能有人和這些單位有關係 | 待驗證 |
| S10 | 新加坡政府對電商平台的交易安全評等（如果有） | 評審 Q&A「平台自己不是已經在做了嗎」 | Ministry of Home Affairs（MHA）的電商平台交易安全評等（E-commerce Marketplace Transaction Safety Ratings 之類的名稱） | 備用，不放影片 | 待驗證 |

**優先順序**：S1 > S5 > S2 > S3 > S4 > 其他。S1、S5 直接影響影片旁白，錄影前一定要有結論（找到或刪句）。

## 3. 查證紀錄表（找到一筆填一列）

| ID | 數字／事實（照原文） | 年份／期間 | 單位、幣別 | 來源機構 | 報告或頁面名稱 | 網址 | 查閱日期 | 原文引述（一句） | 用在哪裡 | 查證人 |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | | | | | | | | | | |

- 公開網頁可以截圖存證，放 `data/private/sources/`（不進 git，避免版權疑慮）。
- 同一項有多個來源、數字不同時，兩個都記，用最新、最一手的那個，並在備註寫原因。

## 4. 找不到時的備用說法

| 分鏡位置 | 原本的句子 | 找不到來源時改成 |
|---|---|---|
| 格 ① 版本 A 大字卡與旁白（S1） | `{Police figure, source pending.}` | 刪掉數字句。Dana 已定：改成 `Scam reports like this are rising across the region.`，**但這句也需要來源**（S1 或 S6 任一有趨勢資料）；都沒有就刪句，畫面停 3 秒 |
| 格 ① 版本 A 旁白 | `second-hand sellers get messages like this every day` | **建議 Dana 改句**：`every day` 是頻率宣稱，目前沒有來源。改成 `second-hand sellers get messages like this.`；訪談若拿到賣家原話（例：一個月被找上幾次），可以改用匿名原話 |
| 格 ③ 旁白（S5） | `marketplaces never ask sellers to verify through a link` | 找到官方原文：改成照原文說，例 `Shopee's own help centre says it won't ask sellers to verify through a link.`（依實際原文）。找不到：改成 `It's a known scam script. Real buyers pay through the app.` |
| 格 ⑥ 社會效益字卡（S1／S3／S6） | `{東南亞／台灣 電商詐騙損失數字}` | 刪掉這一列字卡，只留 `Sellers have no fraud team. Scammers know that.` 與 `Works with any chat app. On the seller's side.` |
| pitch 市場規模（S7） | 市場規模一句話 | 不講市場規模，只講「個人賣家免費、長期授權給平台與金流商」 |

改句屬於 Dana 的分鏡文件，上表只是業務建議；**由 Dana 決定後改 `docs/design/storyboard.md`**。
