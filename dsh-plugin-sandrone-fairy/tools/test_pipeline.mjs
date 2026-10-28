// 流水线验证：三句话，应该做到「第 N 句在播时，第 N+1 句已经在生成」。
// 用假 AudioContext（currentTime 按真实时间推进）跑真请求；记录每句的生成窗口，
// 断言后一句「开始生成」早于前一句「生成结束 + 该句音频长度」，即确实重叠。
import fs from 'node:fs'
import vm from 'node:vm'

const src = fs.readFileSync(process.env.TEMP + '\\speaker_src.js', 'utf8')
const t0 = Date.now()
const now = () => Date.now() - t0

class FakeBuffer {
  constructor(frames, rate) { this.duration = frames / rate; this.data = new Float32Array(frames) }
  getChannelData() { return this.data }
}
const nodes = []
class FakeNode {
  constructor(buf) { this.buffer = buf }
  connect() { return this }
  start(at) { nodes.push({ at: at * 1000, end: (at + this.buffer.duration) * 1000 }) }
  stop() {}
}
class FakeCtx {
  constructor() { this.state = 'running'; this.destination = {}; this._t0 = Date.now() }
  get currentTime() { return (Date.now() - this._t0) / 1000 }
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

// 记录每句的生成窗口
const gens = []
const rawBegin = SPEAKER.beginStream.bind(SPEAKER)
let idx = -1
SPEAKER.beginStream = async (line, onStart) => {
  idx += 1
  const rec = { idx, start: now(), end: null, ok: null }
  gens.push(rec)
  rec.ok = await rawBegin(line, onStart)
  rec.end = now()
  return rec.ok
}

const lines = [
  '齿轮咬合得正好，我听着呢。',
  '你刚才那句话，我推演了两遍，结论是——你说得对。',
  '好了，先到这儿。剩下的明天再想。',
].map((l) => l + '（流水线测试）')

const starts = []
for (const line of lines) SPEAKER.queue.push({ line, onStart: () => starts.push(now()) })
await SPEAKER.pumpQueue()
const total = now()

const audioEnd = nodes.reduce((m, n) => Math.max(m, n.end), 0)
console.log('总耗时(ms):', total)
console.log('生成窗口:', gens.map((g) => `#${g.idx} ${g.start}→${g.end}`).join('  '))
console.log('文字出现(ms):', starts.join(' / '))
console.log('音频排期结束(ms):', Math.round(audioEnd), ' 分块数:', nodes.length)

// 第 2 句开始生成的时刻，应早于「第 1 句生成结束 + 它的音频时长」——说明在上一句播放期间就已开跑。
const firstAudioSec = Math.max(...nodes.filter((n) => n.at < (gens[1] ? gens[1].start : Infinity)).map((n) => n.end), 0)
const overlap = gens.length === 3 && gens[1].start < firstAudioSec
const pass = gens.length === 3 && gens.every((g) => g.ok) && overlap
console.log(overlap
  ? `PASS：第 2 句在 ${gens[1].start}ms 开始生成，而第 1 句音频到 ${Math.round(firstAudioSec)}ms 才播完`
  : 'FAIL：仍然是串行（下一句要等上一句播完才开始生成）')
process.exit(pass ? 0 : 1)
