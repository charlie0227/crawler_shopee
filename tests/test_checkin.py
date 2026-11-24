"""Offline tests: shopee.tw is mocked with page.route, so no account/network needed.

Run:  pytest -q
(Set BROWSER_PATH=/path/to/chrome if Playwright's bundled Chromium is not installed.)
"""
import os
import sys
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import shopee_checkin as sc  # noqa: E402

COINS = "https://shopee.tw/shopee-coins"

PAGE_CAN_CHECKIN = """<html><body>
<div id=app>載入中…</div>
<script>
setTimeout(() => {
  document.getElementById('app').innerHTML =
    '<div>蝦幣獎勵</div><div id=bal>123 蝦幣</div><button id=b>完成簽到 +1</button>';
  document.getElementById('b').onclick = async () => {
    await fetch('/mkt/coins/api/v2/checkin_new', {method: 'POST'});
    document.getElementById('bal').textContent = '124 蝦幣';
    document.getElementById('b').textContent = '明天再回來領取 2 蝦幣';
  };
}, 800);  // simulate SPA render delay
</script></body></html>"""

PAGE_ALREADY = "<html><body><div>456 蝦幣</div><button>明天再回來領取 2 蝦幣</button></body></html>"
PAGE_VERIFY = "<html><body><div>請選擇驗證方式</div><div>使用簡訊驗證</div></body></html>"
PAGE_LOGIN = "<html><body><input name=loginKey><input name=password></body></html>"
PAGE_BLANK = "<html><body><div>維護中</div></body></html>"
# Click does nothing visible, but API returns 200.
PAGE_SILENT_OK = """<html><body><button id=b>立即簽到</button><script>
document.getElementById('b').onclick = () => fetch('/mkt/coins/api/v2/checkin_new', {method:'POST'});
</script></body></html>"""


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        kw = {"headless": True}
        if os.environ.get("BROWSER_PATH"):
            kw["executable_path"] = os.environ["BROWSER_PATH"]
        b = p.chromium.launch(**kw)
        yield b
        b.close()


def make_page(browser, coins_html, redirect_to_login=False):
    ctx = browser.new_context(locale="zh-TW")

    def handler(route):
        url = route.request.url
        if "checkin" in url:
            return route.fulfill(status=200, content_type="application/json", body='{"code":0,"data":{"success":true}}')
        if url.startswith(COINS):
            if redirect_to_login:
                return route.fulfill(status=302, headers={"location": "https://shopee.tw/buyer/login?next=x"})
            return route.fulfill(status=200, content_type="text/html; charset=utf-8", body=coins_html)
        if "/buyer/login" in url:
            return route.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE_LOGIN)
        return route.fulfill(status=404, body="")

    ctx.route("https://shopee.tw/**", handler)
    return ctx, ctx.new_page()


@pytest.fixture
def settings(tmp_path):
    s = sc.Settings()
    s.debug_dir = tmp_path / "debug"
    s.state_timeout_s = 5
    sc.setup_logging(tmp_path / "log")
    return s


def run(browser, settings, html, **kw):
    ctx, page = make_page(browser, html, **kw)
    try:
        return sc.run_checkin(page, settings)
    finally:
        ctx.close()


def test_checkin_success(browser, settings):
    assert run(browser, settings, PAGE_CAN_CHECKIN) == sc.Exit.SUCCESS


def test_already_checked_in(browser, settings):
    assert run(browser, settings, PAGE_ALREADY) == sc.Exit.ALREADY


def test_session_expired_redirects_to_login(browser, settings):
    assert run(browser, settings, "", redirect_to_login=True) == sc.Exit.NEED_LOGIN


def test_verification_required(browser, settings):
    assert run(browser, settings, PAGE_VERIFY) == sc.Exit.NEED_VERIFY
    assert any(settings.debug_dir.glob("*verify.png"))


def test_unknown_page_dumps_debug(browser, settings):
    assert run(browser, settings, PAGE_BLANK) == sc.Exit.UNKNOWN_STATE
    assert any(settings.debug_dir.glob("*unknown.png"))
    assert any(settings.debug_dir.glob("*unknown.html"))


def test_success_inferred_from_api(browser, settings):
    assert run(browser, settings, PAGE_SILENT_OK) == sc.Exit.SUCCESS


def test_balance_regex():
    assert sc.BALANCE_RE.search("目前有 1,234 蝦幣").group(1) == "1,234"
