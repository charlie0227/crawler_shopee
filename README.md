# Shopee coin getter (Playwright)

每天自動到 [shopee.tw](https://shopee.tw/shopee-coins) 簽到領蝦幣。
v2 用 **Playwright** 重寫，取代原本的 Selenium 3 + chromedriver 版本。

## 運作方式

| 指令 | 做什麼 | 多久跑一次 |
|---|---|---|
| `login` | 開一個**有畫面**的瀏覽器，你自己登入蝦皮（密碼、簡訊/Email 驗證、拼圖都自己處理）。登入狀態存在 `profile/` | 第一次，以及 session 失效時 |
| `checkin` | 用 `profile/` 的 session 以 headless 開簽到頁，按下簽到 | 每天（launchd / cron） |

程式**不存帳號密碼**，也不會嘗試繞過驗證碼。蝦皮要求驗證時會直接停下來通知你重新 `login`。

> ⚠️ 必須在**家裡的網路**執行（例如常開的 Mac mini）。從雲端主機或 GitHub Actions 連線會被蝦皮導到 `/verify/traffic/error` 擋下。

## 安裝（macOS）

```bash
git clone https://github.com/charlie0227/crawler_shopee.git
cd crawler_shopee
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium   # 或用已安裝的 Chrome：export BROWSER_CHANNEL=chrome
```

## 使用

```bash
# 1. 第一次：手動登入（會跳出瀏覽器視窗，最多等 10 分鐘）
BROWSER_CHANNEL=chrome .venv/bin/python shopee_checkin.py login

# 2. 測試簽到
BROWSER_CHANNEL=chrome .venv/bin/python shopee_checkin.py checkin
#    想看瀏覽器在做什麼：加 --headed；要詳細 log：加 --debug

# 3. 安裝每日排程（macOS launchd，預設每天 09:17）
scripts/install_launchd.sh 9 17
```

Linux / cron：

```cron
17 9 * * * cd /path/to/crawler_shopee && .venv/bin/python shopee_checkin.py checkin >> log/cron.log 2>&1
```

## 退出碼

| code | 意義 | 該做什麼 |
|---|---|---|
| 0 | 簽到成功 | — |
| 1 | 今天已簽到 | — |
| 2 | 登入失效 | 重跑 `login` |
| 3 | 蝦皮要求驗證 / 流量驗證 | 重跑 `login`；若每天都出現，改 `HEADLESS=0` |
| 4 | 頁面無法辨識（可能改版） | 看 `debug/` 的截圖與 HTML，把新文案加進 `shopee_checkin.py` 的 `TEXT_*` |
| 5 | 其他錯誤 | 看 `log/` |

## 環境變數

| 變數 | 預設 | 說明 |
|---|---|---|
| `BROWSER_CHANNEL` | （Playwright Chromium） | `chrome` = 用本機 Google Chrome |
| `BROWSER_PATH` | | 指定瀏覽器執行檔路徑 |
| `HEADLESS` | `1` | `0` = 顯示視窗執行（headless 被擋時用） |
| `SHOPEE_PROFILE_DIR` | `./profile` | 登入 session 存放處（含 cookie，勿外流） |
| `STATE_TIMEOUT` | `45` | 等待頁面出現已知狀態的秒數 |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | | 設定後，失敗時發 Telegram 通知 |
| `NOTIFY_SUCCESS` | `0` | `1` = 成功時也通知 |

## 測試

測試用 `page.route` 模擬 shopee.tw，不需要帳號或網路：

```bash
.venv/bin/pytest -q
```

## 蝦皮改版時

頁面判斷全部靠畫面文字（不依賴會變的 CSS class），集中在 `shopee_checkin.py` 開頭：
`TEXT_CHECKIN_BUTTON`、`TEXT_ALREADY`、`TEXT_VERIFY`。辨識失敗時 `debug/` 會留截圖和 HTML，照著補文案即可。

## License

[MIT](https://choosealicense.com/licenses/mit/)
