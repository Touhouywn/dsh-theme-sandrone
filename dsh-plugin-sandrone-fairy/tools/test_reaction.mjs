// 验证：场景反应（预制音频）先播，回复语音接在它后面，两者不重叠。
import fs from 'node:fs'
import vm from 'node:vm'

const src = fs.readFileSync(process.env.TEMP + '\\speaker_src.js', 'utf8')
const t0 = Date.now()
const now = () => Date.now() - t0

class FakeBuffer {
  constructor(frames, rate) { this.duration = frames / rate }
  getChannelData() { return new Float32Array(this.duration * 32000) }
}
const nodes = []
class FakeNode {
  constructor(buf) { this.buffer = buf }
  connect() { return this }
  start(at) { nodes.push({ at: at * 1000, end: (at + this.buffer.duration) * 1000, dur: this.buffer.duration }) }
  stop() {}
}
class FakeCtx {
  constructor() { this.state = 'running'; this.destination = {}; this._t0 = Date.now() }
  get currentTime() { return (Date.now() - this._t0) / 1000 }
  createGain() { return { gain: { value: 1 }, connect() {} } }
  createBuffer(ch, frames, rate) { return new FakeBuffer(frames, rate) }
  createBufferSource() { return new FakeNode(null) }
  async decodeAudioData() { return { duration: 2.0 } }
  resume() { return Promise.resolve() }
}

const sandbox = {
  console,
  window: {
    AudioContext: FakeCtx,
    fetch: (url, opts) => fetch('http://127.0.0.1:54306' + url, opts),
    setTimeout, clearTimeout, AbortController,
  },
  URL, Promise, Math, Date, JSON, Set, Map,
  localStorage: { getItem: () => null, setItem() {} },
}
sandbox.globalThis = sandbox
vm.createContext(sandbox)
vm.runInContext(src + '\n;globalThis.__SPEAKER = SPEAKER;', sandbox)
const SPEAKER = sandbox.__SPEAKER
SPEAKER.signal = () => {}
SPEAKER.notify = () => {}
SPEAKER.resting = () => false
SPEAKER.resolvedEngine = () => 'clone'

let reactAt = null
SPEAKER.sayReaction('react-thanks', '谢什么。', () => { reactAt = now() })
await new Promise((r) => setTimeout(r, 600))
SPEAKER.enqueue('不用谢，齿轮转得稳就行。', () => {})
// 等到队列跑完（后台流水线不阻塞调用方）
for (let i = 0; i < 60; i += 1) {
  await new Promise((r) => setTimeout(r, 500))
  if (nodes.length >= 2 && SPEAKER.queue.length === 0 && !SPEAKER.playingQueue && now() > nodes[0].end + 200) break
}

const clip = nodes[0]
const reply = nodes.find((n) => n.at > clip.at)
console.log('块数:', nodes.length)
console.log('预制台词:', Math.round(clip.at), '→', Math.round(clip.end), 'ms')
console.log('回复首块:', reply ? Math.round(reply.at) : null, 'ms')
console.log('文字回调(ms):', reactAt)
const ok = Boolean(clip && reply) && reply.at >= clip.end - 40 && reactAt !== null && reactAt < clip.end
console.log(ok ? 'PASS：预制台词先出声，回复排在它后面，没有重叠' : 'FAIL')
process.exit(ok ? 0 : 1)
