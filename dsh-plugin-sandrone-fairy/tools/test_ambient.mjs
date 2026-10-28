// 验证时段台词：把 idleMurmur 抽出来，在几个假时刻各跑 400 次，看落到哪条。
import fs from 'node:fs'
import vm from 'node:vm'
import { fileURLToPath } from 'node:url'

const src = fs.readFileSync(fileURLToPath(new URL('../client.js', import.meta.url)), 'utf8').replace(/\r\n/g, '\n')
const start = src.indexOf('const AMBIENT = [')
const fnStart = src.indexOf('function idleMurmur(', start)
const fnEnd = src.indexOf('\n    }', fnStart) + '\n    }'.length
const code = src.slice(start, fnEnd)

const MURMURS = [{ text: 'generic', clip: 'whisper-idle' }]
let fakeNow = 0
const ctx = { MURMURS, console }
vm.createContext(ctx)
vm.runInContext(code + '\n;this.idleMurmur = idleMurmur;this.resetAmbient = () => { ambientAt = 0 };', Object.assign(ctx, {
  Date: class extends Date {
    constructor(...args) { if (!args.length) super(fakeNow); else super(...args) }
    static now() { return fakeNow }
  },
  ambientAt: 0,
}))
const idleMurmur = ctx.idleMurmur

function atHour(hour, idleMs) {
  fakeNow = new Date(2026, 9, 26, hour, 30, 0).getTime()
  const tally = new Map()
  for (let i = 0; i < 400; i += 1) {
    ctx.resetAmbient()          // 绕开 2.5 分钟最小间隔，只看时段分配
    const r = idleMurmur(idleMs || 0)
    const key = r ? r.clip : 'null'
    tally.set(key, (tally.get(key) || 0) + 1)
  }
  return [...tally.entries()].sort((a, b) => b[1] - a[1])
}

for (const h of [2, 7, 12, 15, 18, 21]) {
  console.log(String(h).padStart(2) + ' 点:', atHour(h).map(([k, v]) => `${k}:${v}`).join('  '))
}
console.log('长时间空闲(23 点, idle 60min):', atHour(23, 60 * 60 * 1000).map(([k, v]) => `${k}:${v}`).join('  '))
