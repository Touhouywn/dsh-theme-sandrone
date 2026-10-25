/**
 * Sandrone · 人偶工坊 — DeepSeek Harness theme plugin (host half).
 *
 * What it does, and nothing else:
 *   1. serves the theme's own assets (`theme.css`, `background.webp`) from
 *      `/theme-sandrone/*` on the host web server, so the stylesheet and the
 *      artwork can be edited in place without rebuilding anything;
 *   2. contributes three index-injection rows — the stylesheet link, an image
 *      preload, and the shim that keeps `body[data-ds-dark-theme]` set while
 *      the theme is mounted (the skin is dark-only).
 *
 * There is no model-facing surface: no tool, no prompt section, no request.
 */
import { stat, readFile } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

/** Stable Cordis plugin name. */
export const name = 'theme-sandrone'

/** The asset route needs the host web server; the plugin stays pending without one. */
export const inject = ['webServer']

/**
 * Route prefix owned by this plugin. No trailing slash: the web server matches
 * prefixes as `pathname === prefix || pathname.startsWith(prefix + "/")`, so a
 * trailing slash here would build `"...//"` and never match.
 */
const ROUTE = '/theme-sandrone'

const PLUGIN_ROOT = resolve(fileURLToPath(new URL('.', import.meta.url)), '..')

/** Public path → file on disk. An explicit allow-list, so no request can walk out of the package. */
const FILES = new Map([
  ['theme.css', { file: join(PLUGIN_ROOT, 'theme', 'theme.css'), type: 'text/css; charset=utf-8' }],
  ['background.webp', { file: join(PLUGIN_ROOT, 'assets', 'background.webp'), type: 'image/webp' }],
  ['opening.json', { file: join(PLUGIN_ROOT, 'assets', 'opening.json'), type: 'application/json; charset=utf-8' }],
  ['trace.mp4', { file: join(PLUGIN_ROOT, 'assets', 'trace.mp4'), type: 'video/mp4' }],
  ['opening.mp4', { file: join(PLUGIN_ROOT, 'assets', 'opening.mp4'), type: 'video/mp4' }],
  ['icon.png', { file: join(PLUGIN_ROOT, 'assets', 'icon.png'), type: 'image/png' }],
  ['gear.png', { file: join(PLUGIN_ROOT, 'assets', 'gear.png'), type: 'image/png' }],
  ['iris.png', { file: join(PLUGIN_ROOT, 'assets', 'iris.png'), type: 'image/png' }],
  ['strings.png', { file: join(PLUGIN_ROOT, 'assets', 'strings.png'), type: 'image/png' }],
  ['burst.png', { file: join(PLUGIN_ROOT, 'assets', 'burst.png'), type: 'image/png' }],
  ['cryo.png', { file: join(PLUGIN_ROOT, 'assets', 'cryo.png'), type: 'image/png' }],
  ['skill.png', { file: join(PLUGIN_ROOT, 'assets', 'skill.png'), type: 'image/png' }],
])

/**
 * Requests served per asset since this host process started. `/status` reports
 * them, which is how a theme can be proven live without looking at the window:
 * a mounted theme fetches `theme.css` and `background.webp` at least once.
 */
const HITS = { 'theme.css': 0, 'background.webp': 0 }

/** Last self-check beacon the page sent, and how many arrived. */
let lastReport = null
let reportCount = 0

/**
 * Page-side probe: report what the theme actually sees in the document, so the
 * theme can be debugged from outside the window. Read-only, one tiny request.
 */
const PAGE_REPORT_SCRIPT = `(() => {
  const report = () => {
    const frame = document.querySelector('#root > div:first-child')
    const text = (value) => String(value)
    const facts = new URLSearchParams({
      dark: text(document.body.hasAttribute('data-ds-dark-theme')),
      pref: text(document.documentElement.dataset.dsThemeSource || '-'),
      kids: text((document.getElementById('root') || { childElementCount: -1 }).childElementCount),
      frame: text(frame !== null),
      fcls: text(frame === null ? '-' : String(frame.className).slice(0, 70)),
      center: text(document.querySelector('[class*="centerCol"]') !== null),
      sidebar: text(document.querySelector('[class*="sidebarCol"]') !== null),
      applied: text(getComputedStyle(document.body).getPropertyValue('--sandrone-theme').trim() || '-'),
      base: text(getComputedStyle(document.body).getPropertyValue('--dsw-alias-bg-base').trim()),
      link: text(document.querySelector('link[href*="/theme-sandrone/"]') !== null)
    })
    fetch('/theme-sandrone/report?' + facts.toString(), { cache: 'no-store' }).catch(() => {})
  }
  setTimeout(report, 1200)
})()`

/** Palette hold plus the probe: the body script the index row carries. */
const PAGE_SCRIPT = `(() => {
  const attribute = 'data-ds-dark-theme'
  const hold = () => { if (!document.body.hasAttribute(attribute)) document.body.setAttribute(attribute, '') }
  hold()
  new MutationObserver(hold).observe(document.body, { attributes: true, attributeFilter: [attribute] })
  document.documentElement.style.colorScheme = 'dark'
})()
${PAGE_REPORT_SCRIPT}`

/**
 * Record one page report.
 * @param req - request carrying the facts as query parameters.
 * @param res - response to write.
 */
function serveReport(req, res) {
  const params = new URL(req.url ?? '/', 'http://example.invalid').searchParams
  lastReport = Object.fromEntries(params.entries())
  reportCount += 1
  res.writeHead(204, { 'cache-control': 'no-store' })
  res.end()
}

/**
 * Answer the self-check route: counters plus the paths the theme serves.
 * @param res - response to write.
 */
function serveStatus(res) {
  const body = JSON.stringify({
    theme: 'sandrone-marionette',
    route: ROUTE,
    hits: { ...HITS },
    reportCount,
    lastReport,
  })
  res.writeHead(200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' })
  res.end(body)
}

/**
 * Serve one GET/HEAD request for a themed asset.
 * @param pathname - decoded request pathname.
 * @param req - incoming request (read for `if-none-match`).
 * @param res - response to write.
 */
async function serveAsset(pathname, req, res) {
  const key = pathname.slice(ROUTE.length + 1)
  if (key === 'status') {
    serveStatus(res)
    return
  }
  if (key === 'report') {
    serveReport(req, res)
    return
  }
  const entry = FILES.get(key)
  if (entry === undefined) {
    res.writeHead(404, { 'cache-control': 'no-store' })
    res.end()
    return
  }
  if (HITS[key] !== undefined) HITS[key] += 1
  let info
  try {
    info = await stat(entry.file)
  } catch {
    res.writeHead(404, { 'cache-control': 'no-store' })
    res.end()
    return
  }
  const etag = `"${Math.trunc(info.mtimeMs).toString(36)}-${info.size.toString(36)}"`
  if (req.headers['if-none-match'] === etag) {
    res.writeHead(304, { etag, 'cache-control': 'no-cache' })
    res.end()
    return
  }
  const body = await readFile(entry.file)
  res.writeHead(200, {
    'content-type': entry.type,
    'content-length': String(body.byteLength),
    'cache-control': 'no-cache',
    etag,
  })
  res.end(req.method === 'HEAD' ? undefined : body)
}

/**
 * Mount the theme on the running host.
 * @param ctx - plugin context carrying the web server.
 * @param config - optional plugin config: `art` (default true), `forceDark` (default true).
 */
export function apply(ctx, config = {}) {
  const art = config?.art !== false
  const forceDark = config?.forceDark !== false

  ctx.effect(
    () =>
      ctx.webServer.register({
        kind: 'prefix',
        path: ROUTE,
        handler: async (req, res) => {
          if (req.method !== 'GET' && req.method !== 'HEAD') {
            res.writeHead(405, { allow: 'GET, HEAD' })
            res.end()
            return
          }
          const { pathname } = new URL(req.url ?? '/', 'http://localhost')
          await serveAsset(pathname, req, res)
        },
      }),
    'theme-sandrone: asset route',
  )

  ctx.on(
    'webserver/index-inject',
    (table) => {
      table.push({ kind: 'html', placement: 'head', html: `<link rel="stylesheet" href="${ROUTE}/theme.css">` })
      if (art) {
        table.push({
          kind: 'html',
          placement: 'head',
          html: `<link rel="preload" as="image" href="${ROUTE}/background.webp">`,
        })
      }
      if (forceDark) {
        // The skin is dark-only: hold the palette attribute while the theme is
        // mounted, whatever the Appearance setting says. Disabling the plugin
        // removes the shim, and the shell's own presenter takes over again.
        table.push({
          kind: 'script',
          placement: 'body',
          text: PAGE_SCRIPT,
        })
      } else {
        table.push({ kind: 'script', placement: 'body', text: PAGE_REPORT_SCRIPT })
      }
    },
    { prepend: false },
  )
}
