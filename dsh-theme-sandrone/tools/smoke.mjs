// Offline smoke test for the Sandrone theme host half: no DSH required.
import { apply, name, inject } from '../lib/index.js'

const routes = []
const injections = new Map()
const disposers = []

const ctx = {
  effect(fn, label) {
    const dispose = fn()
    disposers.push({ label, dispose })
    return dispose
  },
  on(event, handler, options) {
    injections.set(event, { handler, options })
    return () => injections.delete(event)
  },
  webServer: {
    register(route) {
      routes.push(route)
      return () => {
        const at = routes.indexOf(route)
        if (at !== -1) routes.splice(at, 1)
      }
    },
  },
}

apply(ctx, {})

console.log('name     :', name)
console.log('inject   :', inject)
console.log('routes   :', routes.map((r) => `${r.kind} ${r.path}`).join(', '))

// --- index injections ------------------------------------------------------
const table = []
injections.get('webserver/index-inject').handler(table)
console.log('rows     :', table.map((r) => r.kind).join(', '))

// --- asset route -----------------------------------------------------------
function request(url, method = 'GET', headers = {}) {
  return new Promise((resolve, reject) => {
    const chunks = []
    const res = {
      status: 0,
      headers: {},
      writeHead(status, extra = {}) {
        this.status = status
        this.headers = extra
      },
      end(body) {
        if (body) chunks.push(Buffer.from(body))
        resolve({ status: this.status, headers: this.headers, body: Buffer.concat(chunks) })
      },
      on() {},
      once() {},
    }
    Promise.resolve(routes[0].handler({ method, url, headers }, res)).catch(reject)
  })
}

for (const path of ['/theme-sandrone/theme.css', '/theme-sandrone/background.webp', '/theme-sandrone/../package.json', '/theme-sandrone/nope.webp']) {
  const r = await request(path)
  console.log(`GET ${path.padEnd(38)} -> ${r.status} ${r.headers['content-type'] ?? ''} ${r.body.length} B`)
}

const css = await request('/theme-sandrone/theme.css')
const etag = css.headers.etag
const revalidated = await request('/theme-sandrone/theme.css', 'GET', { 'if-none-match': etag })
console.log(`revalidate (same etag)                -> ${revalidated.status}`)
const head = await request('/theme-sandrone/background.webp', 'HEAD')
console.log(`HEAD background.webp                  -> ${head.status} ${head.headers['content-length']} B declared`)
const post = await request('/theme-sandrone/theme.css', 'POST')
console.log(`POST theme.css                        -> ${post.status} ${post.headers.allow ?? ''}`)

// --- teardown --------------------------------------------------------------
for (const entry of disposers) entry.dispose()
console.log('routes after dispose:', routes.length)
