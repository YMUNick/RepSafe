# UI 規格：RepSafe（MVP）

> Reply safe. Keep your rep.

- 建立：2026-09-24，Dana（設計）
- 依據：`docs/meetings/2026-09-24-電商客服反詐騙.md`、`docs/prd.md`（第 5–8 節）、`docs/engineering/architecture.md`、`app/main.py`、`app/analyze.py`、`app/verdict.py`
- 搭配：`docs/design/storyboard.md`（3 分鐘影片分鏡）
- 2026-09-24 同步老闆拍板：截圖上傳納入 MVP、開關預設開啟，輸入區以「文字＋截圖」為主版本（第 3 節）。
- 2026-09-24 老闆再拍板：**前端要做截圖預覽**（推翻本文件原本「不預覽」的決定，和 PRD 第 11 節前端工時「含截圖上傳、預覽、文字確認」一致）。規格見第 3.1 節。
- 實作：`app/static/index.html`（單檔靜態頁，純 HTML/CSS/JS，沒有建置步驟、沒有外部請求、沒有 API key）。**要讓它能開，Eddie 要先加第 9 節的掛載程式碼。**
- 沒有 Figma，這份文件就是設計稿。token、尺寸、文案都寫死在這裡；**英文文案是定稿，要改請先改這份文件，再改 `index.html`**。
- 只有一套淺色主題（白底），不做深色模式。刻意和 LineSleuth 的深色＋琥珀做出區隔。

## 0. 設計原則（互相衝突時，照這個順序取捨）

1. **不說「安全」**：畫面上沒有綠色判定、沒有勾勾大圖示、沒有 "Safe" 這個字當判定。沒找到紅旗就是琥珀卡。
2. **失敗就誠實說不知道**：任何失敗都不能變成琥珀卡。前端收到未知的 `verdict` 值，或連不到後端，一律顯示灰卡。
3. **顏色不是唯一的訊號**：每一種狀態都同時有顏色、圖示字元、文字，色弱的人和投影偏色的情況下也看得懂。
4. **一個畫面只有一個主動作**：`Check message` 是唯一的深色實心按鈕。`Copy reply` 是結果出來之後的第二個動作（青綠色）。
5. **訊息內容一律當作不可信的純文字**：只用 `textContent` 顯示，**訊息裡的連結絕對不能做成可以點的超連結**，也不能自動偵測成電話或 email。
6. **手機優先**：以 iPhone SE（375px 寬）到 430px 為主要尺寸，內容最大寬度 480px 置中。桌機看到的也是同一條直欄。

## 1. 版面（手機直向，由上到下，單一畫面）

```
┌──────────────────────────────┐  max-width 480px，左右留白 16px
│ RepSafe  Reply safe. Keep... │  品牌列（沒有 logo 圖、沒有選單）
│ [Offline test mode ...]      │  只在 offline_fixture 時出現
├──────────────────────────────┤
│ [ Paste text | Upload shot ] │  主版本預設出現（screenshot_enabled=true）；開關關閉時隱藏（第 3 節）
│ ┌────┐ chat.png              │  截圖預覽（選了截圖才出現，兩個分頁都看得到，第 3.1 節）
│ │縮圖│ 1.2 MB. Preview stays…│
│ └────┘ [Change] [Remove]     │
│ Buyer's message              │
│ ┌──────────────────────────┐ │
│ │ Paste the buyer's        │ │  textarea，最小高度 160px
│ │ message here...          │ │
│ └──────────────────────────┘ │
│ Checked before you reply. 0/5000
│ [   Check message   ][Clear] │  主按鈕深色實心，高 48px
│ We never open the links ...  │  隱私小字
├──────────────────────────────┤
│  (1)      (2)      (3)   (4) │  四步驟標籤
│ Read    Check   Match  Verdict
│ text    links   domains      │
│ Your    Google  Look-  Gemini│  副標：每一步是誰在做
│ message Web Risk alike       │
│ Done    Done    Done   Done  │  狀態字
│ Every link goes through both checks. The AI can't skip them.
├──────────────────────────────┤
│ ┌ 判定卡（紅／琥珀／灰）───┐ │
│ └──────────────────────────┘ │
│ ┌ Red flags（只有紅卡有）──┐ │
│ │ ▌"https://shopee-tw..."   │ │  原句（連結用等寬字）
│ │ ▌Uses the name Shopee ... │ │  原因
│ │ ▌[Domain check]           │ │  工具標籤
│ └──────────────────────────┘ │
│ ┌ Safe reply（青綠）────────┐ │
│ │ Hi! To keep us both ...   │ │
│ │ Links, numbers and IDs... │ │
│ │ [      Copy reply       ] │ │  高 48px，滿寬
│ └──────────────────────────┘ │
│ RepSafe can miss brand-new...│  頁尾免責
└──────────────────────────────┘
```

- 首頁一打開就看得到四個步驟標籤（灰色待命狀態），讓第一次來的人不必讀說明，就知道按下去之後會發生什麼事。
- 結果出來後，頁面自動捲到判定卡（`scrollIntoView`，減少動態偏好時不做平滑捲動）。因為手機上輸入區會佔掉整個螢幕，不捲的話賣家會以為沒反應。
- **刻意不做**（砍掉讓體驗更簡單，也省前端工時）：聊天泡泡重現、連結清單區塊（`links` 欄位先不顯示，紅旗原因已經寫清楚了）、歷史紀錄、分享、語言切換、深色模式、登入、「結果過期」提示（改了文字就重按一次即可）。

## 2. 設計 Token（CSS 變數）

直接寫在 `index.html` 的 `:root`。元件只准引用變數，不寫死色碼。

```css
:root {
  /* 底色與文字 */
  --color-bg: #FFFFFF;            /* 頁面底：白 */
  --color-surface: #F6F7F9;       /* 分頁切換底、工具標籤底 */
  --color-border: #E3E6EB;
  --color-border-strong: #C9CED6; /* 輸入框、次要按鈕外框 */
  --color-text: #111827;
  --color-text-2: #4B5563;
  --color-text-muted: #6B7280;    /* 最淡的可用文字色（白底對比 4.8:1），不能再更淡 */
  --color-ink: #111827;           /* 主按鈕 Check message、步驟完成的實心圓 */
  --color-on-ink: #FFFFFF;
  --color-focus: #2563EB;         /* 只用在鍵盤焦點框 */

  /* 判定三態 */
  --red-text: #B91C1C;   --red-accent: #DC2626;   --red-bg: #FEF2F2;   --red-border: #FCA5A5;
  --amber-text: #92400E; --amber-accent: #D97706; --amber-bg: #FFFBEB; --amber-border: #FCD34D;
  --grey-text: #374151;  --grey-accent: #6B7280;  --grey-bg: #F3F4F6;  --grey-border: #9CA3AF;

  /* 青綠：只用在 Safe reply 卡和 Copy reply 按鈕 */
  --teal-text: #115E59; --teal-accent: #0F766E; --teal-bg: #F0FDFA; --teal-border: #99F6E4; --on-teal: #FFFFFF;

  /* 字體 */
  --font-sans: system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif;
  --font-mono: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  --fs-xs: 13px; --fs-sm: 14px; --fs-md: 16px; --fs-lg: 20px; --fs-xl: 22px;
  --lh: 1.5;

  /* 間距（4px 基準）、圓角、觸控、動態 */
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-5: 24px; --space-6: 32px;
  --radius-sm: 6px; --radius-md: 12px; --radius-pill: 999px;
  --tap: 48px;
  --motion: 200ms;
  --stagger: 280ms;   /* 步驟逐一亮起的間隔；減少動態偏好時變 0 */
}
```

### 顏色規則

| 顏色 | 用在哪裡 | 絕對不能用在 |
|---|---|---|
| 紅 | 紅卡、紅旗清單左側色條、紅旗裡的連結底色、輸入錯誤文字 | 按鈕 |
| 琥珀 | 只有琥珀卡 | 其他任何地方 |
| 灰 | 灰卡（虛線外框）、步驟「沒完成」、離線模式提示 | — |
| 青綠 | **只有** Safe reply 卡和 Copy reply 按鈕 | 判定卡、步驟標籤、任何「完成」「通過」的圖示 |
| 深墨色 | 主按鈕、步驟完成的實心圓 | — |

- 步驟完成用**深墨色實心圓＋白色勾**，不是綠色勾。這是刻意的：綠色勾會讓人誤讀成「通過＝安全」。
- 對比度：所有文字對底色至少 4.5:1（琥珀卡用深棕 `#92400E` 當文字色，不用亮琥珀）。
- 灰卡文字要全亮度（`--grey-text`），不能做成像 disabled 的淡灰。灰卡是刻意的結果，不是錯誤畫面。

### 字體

- 不載入任何網路字型（Cloud Run 冷啟動已經夠慢，也不對外發請求）。用系統字型，並把繁中字型列進後備，讓中文對話顯示正常。
- 正文和 textarea 一律 **16px**：iOS Safari 在輸入框字級小於 16px 時會自動放大頁面，版面會跑掉。
- **紅旗清單裡來自連結的原句（工具是 `domain_check` 或 `url_reputation`）用等寬字**，讓 `shopee-tw`、`xn--` 這類差一個字元的網址看得清楚。
- 字級：品牌 22px/800；判定卡標題 20px/700；卡片標題 16px/700；正文 16px；說明 14px；小字、標籤 13px；步驟副標 11px（只放在步驟格這種不重要的輔助資訊）。

## 3. 輸入區（主版本：文字＋截圖）

**已決定（2026-09-24 老闆拍板）：截圖上傳納入 MVP，開關預設開啟**（PRD 第 5、11 節，F1）。以「文字＋截圖」為主版本；「只有貼文字」降為開關關閉時的備用版本（例如 10/4 對帳時截圖工作超支、老闆決定關掉，見 PRD 第 11 節）。前端兩種版本都已經做好，由後端開關決定，切換不用改前端：

| | **主版本：文字＋截圖（預設）** | 備用版本：只有貼文字 |
|---|---|---|
| 開關 | `SCREENSHOT_ENABLED=true` | `SCREENSHOT_ENABLED=false` |
| 前端怎麼知道 | 開頁時呼叫 `GET /api/config`，`screenshot_enabled:true` | 同左，`screenshot_enabled:false` |
| 畫面 | textarea 上方有分頁切換 `Paste text` ／ `Upload screenshot`，預設停在 `Paste text` | 沒有分頁切換，只有 textarea |
| `/api/extract-text` | 存在 | 不存在（404），前端不會呼叫 |

- 預設分頁停在 `Paste text`：截圖讀完也會切回這個分頁讓賣家確認，兩條路最後都落在同一個 `Check message`，操作只有一種收尾。
- `/api/config` 呼叫失敗時，前端照備用版本顯示（保守做法：不顯示上傳按鈕，貼文字仍然能用）。

### 主版本的截圖流程

1. 點 `Upload screenshot` 分頁 → 虛線框裡只有一個按鈕 `Choose screenshot`，上面寫 `We only read the text in your screenshot.`，下面寫格式與大小限制。
2. 選好圖片 → 前端先檢查格式與大小（格式不在白名單或超過 `max_image_mb` 直接擋：不預覽、不上傳，錯誤文案見第 6.2 節）→ 通過就**立刻顯示預覽**（第 3.1 節）→ 顯示 `Reading text from your screenshot…` → `POST /api/extract-text`。
3. 成功 → **自動切回 `Paste text` 分頁**，把讀出來的文字填進 textarea，下方出現提示 `Text read from your screenshot. Check it, especially the links, then tap Check message.`。預覽留在 textarea 上方，賣家可以點縮圖放大，**對照原圖檢查連結**。**不會自動送出**：Eddie 的設計是讓賣家先看一眼讀出來的文字（Gemini 可能把改字網域「修正」回正確網址）。
4. 失敗 → 分頁內顯示後端的 `detail` 文字（後端的錯誤訊息都已經是英文、可以直接給使用者看），網路錯誤則顯示 `Could not read the screenshot. Please paste the text.`。預覽保留，賣家可以按 `Change` 換一張或 `Remove` 移除。
5. ~~圖片不預覽、不保留在頁面上（少一個元件，也少一個隱私疑慮）。~~ **已被 2026-09-24 老闆拍板推翻**：改成只在瀏覽器本機預覽。原本擔心的隱私疑慮用第 3.1 節的規則處理（object URL、不另外上傳、不存、換圖／清除就釋放）；多出來的元件換到的是「讀出的文字可以和原圖對照」，這正是確認步驟需要的。

### 3.1 截圖預覽（2026-09-24 拍板新增）

**位置**：分頁切換下方、兩個分頁共用的一塊（`#shot-preview`）。選了截圖才出現，切到 `Paste text` 也還在，讓賣家邊看圖邊確認文字。開關關閉（備用版本）時永遠不會出現。

**外觀**：`--color-surface` 底、1px `--color-border` 外框、`--radius-md` 圓角、內距 12px。

| 元件 | 規格 |
|---|---|
| 縮圖 | **72×72px**，`object-fit: cover`、`object-position: top`（聊天截圖是長圖，從頂端裁），1px `--color-border-strong` 框、`--radius-sm`。縮圖本身是按鈕：點一下在下方展開**大圖**（滿寬、最高 `70vh`、`object-fit: contain`），再點收合；展開時縮圖框變 2px 深墨色 |
| 檔名 | 14px／600，單行，過長用省略號。用 `textContent` 顯示 |
| 說明 | 13px 淡字：`{size}. Preview stays on this device.`（`{size}` 例如 `1.2 MB`、`840 KB`） |
| 按鈕 | `Change`、`Remove`，次要按鈕樣式縮小版（高 40px、14px 字）。**不用紅色**（紅色不能用在按鈕，第 2 節）。`Change` 直接打開選檔；`Remove` 只移除圖片 |

**行為**

- `Change`：選新圖 → 走完整流程（檢查 → 新預覽 → 重新讀文字 → 覆蓋 textarea）。新圖被格式／大小擋下時，**舊預覽維持原狀**，只顯示錯誤。
- `Remove`：移除預覽與讀取中／錯誤訊息，**不清掉 textarea 的文字**（賣家可能已經改過）；要全部清空按 `Clear`。
- `Clear`：清文字、清結果，**也一併移除預覽**。
- 讀取途中換圖或移除：舊圖的讀取結果直接丟棄，不會填進 textarea。
- 選檔、格式錯、大小錯時，自動切到 `Upload screenshot` 分頁，讓讀取狀態和錯誤訊息看得到。

**瀏覽器無法顯示的格式（HEIC／HEIF 等）**

- Chrome、Firefox 桌機版通常不能顯示 HEIC（iPhone Safari 可以）。前端不猜，**圖片載入失敗（`onerror`）就改顯示替代框**：同樣 72×72，裡面是線條圖片圖示（inline SVG，不對外請求）＋副檔名大寫（例如 `HEIC`）。
- 說明改成：`{size}. This browser can't show {EXT} images, but we can still read the text.`
- 大圖不能展開（替代框不是按鈕），`Change`／`Remove` 照常可用。讀文字照常送後端（後端接受 HEIC）。

**隱私（必守）**

1. 預覽只用 `URL.createObjectURL(file)` 在瀏覽器本機顯示，**不另外上傳**（唯一的上傳就是原本的 `/api/extract-text`），**不存 `localStorage`／`sessionStorage`／IndexedDB**、不轉成 data URL 放進 DOM。
2. 換圖、`Remove`、`Clear`、離開頁面（`pagehide`）時一律 `URL.revokeObjectURL()`，並移除 `<img>` 的 `src`。
3. 隱私小字 `We never open the links you paste, and we don't save your messages.` 不用改：截圖也沒有被保存。

**無障礙**

| 元素 | 設定 |
|---|---|
| 縮圖按鈕 | `aria-label="Show screenshot larger"`／展開後 `Hide larger screenshot`，`aria-expanded`、`aria-controls` 指向大圖區；裡面的 `<img alt="">`（按鈕已經有名字，不重複念） |
| 大圖 | `alt="Your screenshot, full size"`（內容無法預先描述，讀出來的文字就在 textarea，螢幕閱讀器使用者以文字為準） |
| 替代框 | `role="img"`、`aria-label="Screenshot file, no preview"`，圖示 `aria-hidden` |
| 按鈕 | `aria-label="Change screenshot"`／`Remove screenshot`（包含畫面上的字，符合 label-in-name） |
| 焦點 | `Remove` 後焦點回到目前分頁的輸入（textarea 或選檔） |
| 錯誤 | 沿用 `#shot-error`（`role="alert"`），讀取中沿用 `#shot-status`（`role="status"`） |

**文案紅線**：介面、影片、pitch 任何地方都**不能**出現 "detect fake screenshots"、"verify payment proof"、"fake transfer" 這類字眼。截圖只讀文字。

## 4. 四步驟標籤

### 固定文字

| # | `steps[].id` | 標題 | 副標（誰在做） |
|---|---|---|---|
| 1 | `read_text` | Read text | Your message |
| 2 | `check_urls` | Check links | Google Web Risk |
| 3 | `match_domains` | Match domains | Look-alike check |
| 4 | `verdict` | Verdict | Gemini |

步驟下方固定一行小字：`Every link goes through both checks. The AI can't skip them.`

- 這行字是在反映 **Eddie 的實作決定①**：兩個工具由程式對**每一個連結強制執行**，不是讓模型自己決定要不要呼叫（architecture 第 4 節）。畫面上照樣顯示四步，而這行小字把它轉成賣點：注入攻擊沒辦法叫 AI「不要查」。影片與 pitch 的說法統一用 "tool-augmented Gemini, tools enforced by code"。
- 不要寫成 "function calling"，免得評審以為是模型自己決定呼叫。

### 每一格的狀態

| 前端狀態 | 圓點 | 狀態字 | 什麼時候 |
|---|---|---|---|
| `idle` | 灰框空心，裡面是步驟編號 | （空） | 還沒按 Check message |
| `run` | 深墨色框＋旋轉圈 | `Reading…`／`Checking…` | 等待後端回應 |
| `done` | 深墨色實心＋白色 ✓ | `Done` | API 回 `done` |
| `none` | 灰色虛線框＋ – | `No links` | API 回 `none`（訊息裡沒有連結） |
| `warn` | 灰底＋ ! | `Didn't finish` | API 回 `error` 或 `skipped` |
| `warn`（第 4 格） | 灰底＋ ! | `Without Gemini` | `problems` 含任何 `gemini_*` 或 `rate_limited` |
| `warn`（第 4 格） | 灰底＋ ! | `Didn't finish` | `problems` 含 `internal_error` |

### 動態（誠實說明）

`/api/analyze` 是**一次回傳全部結果**，後端沒有逐步推送進度。所以：

1. 按下後：第 1 格 `run` → 280ms 後變 `done`；第 2–4 格同時進入 `run`（和後端實際行為一致：網域比對先跑完，Web Risk 和 Gemini 平行跑）。
2. 回應回來後：第 2、3、4 格**每隔 280ms 依序**換成最終狀態，再過 280ms 判定卡淡入。總共大約 1.1 秒。
3. 這個間隔**只是呈現用的節奏**，讓人眼跟得上（影片裡也需要「逐一亮起」的畫面）。畫面上不顯示每一步各花了幾秒，也不宣稱它們依序執行。
4. 等超過 8 秒：步驟下方出現 `Still checking. The first check after a quiet spell can take a little longer.`（冷啟動，最小實例是 0）。
5. 前端 30 秒逾時 → 中止請求，顯示灰卡（第 5 節「連不到」）。
6. `prefers-reduced-motion`：間隔變 0、旋轉圈停轉。

## 5. 判定卡三態

判定**只看 `verdict` 欄位**（`app/verdict.py` 是全專案唯一決定判定的地方），前端不自己推判定。

| `verdict` | 外觀 | 圖示字元 | 標題 | 內文 | 額外內容 |
|---|---|---|---|---|---|
| `red` | 紅底、2px 紅實線框 | `!` | **Scam red flags found** | `{n} red flag(s). Don't open the links, and don't pay or chat outside the platform.` | 手法標籤（`scam_type`，對照見第 6.3 節）；`problems` 不是空的時候加一行小字（見下） |
| `amber` | 琥珀底、2px 琥珀實線框 | `i` | **No red flags found** | `Our checks found nothing suspicious in this message.` | **固定小字**：`This doesn't mean it's safe. Before any payment, stay in the platform's own checkout.` |
| `grey` | 灰底、2px 灰色**虛線**框 | `?` | **Can't determine** | `Not every check finished, so we won't guess. Don't open the links or pay outside the platform. If unsure, ask the platform's customer service.` | 原因清單（由 `problems` 轉成人話，第 6.4 節）＋ `Try again` 按鈕 |

- 琥珀卡固定小字的中文原意是「不代表安全，付款前請走平台內流程」。英文定稿就是上表那一句，**不論什麼情況都要顯示，不能收合、不能變淡**。
- 判定卡加 `role="status"`，結果區 `aria-live="polite"`，螢幕閱讀器會念出判定。

### 紅卡優先於灰卡（反映 Eddie 的實作決定②）

已經找到紅旗時，就算 Web Risk 或 Gemini 失敗，`verdict` 仍然是 `red`，**前端照樣顯示紅卡，不降成灰卡**。畫面這樣處理：

- 紅卡內文照常，下方多一行小字：`Some checks didn't finish, but these red flags are enough to stop.`
- 步驟第 2 格可能顯示 `Didn't finish`、第 4 格可能顯示 `Without Gemini`，讓賣家看得出是哪一步沒完成。
- 紅旗清單照常列出已經找到的紅旗（例如來自 `domain_check` 的網域冒用）。
- 這條規則 Eddie 已經請 Paula、Quinn 確認（architecture E2）。在確認之前，前端照後端的 `verdict` 顯示即可，不用改。

### 前端自己的保底規則

- `verdict` 不是 `red`／`amber`／`grey` 其中一個 → 顯示灰卡。
- 連不到後端、非 400/422 的 HTTP 錯誤、30 秒逾時、回應裡沒有 `verdict` → 顯示灰卡，原因寫 `Couldn't reach RepSafe. Check your connection.`，**這種情況不顯示 Safe reply 卡**（沒有經過後端過濾的回覆，不給）。

## 6. 英文 UI 文案（定稿，程式逐字使用）

### 6.1 固定文案

| 位置 | 文案 |
|---|---|
| `<title>` | `RepSafe: Reply safe. Keep your rep.` |
| 品牌列 | `RepSafe` ／ `Reply safe. Keep your rep.` |
| 離線提示 | **`Offline test mode.`** `Results come from simple keyword rules, not Gemini. Don't rely on them.` |
| 分頁（主版本） | `Paste text` ／ `Upload screenshot` |
| 輸入欄標籤 | `Buyer's message` |
| placeholder | `Paste the buyer's message here. The whole chat is fine.` |
| 輸入欄左下 | `Checked before you reply.` |
| 字數 | `{n} / {max_input_chars}`（超過時變紅、粗體） |
| 截圖說明 | `We only read the text in your screenshot.` |
| 截圖按鈕 | `Choose screenshot` |
| 截圖限制 | `PNG, JPG, WebP or HEIC, up to {max_image_mb} MB` |
| 截圖讀取中 | `Reading text from your screenshot…` |
| 截圖讀完 | `Text read from your screenshot. Check it, especially the links, then tap Check message.` |
| 預覽說明 | `{size}. Preview stays on this device.` |
| 預覽說明（無法顯示） | `{size}. This browser can't show {EXT} images, but we can still read the text.` |
| 預覽按鈕 | `Change` ／ `Remove`（aria-label：`Change screenshot` ／ `Remove screenshot`） |
| 縮圖按鈕（aria-label） | `Show screenshot larger` ／ `Hide larger screenshot` |
| 大圖 alt | `Your screenshot, full size` |
| 主按鈕 | `Check message` ／ 讀取中 `Checking…`（加旋轉圈、disabled） |
| 次按鈕 | `Clear` |
| 隱私小字 | `We never open the links you paste, and we don't save your messages.` |
| 步驟說明 | `Every link goes through both checks. The AI can't skip them.` |
| 冷啟動提示 | `Still checking. The first check after a quiet spell can take a little longer.` |
| 紅旗清單標題 | `Red flags` |
| 安全回覆標題 | `Safe reply` |
| 安全回覆說明（`safe_reply_source=gemini`） | `Links, numbers and IDs are removed automatically.` |
| 安全回覆說明（`safe_reply_source=fallback`） | `Standard reply, because the AI reply wasn't available. Links, numbers and IDs are removed.` |
| 複製按鈕 | `Copy reply` → 成功 `Copied`（2 秒後還原） → 失敗 `Couldn't copy. Press and hold the text to copy it.` |
| 灰卡按鈕 | `Try again` |
| 頁尾 | `RepSafe can miss brand-new scams. When in doubt, keep the chat and the payment inside the platform.` |

- 隱私小字的根據：後端不打開連結、log 不記訊息內容（architecture 第 5 節）。如果之後有任何一條改變，這句要跟著改。
- 頁尾那句是琥珀卡小字的延伸，讓「查不到不等於安全」在整頁都成立。

### 6.2 空輸入與輸入錯誤（顯示在輸入框下方，紅字，不出判定卡）

| 情況 | 文案 | 來源 |
|---|---|---|
| 空白就按 Check message | `Paste the buyer's message first.` | 前端先擋（和後端 400 同一句） |
| 超過字數上限 | `Message is longer than {max} characters. Paste only the buyer's recent messages.` | 前端先擋 |
| 後端回 400 | 直接顯示 `detail` | `app/main.py` |
| 後端回 422 | `Please check the message and try again.` | FastAPI 驗證錯誤 |
| 截圖超過大小 | `Image is larger than {max_image_mb} MB.` | 前端先擋（和後端同一句），顯示在截圖分頁 |
| 截圖格式不支援 | `This file type isn't supported. Use PNG, JPG, WebP or HEIC.` | 前端先擋（白名單和 `app/screenshot.py` 的 `ALLOWED_MIME` 相同），顯示在截圖分頁 |

- 主按鈕**不做成 disabled** 來擋空輸入：按了沒反應的按鈕比一行錯誤訊息更難懂。
- 使用者一開始打字，錯誤訊息就消失。

### 6.3 手法標籤（`scam_type` → 紅卡上的 chip）

| `scam_type` | 顯示 |
|---|---|
| `phishing_link` | Phishing link |
| `impersonation` | Fake staff |
| `off_platform_payment` | Off-platform payment |
| `credential_request` | Asks for codes or passwords |
| `prompt_injection` | Tries to trick the checker |
| `other_scam` | Other scam pattern |
| `short_link` | Hidden short link |
| `idn_domain` | Look-alike letters |
| `brand_impersonation`、`lookalike_domain` | Fake marketplace domain |
| `userinfo_trick` | Disguised link |
| `bad_punycode` | Malformed link |
| `listed_threat` | Known dangerous link |
| `none`、`null`、其他 | 不顯示 chip |

（後面七個是 Gemini 沒給手法、但工具找到紅旗時，後端改用第一條紅旗的 `code` 當 `scam_type`，見 `app/analyze.py`。）

### 6.4 灰卡原因（`problems` → 人話，重複的只列一次）

| `problems` 代碼 | 顯示 |
|---|---|
| `gemini_timeout` | The AI check took too long. |
| `gemini_error`、`gemini_unavailable` | The AI check is unavailable right now. |
| `gemini_quota` | Today's check limit has been reached. |
| `gemini_bad_output` | The AI answer couldn't be verified against your message. |
| `reputation_error` | Google Web Risk didn't answer for some links. |
| `reputation_skipped` | There were too many links, so some weren't checked. |
| `rate_limited` | Too many checks right now. Try again in a few minutes. |
| `internal_error` | Something went wrong on our side. |
| （前端）連不到 | Couldn't reach RepSafe. Check your connection. |
| 其他未知代碼 | A check didn't finish. |

### 6.5 紅旗清單的工具標籤（`red_flags[].tool`）

| `tool` | 標籤 | 原句樣式 |
|---|---|---|
| `domain_check` | Domain check | 等寬字、淺紅底（這是連結） |
| `url_reputation` | Google Web Risk | 等寬字、淺紅底（這是連結） |
| `injection_guard` | Injection guard | 一般字 |
| `gemini` | Gemini | 一般字 |

- 每一條紅旗：左側 3px 紅色色條 → 原句（`quote`）→ 原因（`reason`，後端已經是英文）→ 工具標籤。
- 同一句被兩個工具抓到時，後端會回兩條，前端照樣列兩條，這正好讓評審看到「兩個工具都抓到」。
- 中文原句不翻譯（後端的 `reason` 已經是英文）；影片裡用字幕補翻譯。

## 7. 各狀態總覽

| 狀態 | 輸入區 | 步驟 | 結果區 |
|---|---|---|---|
| 初次開啟 | 空白 textarea | 四格 `idle` | 空 |
| 空輸入就送出 | 紅字錯誤、輸入框紅框 | 不動 | 不動 |
| 載入中 | 主按鈕 `Checking…` disabled、Clear disabled | 第 1 格 done，2–4 格 `run` | 清空 |
| 載入超過 8 秒 | 同上 | 同上＋冷啟動提示 | 空 |
| 紅 | 恢復 | 最終狀態 | 紅卡 → Red flags → Safe reply |
| 琥珀 | 恢復 | 最終狀態 | 琥珀卡 → Safe reply |
| 灰（後端回灰） | 恢復 | 最終狀態（有 `Didn't finish`／`Without Gemini`） | 灰卡＋原因＋ Try again → Safe reply（固定範本） |
| 灰（連不到） | 恢復 | 2–4 格 `Didn't finish` | 灰卡＋ `Couldn't reach RepSafe…` ＋ Try again（**沒有** Safe reply） |
| 離線模式 | — | — | 頁首灰色提示條常駐 |
| 截圖讀取中（主版本） | 預覽出現＋分頁內 `Reading text…` | 不動 | 不動 |
| 截圖讀完（主版本） | 切回文字分頁，預覽留在 textarea 上方 | 不動 | 不動 |
| 截圖失敗（主版本） | 預覽保留＋分頁內紅字 | 不動 | 不動 |
| 截圖被擋（格式／大小） | 分頁內紅字，不產生新預覽（舊預覽不動） | 不動 | 不動 |
| 瀏覽器無法顯示（HEIC） | 預覽改成圖示＋副檔名＋說明 | 不動 | 不動 |

## 8. 欄位與 API JSON 對照

### `GET /api/config`（開頁時呼叫一次）

| 欄位 | 前端用途 |
|---|---|
| `screenshot_enabled` | `true` 才顯示分頁切換與上傳（第 3 節） |
| `offline_fixture` | `true` 顯示離線提示條 |
| `max_input_chars` | 字數計數與前端先擋 |
| `max_image_mb` | 截圖大小先擋、限制文案 |
| `mode` | 不顯示 |

### `POST /api/analyze` `{ "text": "..." }`

| 欄位 | 畫面位置 | 說明 |
|---|---|---|
| `verdict` | 判定卡顏色與標題 | `red`／`amber`／`grey`；未知值當灰 |
| `problems[]` | 灰卡原因清單；紅卡的「有些檢查沒完成」小字；第 4 步 `Without Gemini` | 代碼對照第 6.4 節 |
| `scam_type` | 紅卡 chip | 對照第 6.3 節 |
| `red_flags[].quote` | 紅旗原句 | 純文字，不能變成超連結 |
| `red_flags[].reason` | 紅旗原因 | 後端英文 |
| `red_flags[].tool` | 工具標籤、原句要不要用等寬字 | 對照第 6.5 節 |
| `red_flags[].code` | 不顯示 | — |
| `steps[].id`／`steps[].status` | 四步驟狀態 | 對照第 4 節 |
| `safe_reply` | Safe reply 內文 | 後端已經過濾過網址、帳號 |
| `safe_reply_source` | Safe reply 說明文字 | `gemini`／`fallback` |
| `offline_fixture` | 離線提示條 | 以回應為準（和 `/api/config` 取聯集） |
| `links[]` | **MVP 不顯示** | 之後如果要做「連結清單」再用 |
| `request_id`、`mode`、`latency_ms` | 不顯示 | `latency_ms` 可以在錄影片時從 DevTools 看 |

### `POST /api/extract-text` `{ "image_base64": "data:...", "mime_type": "image/png" }`（主版本；開關關閉時不存在）

| 回應 | 前端處理 |
|---|---|
| 200 `{text, mode}` | 填入 textarea、切回文字分頁、顯示確認提示 |
| 400／429／503 `{detail}` | 分頁內紅字顯示 `detail` |
| 404 | 不會發生（開關關閉時前端根本不顯示上傳） |

- HEIC 在部分瀏覽器 `file.type` 是空字串，前端會依副檔名補成 `image/heic`／`image/heif`。
- `image_base64` 直接送 data URL，後端會切掉逗號前面的部分（`app/screenshot.py`）。

## 9. 交接給 Eddie：後端要加的掛載程式碼

前端檔案已經放在 `app/static/index.html`，**我沒有修改任何 Python 檔**。目前 `app/main.py` 沒有提供 `/` 路由，所以頁面還打不開。請 Eddie 在 `app/main.py` 加上下面這段（放在其他路由之後、`if settings.screenshot_enabled:` 之前或之後都可以）：

```python
from pathlib import Path
from fastapi.responses import FileResponse

INDEX_HTML = Path(__file__).parent / "static" / "index.html"


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Single-file front end (docs/design/ui-spec.md). No-cache so a redeploy shows up right away."""
    return FileResponse(INDEX_HTML, media_type="text/html",
                        headers={"Cache-Control": "no-cache", "Referrer-Policy": "no-referrer",
                                 "X-Content-Type-Options": "nosniff"})
```

- 只有一個檔案，所以用 `FileResponse` 就好，不需要 `StaticFiles` 掛整個資料夾。
- `Dockerfile` 是 `COPY app ./app`，`.dockerignore` 沒有排除 `.html`，**Docker 映像檔不用改**。
- 前端完全沒有外部請求，所以之後想加 CSP 可以用：`default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'`（可選，不影響功能）。
- 建議加一個測試：`GET /` 回 200、內容包含 `RepSafe`，而且 HTML 裡**沒有** `key=`、`AIza` 這類字串（對應 Quinn「前端無 API key」的檢查）。
- 可選的小改動（不做也能 demo）：`url_reputation` 紅旗的 `reason` 目前是 `Listed by Google Web Risk as SOCIAL_ENGINEERING.`，建議把威脅類型轉成人話，例如 `SOCIAL_ENGINEERING` → `phishing / social engineering`。

## 10. 驗收清單（Dana 視覺驗收，10/6 起）

- [ ] iPhone Safari（375px）與 Android Chrome 各跑一次紅、琥珀、灰三種結果。
- [ ] iPhone Safari 上 `Copy reply` 真的能貼到 LINE（Quinn 清單也有這項）。Cloud Run 是 https，`navigator.clipboard` 可以用；失敗時有 `execCommand` 備援和「長按複製」的提示。
- [ ] 點 textarea 時 iOS 不會把畫面放大。
- [ ] 紅旗清單裡的連結**點不下去**、長按也不會出現「打開連結」（它是純文字）。
- [ ] 灰卡的文字清楚，不像 disabled 的按鈕。
- [ ] 琥珀卡的固定小字在任何寬度都看得到。
- [ ] 畫面上任何地方都沒有綠色判定、沒有 "safe" 當判定、沒有「偵測偽造截圖」相關字眼。
- [ ] 離線模式時頁首一定有提示條；**錄影片前確認提示條沒有出現**（出現代表還在離線模式）。
- [ ] 開啟系統「減少動態效果」後，步驟直接顯示結果、沒有轉圈。
- [ ] 首頁看得到 `Paste text`／`Upload screenshot` 分頁（開關已開）；iPhone Safari 選相簿截圖、Android Chrome 各上傳一次，讀完會切回文字分頁並出現確認提示，**不會自動送出**。
- [ ] 上傳含改字網域的截圖，讀出來的網址和原圖一字不差；如果被「修正」，確認提示有讓人注意到連結。
- [ ] 截圖預覽：縮圖出現、點縮圖可放大／收合；`Change` 換圖後文字被新圖覆蓋；`Remove` 只移除圖、文字還在；`Clear` 圖文都清掉。
- [ ] Chrome 桌機上傳 HEIC：顯示圖示＋ `HEIC`＋替代說明，文字照常讀出。iPhone Safari 上傳 HEIC 顯示真正的縮圖。
- [ ] 上傳 `.gif`／`.pdf` 或超過大小的檔案：出現第 6.2 節錯誤、沒有預覽、DevTools Network **沒有**送出 `/api/extract-text`。
- [ ] DevTools Network 裡除了 `/api/extract-text` 沒有任何和圖片有關的請求（預覽是 `blob:` 本機網址）；Application 分頁的 Local/Session Storage 是空的。

## 11. 工時（前端 4 小時預算）

| 項目 | 估計 | 狀態 |
|---|---|---|
| 單檔頁面（主版本＋備用版本、三態、步驟、複製） | — | Dana 已寫好初版 `app/static/index.html` |
| Eddie 加 `/` 路由與測試 | 待估算（應該很少） | 待做 |
| 接上真的 Gemini 後調整文案、實機驗收（第 10 節） | 待估算 | 10/6 起 |
| 截圖上傳的實機測試（10MB、HEIC、iPhone） | 包含在 architecture 第 6 節的 2–3 小時裡 | 必做（2026-09-24 拍板開啟），10/6 起 |
| 截圖預覽（第 3.1 節） | 包含在前端 4 小時裡（PRD 第 11 節） | Dana 已寫進 `index.html`（2026-09-24），待實機驗收 |

初版已經寫好，前端 4 小時的預算應該會有剩，剩多少**待估算**（要看老闆實際讀程式、驗收花多少時間）。剩下的時間建議還給「找賣家」。
