#!/usr/bin/env python3
"""Shopee TW daily coin check-in (Playwright).

Two commands:

  login    Opens a real (headed) browser window. You log in to shopee.tw yourself
           (password, SMS / email link, puzzle — whatever Shopee asks for). The
           session is kept in a persistent browser profile on disk.

  checkin  Re-uses that profile, opens the coins page and presses the check-in
           button. Meant to run unattended every day (cron / launchd / Docker).

Exit codes (useful for schedulers / notifications):
  0  checked in successfully
  1  already checked in today
  2  not logged in (session expired) -> run `login` again
  3  Shopee asked for verification / blocked the session -> run `login` again
  4  page did not reach a known state (UI changed?) -> see debug/ dump
  5  unexpected error
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, Response, sync_playwright
from playwright.sync_api import Error as PlaywrightError

BASE_DIR = Path(__file__).resolve().parent


class Exit(IntEnum):
    SUCCESS = 0
    ALREADY = 1
    NEED_LOGIN = 2
    NEED_VERIFY = 3
    UNKNOWN_STATE = 4
    ERROR = 5


@dataclass
class Settings:
    coins_url: str = "https://shopee.tw/shopee-coins"
    login_url: str = (
        "https://shopee.tw/buyer/login?next=" + urllib.parse.quote("https://shopee.tw/shopee-coins", safe="")
    )
    profile_dir: Path = BASE_DIR / "profile"
    log_dir: Path = BASE_DIR / "log"
    debug_dir: Path = BASE_DIR / "debug"
    headless: bool = True
    channel: str | None = None  # "chrome" to use installed Google Chrome
    executable_path: str | None = None
    state_timeout_s: float = 45.0
    login_timeout_s: float = 600.0
    telegram_token: str | None = None
    telegram_chat_id: str | None = None
    notify_success: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        s = cls()
        env = os.environ
        if env.get("SHOPEE_PROFILE_DIR"):
            s.profile_dir = Path(env["SHOPEE_PROFILE_DIR"]).expanduser()
        if env.get("SHOPEE_LOG_DIR"):
            s.log_dir = Path(env["SHOPEE_LOG_DIR"]).expanduser()
        if env.get("SHOPEE_DEBUG_DIR"):
            s.debug_dir = Path(env["SHOPEE_DEBUG_DIR"]).expanduser()
        if env.get("SHOPEE_COINS_URL"):
            s.coins_url = env["SHOPEE_COINS_URL"]
        s.headless = env.get("HEADLESS", "1").lower() not in ("0", "false", "no")
        s.channel = env.get("BROWSER_CHANNEL") or None
        s.executable_path = env.get("BROWSER_PATH") or None
        s.state_timeout_s = float(env.get("STATE_TIMEOUT", s.state_timeout_s))
        s.telegram_token = env.get("TELEGRAM_BOT_TOKEN") or None
        s.telegram_chat_id = env.get("TELEGRAM_CHAT_ID") or None
        s.notify_success = env.get("NOTIFY_SUCCESS", "0").lower() in ("1", "true", "yes")
        return s


# --- Page text Shopee shows (zh-TW). Several variants each, because Shopee
# --- renames these occasionally. Add new wording here if the UI changes.
TEXT_CHECKIN_BUTTON = re.compile(r"完成簽到|今日簽到|簽到領取|立即簽到|領取蝦幣")
TEXT_ALREADY = re.compile(r"明天再回來|明日再來|今日已簽到|已完成簽到")
TEXT_VERIFY = re.compile(
    r"使用簡訊驗證|透過電子郵件連結驗證|點擊以重新載入頁面|身份驗證已遭到拒絕|已達到今日驗證次數上限|驗證碼"
)
LOGIN_URL_RE = re.compile(r"/buyer/login|/buyer/signup")
VERIFY_URL_RE = re.compile(r"/verify/|/verification|captcha", re.I)
CHECKIN_API_RE = re.compile(r"/coins?/.*check_?in|checkin", re.I)
BALANCE_RE = re.compile(r"(\d[\d,]*)\s*(?:蝦幣|枚)")


log = logging.getLogger("shopee")


def setup_logging(log_dir: Path, debug: bool = False) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s")
    log.setLevel(logging.DEBUG if debug else logging.INFO)
    log.handlers.clear()
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    fh = logging.FileHandler(log_dir / datetime.now().strftime("shopee.%Y-%m.log"), encoding="utf-8")
    fh.setFormatter(fmt)
    log.addHandler(sh)
    log.addHandler(fh)


def notify(s: Settings, text: str) -> None:
    """Send a Telegram message if TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID are set."""
    if not (s.telegram_token and s.telegram_chat_id):
        return
    try:
        data = urllib.parse.urlencode({"chat_id": s.telegram_chat_id, "text": text}).encode()
        url = f"https://api.telegram.org/bot{s.telegram_token}/sendMessage"
        urllib.request.urlopen(url, data=data, timeout=15).read()
    except Exception as e:  # never let notification failure break the run
        log.warning("Telegram notify failed: %r", e)


def open_context(p, s: Settings, headless: bool) -> BrowserContext:
    s.profile_dir.mkdir(parents=True, exist_ok=True)
    kwargs = dict(
        user_data_dir=str(s.profile_dir),
        headless=headless,
        locale="zh-TW",
        timezone_id="Asia/Taipei",
        viewport={"width": 1280, "height": 900},
    )
    if s.executable_path:
        kwargs["executable_path"] = s.executable_path
    elif s.channel:
        kwargs["channel"] = s.channel
    return p.chromium.launch_persistent_context(**kwargs)


def first_page(ctx: BrowserContext) -> Page:
    return ctx.pages[0] if ctx.pages else ctx.new_page()


def _visible(page: Page, pattern: re.Pattern) -> bool:
    try:
        loc = page.get_by_text(pattern)
        n = loc.count()
        for i in range(min(n, 5)):
            if loc.nth(i).is_visible():
                return True
    except PlaywrightError:
        pass
    return False


def detect_state(page: Page) -> str | None:
    """One snapshot of what the coins page is showing. None = still loading."""
    url = page.url
    if LOGIN_URL_RE.search(url):
        return "login"
    if VERIFY_URL_RE.search(url) or _visible(page, TEXT_VERIFY):
        return "verify"
    if _visible(page, TEXT_ALREADY):
        return "already"
    if _visible(page, TEXT_CHECKIN_BUTTON):
        return "can_checkin"
    return None


def wait_for_state(page: Page, timeout_s: float, wanted: set[str] | None = None) -> str | None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        st = detect_state(page)
        if st and (wanted is None or st in wanted):
            return st
        page.wait_for_timeout(500)
    return None


def read_balance(page: Page) -> str | None:
    try:
        body = page.inner_text("body", timeout=3000)
    except PlaywrightError:
        return None
    m = BALANCE_RE.search(body)
    return m.group(1) if m else None


def dump_debug(page: Page, s: Settings, tag: str) -> Path | None:
    try:
        s.debug_dir.mkdir(parents=True, exist_ok=True)
        stem = s.debug_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{tag}"
        page.screenshot(path=f"{stem}.png", full_page=True)
        Path(f"{stem}.html").write_text(page.content(), encoding="utf-8")
        log.error("Debug dump saved: %s.png / .html (url=%s)", stem, page.url)
        return stem
    except Exception as e:
        log.warning("Could not save debug dump: %r", e)
        return None


def click_checkin(page: Page) -> None:
    loc = page.get_by_text(TEXT_CHECKIN_BUTTON)
    for i in range(min(loc.count(), 5)):
        el = loc.nth(i)
        if el.is_visible():
            el.click()
            return
    raise RuntimeError("check-in button disappeared before click")


def run_checkin(page: Page, s: Settings) -> Exit:
    api_hits: list[dict] = []

    def on_response(resp: Response) -> None:
        if resp.request.method == "POST" and CHECKIN_API_RE.search(resp.url):
            try:
                api_hits.append({"url": resp.url, "status": resp.status, "body": resp.json()})
            except Exception:
                api_hits.append({"url": resp.url, "status": resp.status})

    page.on("response", on_response)

    log.info("Open %s", s.coins_url)
    page.goto(s.coins_url, wait_until="domcontentloaded", timeout=60_000)

    state = wait_for_state(page, s.state_timeout_s)
    log.info("Page state: %s (url=%s)", state, page.url)

    if state == "login":
        return Exit.NEED_LOGIN
    if state == "verify":
        dump_debug(page, s, "verify")
        return Exit.NEED_VERIFY
    if state == "already":
        log.info("今天已經簽到過了，目前蝦幣：%s", read_balance(page) or "?")
        return Exit.ALREADY
    if state != "can_checkin":
        dump_debug(page, s, "unknown")
        return Exit.UNKNOWN_STATE

    before = read_balance(page)
    log.info("簽到前蝦幣：%s，按下簽到", before or "?")
    click_checkin(page)

    after_state = wait_for_state(page, s.state_timeout_s, wanted={"already", "verify", "login"})
    for hit in api_hits:
        log.info("check-in API: %s -> %s %s", hit["url"], hit["status"], json.dumps(hit.get("body"), ensure_ascii=False)[:300])

    if after_state == "already":
        log.info("簽到成功，目前蝦幣：%s", read_balance(page) or "?")
        return Exit.SUCCESS
    if after_state in ("verify", "login"):
        dump_debug(page, s, "after-click-" + after_state)
        return Exit.NEED_VERIFY
    # No confirmation text, but the API might have said OK.
    if any(h.get("status") == 200 for h in api_hits):
        log.warning("沒看到確認文字，但簽到 API 回 200，視為成功")
        return Exit.SUCCESS
    dump_debug(page, s, "after-click-unknown")
    return Exit.UNKNOWN_STATE


def cmd_checkin(s: Settings) -> int:
    with sync_playwright() as p:
        ctx = open_context(p, s, headless=s.headless)
        page = first_page(ctx)
        try:
            code = run_checkin(page, s)
        except Exception as e:
            log.exception("Unexpected error: %r", e)
            dump_debug(page, s, "error")
            code = Exit.ERROR
        finally:
            ctx.close()

    messages = {
        Exit.SUCCESS: "✅ 蝦皮簽到成功",
        Exit.ALREADY: "ℹ️ 蝦皮今天已簽到",
        Exit.NEED_LOGIN: "⚠️ 蝦皮登入已失效，請執行 `python shopee_checkin.py login`",
        Exit.NEED_VERIFY: "⚠️ 蝦皮要求驗證，請執行 `python shopee_checkin.py login` 手動完成",
        Exit.UNKNOWN_STATE: "❌ 蝦皮簽到頁面無法辨識（可能改版），請看 debug/ 截圖",
        Exit.ERROR: "❌ 蝦皮簽到發生錯誤，請看 log",
    }
    msg = messages[code]
    (log.info if code in (Exit.SUCCESS, Exit.ALREADY) else log.error)("%s (exit %d)", msg, code)
    if code not in (Exit.SUCCESS, Exit.ALREADY) or s.notify_success:
        notify(s, msg)
    return int(code)


def cmd_login(s: Settings) -> int:
    log.info("開啟瀏覽器，請在視窗中自行登入蝦皮（含簡訊/Email 驗證）。最多等 %d 分鐘。", s.login_timeout_s // 60)
    with sync_playwright() as p:
        ctx = open_context(p, s, headless=False)
        page = first_page(ctx)
        try:
            page.goto(s.login_url, wait_until="domcontentloaded", timeout=60_000)
            deadline = time.monotonic() + s.login_timeout_s
            while time.monotonic() < deadline:
                if page.is_closed():
                    page = first_page(ctx)
                if page.url.startswith(s.coins_url) and detect_state(page) in ("can_checkin", "already"):
                    log.info("登入成功，session 已存到 %s", s.profile_dir)
                    page.wait_for_timeout(2000)  # let cookies flush
                    return 0
                page.wait_for_timeout(1000)
            log.error("等待登入逾時")
            return int(Exit.NEED_LOGIN)
        finally:
            ctx.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Shopee TW daily coin check-in (Playwright)")
    ap.add_argument("command", choices=["checkin", "login"], nargs="?", default="checkin")
    ap.add_argument("--headed", action="store_true", help="show the browser window during checkin")
    ap.add_argument("--debug", action="store_true", help="verbose logging")
    args = ap.parse_args(argv)

    s = Settings.from_env()
    if args.headed:
        s.headless = False
    setup_logging(s.log_dir, args.debug)

    if args.command == "login":
        return cmd_login(s)
    return cmd_checkin(s)


if __name__ == "__main__":
    sys.exit(main())
