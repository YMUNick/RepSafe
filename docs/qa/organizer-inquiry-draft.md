# 寄給主辦的詢問信（RepSafe，草稿，尚未寄出）

- 擬稿：2026-09-24，Quinn（QA）
- 寄件人：老闆本人（用報名 AI Builder Cup 的信箱）
- 最晚寄出：**今天（9/24）**，最晚 9/26 前，才趕得上 9/30 停損點①（`docs/roadmap.md`）
- 收件人：官網 FAQ／Contact 頁面上的主辦聯絡信箱，或 Hack2skill 平台上的官方支援管道。**寄之前先到官網確認，不要用猜的地址。**

## 寄之前老闆要做的事

1. **和 LineSleuth 那封合併成一封。** 姊妹專案已經有一份草稿（`G:\claude\project\2026AIBUILDERCUP\docs\qa\organizer-inquiry-draft.md`）。如果那封還沒寄，請合併：把下面 A 段接在那封的 A 段後面，重複的題目（原型開到何時、組隊資格）只留一題。分兩封寄，主辦可能只回一封，也可能覺得我們在洗版。如果那封已經寄了，就寄這封，主旨註明是 follow-up。
2. 先把官網的 Rules／Terms／FAQ 全部看一遍，**官網已經寫清楚的題目就刪掉**，只問沒寫的，主辦比較願意回。
3. 填好 `[ ]` 裡的內容。
4. 回信存成 `docs/qa/organizer-reply-YYYY-MM-DD.md`，我會照回覆更新 test-plan 第 7 節（冷啟動）和第 10 節（截圖、影片）；Paula 更新 roadmap 停損點①；Felix 更新預算（原型要開多久、抵免額）。

語氣說明：信件刻意寫成是非題、編號排列，方便主辦逐條回覆；**不寫產品細節和詐騙手法**，避免被當成要求預審，也避免在信裡出現任何網址樣本。

## 回覆後怎麼決定（給老闆）

| 題號 | 回覆 | 我們怎麼做 |
|---|---|---|
| 1 | 不能交兩件 | **停損①成立，RepSafe 立刻停**，全部時間回 LineSleuth |
| 1 | 可以，但要不同團隊 | 看第 2 題；隊友找不到就停 |
| 2 | 隊友不能重疊 | 要另外找 1 位符合資格的隊友（Sandy 的名單）；9/30 前找不到就停 |
| 3 | 要開到 12/4 或評審期間隨時可開 | 冷啟動變成評審第一印象：Felix 重算最小實例 1 的費用，test-plan 第 7 節冷啟動改成有門檻 |
| 4 | 不能用 Web Risk | 改成只用網域比對（純程式），影片和 pitch 拿掉 Web Risk 字樣 |
| 5 | 不能放真實截圖 | 影片全部用合成訊息（Demo-TW／Demo-EN），真實案例只當盲測 |
| 6 | 不能附使用者引言 | 分鏡格①右側不放真實引言，改用標 `Scenario reenacted. Not a real quote.` 的情境改寫句或留白；訪談結果只用在 Q&A 口頭回答（`docs/pitch/pitch-script.md` 第 8 節） |
| 6 | 可以，有格式要求 | Sandy 照要求改盤點表的引言欄與同意書，Dana 照格式做字卡 |
| 沒回 | 9/30 還沒回 | 依 PRD Q8，老闆決定要不要繼續；建議先照「最嚴格的答案」準備（原型開到 12/4、影片不放真實截圖） |

---

**Subject:** AI Builder Cup 2026 – Questions on multiple submissions, prototype hosting, third-party APIs and user evidence

Dear AI Builder Cup 2026 Organizing Team,

My name is [Full name]. I am registered for AI Builder Cup 2026 ([registered email]) and I am based in [Country/City]. I would be grateful if you could clarify a few points that I could not find in the official rules and FAQ. Short yes/no answers would already help a lot.

**A. Multiple submissions and teams**

1. May one participant take part in **two different submissions** in AI Builder Cup 2026 (for example, one in the Manufacturing theme and one in the BFSI theme)? If yes, must they be submitted by two separate teams, or may the same team submit two projects?
2. If two separate teams are required, may the **same person be a member of both teams**? And may the two teams share more than one member (for example, the same two people in both teams)?

**B. The deployed prototype**

3. How long must the deployed prototype remain **publicly accessible** to judges: until the submission deadline (October 18), until the end of online judging (please share the date if known), or until the final on December 4? Will judges open the prototype URL themselves at any time during judging, or only watch the demo video?

**C. APIs and data**

4. Besides Gemini on Google Cloud, may the prototype call **other Google Cloud APIs** (for example, the Web Risk API for URL reputation) and, in principle, non-Google third-party APIs? Are there any restrictions we should know about?
5. May the 3-minute demo video show **real screenshots of chat messages** provided by real users, if we have their written consent and all personal information (names, phone numbers, account IDs, profile pictures) is blurred? Are platform names or logos visible in such screenshots a problem?
6. May the demo video or submission include **evidence from real users**, such as a short anonymous quote from a seller we interviewed (for example, "a Carousell seller in Singapore"), if the seller has given written consent? Is there a required format for such user evidence, or anything we should avoid?

**D. Optional**

7. Do participants receive any **Google Cloud credits** for building and hosting the prototype? If yes, how can we request them?

Thank you very much for your time. I look forward to your reply.

Best regards,
[Full name]
[Registered email] · [Country/City]
[Team name(s), if already registered]

---

## 中文對照（給老闆確認意思，不用寄）

1. 同一個人能不能參與兩件作品（例如製造業一件、BFSI 一件）？要兩個不同團隊，還是同一團隊可以交兩件？
2. 如果要兩個團隊，同一個人能不能同時在兩隊？兩隊能不能有超過一位共同成員？
3. 部署的原型要公開到什麼時候（10/18、線上評審結束、還是 12/4 決賽）？評審會自己打開網址，還是只看影片？
4. 除了 Gemini，能不能呼叫其他 Google Cloud API（例如 Web Risk）或非 Google 的第三方 API？有沒有限制？
5. 影片能不能放真實使用者提供、有書面同意、而且個資都打碼的聊天截圖？截圖裡出現平台名稱或 logo 有沒有問題？
6. （2026-09-25 Sandy 加，依 9/24 盤點會議）demo／影片或提交資料裡，能不能附使用者證據，例如受訪賣家有書面同意的匿名引言（像「一位新加坡 Carousell 賣家」）？有沒有格式要求或要避免的地方？
7. （選問，Felix 要的）參賽者有沒有 Google Cloud 抵免額？怎麼申請？
