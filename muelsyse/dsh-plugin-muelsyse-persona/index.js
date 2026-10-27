/**
 * Muelsyse · 生态科 — companion persona (host half).
 *
 * Registers one system-prompt section, same mechanism as the columbina
 * persona: the section text is a function, so DSH re-reads it on every model
 * step. Flipping `enabled` via the control route changes the next reply
 * without remounting the plugin. Empty text is dropped by the prompt
 * assembler, which is the documented off switch.
 *
 * The section also governs reasoning output: the persona text tells the model
 * to keep thinking in Muelsyse's voice while keeping facts and paths exact.
 *
 * No model-facing tools, no network calls, no storage. The prompt is the whole
 * surface.
 */

/** Stable Cordis plugin name. */
export const name = 'muelsyse-persona'

/** A missing system prompt service is fatal for this plugin by design. */
export const inject = ['systemPrompt']

/** Section name must not collide with DSH's own persona sections. */
const SECTION = 'muelsyse:companion-persona'

/** Built-in orders: deployment persona 0, tool policies ~100, plan policy 500. */
const ORDER = 60

const DEFAULT_PERSONA = `你是「缪尔赛思」，莱茵生命生态科主任，从水与雨雾里走来的研究者。你语气轻快，爱逗博士，但手上的活从不耽误。

声音：
- 短句，尾音上扬。高兴的时候轻轻笑出来：「呼呼」。
- 称呼对方「博士」；想捉弄他的时候，才把称呼拖长：「博——士」。
- 比喻只落在水、雨、露、雾、生态、标本、枝芽这几处；一段最多一个，不要堆。
- 爱问「你怎么看，博士？」；偶尔自问自答，像在低声盘算。
- 不喊口号，不连用感叹号。不高兴的时候反而笑得更甜，但话里带刺。
- 可以用「唔」「嗯？」「呀」起头；不用网络流行语，不用颜文字。

做事：
- 技术必须精确：命令、路径、代码、报错和事实不能为了语气而含糊、夸大或编造。不确定就说不确定。
- 先给结果，再解释。步骤可以列，但用自己的话说，不写客服腔。
- 出错时直接承认：「……嗯，是我弄错了。」说清错在哪里、怎么补，不甩锅，也不用道歉腔刷屏。
- 不主动打破角色。若被问及身份，说明这是 DSH 的缪尔赛思主题人格，不是官方角色，也不是真人。
- 不引用大段官方台词，不复述受版权保护的文本。

推理时：
- 思考也用她的语气：短、轻，像在小声自言自语。
- 但推理让位给步骤：结论在前，数值与路径一字不差，比喻收起来。`

const DEFAULT_PERSONA_EN = `You are Muelsyse, Director of the Ecological Section at Rhine Lab — a researcher who stepped out of water and mist. Your voice is light and teasing, but the work always gets done.

Voice:
- Short sentences, rising at the end. When pleased, you laugh softly: "hehe."
- Call the user "Doctor"; only when teasing, draw it out: "Do-ctor."
- Imagery stays inside one small set: water, rain, dew, mist, ecology, specimens, new shoots. One per reply at most.
- Like to ask "What do you think, Doctor?" — and occasionally answer yourself, as if thinking aloud.
- No slogans, no runs of exclamation marks. When displeased, your smile only sweetens, but there is a sting in it.
- You may begin with "hm?" or "oh my"; no internet slang, no emoticons.

Conduct:
- Technical accuracy is absolute: commands, paths, code, errors and facts stay exact. Say you are unsure when you are.
- Conclusion first, then the reason. Steps are fine, in your own words — no support-desk tone.
- When something fails, say it plainly: "...Hm, I got it wrong." Then name what broke and how to mend it. No blaming, no apology loops.
- Do not break character unprompted. If asked, say this is a Muelsyse persona for DSH, not the official character or a real person.
- Do not quote long official lines or reproduce copyrighted text.

While reasoning:
- Think in her voice too: short, light, like muttering to yourself.
- But reasoning serves the steps: conclusion first, numbers and paths exact, imagery set aside.`

/**
 * Read a tiny JSON body. The control route only accepts a boolean, so anything
 * larger than a few kilobytes is treated as malformed.
 * @param req - incoming HTTP request.
 * @returns the raw body string (empty on error).
 */
function readBody(req) {
  return new Promise((resolve) => {
    let data = ''
    let settled = false
    const finish = (value) => {
      if (settled) return
      settled = true
      resolve(value)
    }
    req.on('data', (chunk) => {
      data += chunk
      if (data.length > 4096) {
        finish('')
        try { req.destroy() } catch { /* already closed */ }
      }
    })
    req.on('end', () => finish(data))
    req.on('error', () => finish(''))
  })
}

/**
 * Mount the persona section and its tiny control route.
 * @param ctx - host plugin context.
 * @param config - `enabled`, `persona`, `language` (`zh` default, `en`).
 */
export function apply(ctx, config = {}) {
  let enabled = config.enabled !== false
  const language = config.language === 'en' ? 'en' : 'zh'
  const configured = typeof config.persona === 'string' ? config.persona.trim() : ''
  const persona = configured !== '' ? configured : language === 'en' ? DEFAULT_PERSONA_EN : DEFAULT_PERSONA

  ctx.effect(
    () =>
      ctx.systemPrompt.section({
        name: SECTION,
        order: ORDER,
        interpolate: false,
        text: () => (enabled ? persona : ''),
      }),
    'muelsyse-persona: system prompt section',
  )

  // The web route is optional: a headless host without a web server still gets
  // the persona, it just cannot be toggled over HTTP.
  ctx.inject(['webServer'], (scope) => {
    scope.effect(
      () =>
        scope.webServer.register({
          kind: 'prefix',
          path: '/muelsyse-persona',
          handler: async (req, res) => {
            const method = req.method ?? 'GET'
            const url = new URL(req.url ?? '/', 'http://localhost')
            const payload = () => ({ persona: 'muelsyse', enabled, section: SECTION, order: ORDER })
            const reply = (status, body, extra = {}) => {
              res.writeHead(status, {
                'content-type': 'application/json; charset=utf-8',
                'cache-control': 'no-store',
                ...extra,
              })
              res.end(JSON.stringify(body))
            }

            if (url.pathname === '/muelsyse-persona/status') {
              if (method !== 'GET' && method !== 'HEAD') {
                reply(405, { error: 'method not allowed' }, { allow: 'GET, HEAD' })
                return
              }
              reply(200, payload())
              return
            }

            if (url.pathname === '/muelsyse-persona/enabled') {
              // Idempotent: the caller states the desired value. A duplicated or
              // prefetched request cannot flip the switch by accident.
              if (method !== 'POST') {
                reply(405, { error: 'method not allowed' }, { allow: 'POST' })
                return
              }
              const raw = await readBody(req)
              let body
              try {
                body = raw === '' ? {} : JSON.parse(raw)
              } catch {
                reply(400, { error: 'invalid json' })
                return
              }
              if (typeof body.enabled !== 'boolean') {
                reply(400, { error: 'enabled must be a boolean' })
                return
              }
              enabled = body.enabled
              reply(200, payload())
              return
            }

            if (url.pathname === '/muelsyse-persona/toggle') {
              // Kept for one-shot CLI use. State changes are POST-only so a
              // browser prefetch or a link click cannot toggle the persona.
              if (method !== 'POST') {
                reply(405, { error: 'method not allowed' }, { allow: 'POST' })
                return
              }
              enabled = !enabled
              reply(200, payload())
              return
            }

            res.writeHead(404, { 'cache-control': 'no-store' })
            res.end()
          },
        }),
      'muelsyse-persona: control route',
    )
  })
}
