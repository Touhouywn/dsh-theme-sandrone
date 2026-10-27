"""看一眼抽听页面渲染成什么样（截图 + 点一次播放按钮）。"""

import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

AUDIT = Path(r"E:\AI-theme\columbina\.assets-src\voice\v2\04-audit")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
server = ThreadingHTTPServer(("127.0.0.1", port), partial(Quiet, directory=str(AUDIT)))
threading.Thread(target=server.serve_forever, daemon=True).start()

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=EDGE, headless=True,
                                 args=["--disable-features=NetworkServiceSandbox", "--autoplay-policy=no-user-gesture-required"])
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda e: print("PAGEERROR", str(e)[:200]))
    page.goto(f"http://127.0.0.1:{port}/listen.html", wait_until="load", timeout=60000)
    page.wait_for_timeout(500)
    print("rows:", page.locator("tr[data-id]").count())
    print("sections:", page.locator("section").count())
    page.locator("tr[data-id] .play").first.click()
    page.wait_for_timeout(800)
    print("player src set:", page.evaluate("document.getElementById('player').src.slice(0, 30)"))
    print("now:", page.locator("#now").inner_text())
    print("playing row:", page.locator("tr.playing").count())
    page.screenshot(path=str(AUDIT / "listen-page.png"), full_page=False)
    print("shot ok")
    browser.close()
server.shutdown()
