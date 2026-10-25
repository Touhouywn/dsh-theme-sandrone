// Audit the theme's custom-property names against the DSH design token sheets.
//
//   node tools/audit-tokens.mjs <dsh-client-bundle.js> [theme.css] [app.css]
//   DSH_CLIENT_BUNDLE=<dsh-client-bundle.js> DSH_APP_CSS=<app.css> node tools/audit-tokens.mjs
//
// The client bundle embeds the design token sheets; app.css carries the
// component-scoped tokens the theme also overrides. Both are optional inputs:
// pass the ones you have, and the theme stylesheet defaults to ../theme/theme.css.
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const clientPath = process.argv[2] ?? process.env.DSH_CLIENT_BUNDLE
const themePath = process.argv[3] ?? resolve(here, '../theme/theme.css')
const appCssPath = process.argv[4] ?? process.env.DSH_APP_CSS

if (!clientPath) {
  console.error('usage: node tools/audit-tokens.mjs <dsh-client-bundle.js> [theme.css] [app.css]')
  console.error('   or: DSH_CLIENT_BUNDLE=<dsh-client-bundle.js> DSH_APP_CSS=<app.css> node tools/audit-tokens.mjs')
  process.exit(64)
}

const theme = readFileSync(themePath, 'utf8')
const sources = [readFileSync(clientPath, 'utf8')]
if (appCssPath) sources.push(readFileSync(appCssPath, 'utf8'))

// Every `--dsw-*` / `--dsh-*` / `--ds-*` / `--shiki-*` name declared by the design sheets.
const declared = new Set()
for (const source of sources) {
  for (const match of source.matchAll(/(--(?:dsw|dsh|ds|shiki)[a-z0-9-]*):/g)) declared.add(match[1])
}

// Custom properties the DSH stylesheets only *read* (no fallback in the sheet) still count as known.
const consumedButUndeclared = new Set()
for (const source of sources) {
  for (const match of source.matchAll(/var\((--(?:dsw|dsh|ds|shiki)[a-z0-9-]*?)(?:,|\))/g)) {
    if (!declared.has(match[1])) consumedButUndeclared.add(match[1])
  }
}

// Names the theme declares, in order of appearance.
const mine = [...theme.matchAll(/^\s*(--(?:dsw|dsh|ds|shiki)[a-z0-9-]*):/gm)].map((m) => m[1])

const unknown = mine.filter((n) => !declared.has(n) && !consumedButUndeclared.has(n))
const known = mine.length - unknown.length

console.log(`design sheets declare ${declared.size} tokens`)
console.log(`theme declares         ${mine.length} (unique ${new Set(mine).size})`)
console.log(`known                  ${known}`)
console.log(`unknown                ${unknown.length}`)
for (const name of unknown) console.log(`  ? ${name}`)

// Brace balance sanity check.
let depth = 0
let min = 0
for (const ch of theme) {
  if (ch === '{') depth += 1
  if (ch === '}') depth -= 1
  if (depth < min) min = depth
}
console.log(`brace balance          ${depth === 0 ? 'ok' : `BROKEN (${depth})`}${min < 0 ? ', underflow' : ''}`)
