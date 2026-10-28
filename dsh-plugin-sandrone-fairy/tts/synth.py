"""Sandrone TTS bridge: Edge Read-Aloud neural voices, no training needed.

Reads one JSON request from stdin, writes MP3 bytes to stdout.

  {"text": "...", "voice": "zh-CN-XiaoxiaoNeural", "rate": "-8%", "pitch": "-12Hz"}
"""
import asyncio
import json
import sys


async def main():
    raw = sys.stdin.buffer.read()
    req = json.loads(raw.decode("utf-8") or "{}")
    text = (req.get("text") or "").strip()
    if not text:
        sys.stderr.write("empty text\n")
        return 2

    try:
        import edge_tts
    except Exception as exc:  # pragma: no cover
        sys.stderr.write("edge_tts missing: %s\n" % (exc,))
        return 3

    voice = req.get("voice") or "zh-CN-XiaoxiaoNeural"
    rate = req.get("rate") or "-8%"
    pitch = req.get("pitch") or "-12Hz"

    out = sys.stdout.buffer
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    async for chunk in comm.stream():
        if chunk.get("type") == "audio" and chunk.get("data"):
            out.write(chunk["data"])
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
