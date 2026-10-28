import json
import threading
import time
import urllib.request

URL = "http://127.0.0.1:54306/sandrone/tts"


def call(text):
    body = json.dumps({"text": text, "stream": False}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as r:
        data = r.read()
    return time.time() - t0, len(data)


C = "先单跑一条，用来做基准，这句不进并发。"
A = "推演完了。这具机偶没在偷懒，你也没。这句是并发测试的第一条。"
B = "第二句。我在听，你慢慢说，不着急。这句是并发测试的第二条。"
A = A + "（甲）"
B = B + "（乙）"

t0 = time.time()
ta, sa = call(C)
single = time.time() - t0
print(f"单条: {single:.2f}s  {sa}B")

results = {}


def worker(name, text):
    results[name] = call(text)


t0 = time.time()
th1 = threading.Thread(target=worker, args=("a", A))
th2 = threading.Thread(target=worker, args=("b", B))
th1.start()
th2.start()
th1.join()
th2.join()
wall = time.time() - t0
print(f"两条并发: 墙钟 {wall:.2f}s  A={results['a'][0]:.2f}s  B={results['b'][0]:.2f}s")
print(f"加速比: {single * 2 / wall:.2f}x （1.0 = 完全串行，2.0 = 完全并行）")
