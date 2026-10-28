// 流式播放的单元测试：把 client.js 里的 SPEAKER 抽出来，在 Node 里用假 AudioContext 跑一遍，
// 验证「首块到达就出声」这条链是通的（真浏览器里听感另说，但代码路径必须没有运行时错误）。
import fs from 'node:fs'
import vm from 'node:vm'

const src = fs.readFileSync(process.env.TEMP + '\\speaker_src.js', 'utf8')

const events = []
const scheduled = []

class FakeBuffer {
  constructor(frames, rate) {
    this.duration = frames / rate
    this.data = new Float32Array(frames)
  }
  getChannelData() { return this.data }
}

class FakeNode {
  constructor(buf) { this.buffer = buf }
  connect() { return this }
  start(at) { scheduled.push({ at, duration: this.buffer.duration }) }
  stop() {}
}

class FakeCtx {
  constructor() { this.currentTime = 0; this.state = 'running'; this.destination = {} }
  createGain() { return { gain: { value: 1 }, connect() {} } }
  createBuffer(ch, frames, rate) { return new FakeBuffer(frames, rate) }
  createBufferSource() { return new FakeNode(null) }
  resume() { return Promise.resolve() }
}

const sandbox = {
  console,
  window: {
    AudioContext: FakeCtx,
    fetch: (url, opts) => fetch('http://127.0.0.1:54306' + url, opts),
    setTimeout, clearTimeout,
    AbortController,
  },
  URL,
  Promise,
  Math,
  Date,
  JSON,
  Set,
  Map,
  localStorage: { getItem: () => null, setItem() {} },
}
sandbox.globalThis = sandbox
vm.createContext(sandbox)
vm.runInContext(src + '\n;globalThis.__SPEAKER = SPEAKER;', sandbox)
const SPEAKER = sandbox.__SPEAKER

SPEAKER.signal = (kind, detail) => events.push([kind, detail && detail.text])
SPEAKER.notify = () => {}
SPEAKER.resting = () => false
SPEAKER.resolvedEngine = () => 'clone'

const line = '推演完了。这具机偶没在偷懒——你也没。'
const t0 = Date.now()
let startedAt = null
const ok = await SPEAKER.speakStream(line, () => { startedAt = Date.now() - t0 })
const total = Date.now() - t0

console.log('speakStream ->', ok)
console.log('首块出声(ms):', startedAt)
console.log('整句结束(ms):', total)
console.log('调度块数:', scheduled.length, ' 总时长:', scheduled.reduce((s, x) => s + x.duration, 0).toFixed(2) + 's')
console.log('事件顺序:', events.map((e) => e[0]).join(' → '))

const pass = ok && startedAt !== null && startedAt < 1500 && scheduled.length > 1
console.log(pass ? 'PASS：首块 <1.5s 就出声，且是多块流式' : 'FAIL')
process.exit(pass ? 0 : 1)
