"""截图验证 A/B 抽听页能正常渲染与播放。"""

import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

AB = Path(r"E:\AI-theme\columbina\.assets-src\voice\v2\01-separate\ab-listen")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
server = ThreadingHTTPServer(("127.0.0.1", port), partial(Quiet, directory=str(AB)))
threading.Thread(target=server.serve_forever, daemon=True).start()

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=EDGE, headless=True,
                                 args=["--disable-features=NetworkServiceSandbox",
                                       "--autoplay-policy=no-user-gesture-required"])
    page = browser.new_page(viewport={"width": 1080, "height": 780})
    page.on("pageerror", lambda e: print("PAGEERROR", str(e)[:200]))
    page.goto(f"http://127.0.0.1:{port}/listen.html", wait_until="load", timeout=30000)
    page.wait_for_timeout(400)
    print("rows:", page.locator("tbody tr").count())
    print("sections:", page.locator("section").count())
    page.locator("tbody tr .ab").first.click()
    page.wait_for_timeout(600)
    print("player:", page.evaluate("document.getElementById('player').src.slice(0,28)"))
    print("now:", page.locator("#now").inner_text())
    page.screenshot(path=str(AB / "listen-page.png"))
    print("shot ok")
    browser.close()
server.shutdown()
