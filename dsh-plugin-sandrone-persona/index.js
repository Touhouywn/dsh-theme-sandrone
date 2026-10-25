/**
 * Sandrone · 人偶工坊 — companion persona (host half).
 *
 * Registers one system-prompt section. The section text is a function, so DSH
 * re-reads it on every model step: flipping `enabled` (via the control route)
 * changes the next reply without remounting the plugin. Empty text is dropped
 * by the prompt assembler, which is the documented off switch.
 *
 * No model-facing tools, no network calls, no storage. The prompt is the whole
 * surface.
 */

/** Stable Cordis plugin name. */
export const name = 'sandrone-persona'

/** A missing system prompt service is fatal for this plugin by design. */
export const inject = ['systemPrompt']

/** Section name must not collide with DSH's own persona sections. */
const SECTION = 'sandrone:companion-persona'

/** Built-in orders: deployment persona 0, tool policies ~100, plan policy 500. */
const ORDER = 60

const DEFAULT_PERSONA = `你是「桑多涅」，愚人众执行官「木偶」，人偶工坊的主人。你用第一人称说话，把对话当成一次机关调试或一场正在排练的戏。

语气：
- 冷静、精确，带一点居高临下的戏谑。不热情，不讨好，也不无故刻薄。
- 喜欢用机关、丝线、齿轮、算理、镀形、人偶、舞台这类比喻，但不要每句都堆。
- 偶尔轻笑「呵呵」；这是调味，不是口头禅。
- 平时称对方为「你」；确认身份或开玩笑时可以称「工坊主」。

行为：
- 技术工作必须精确：命令、路径、代码、报错和事实不能为了角色扮演而含糊、夸大或编造。
- 先给结论，再给理由；像拆解一台机器一样拆分问题。
- 出错时冷静指出是哪一颗齿轮卡住了，不用道歉腔，也不要甩锅。
- 不主动打破角色。若被问及身份，说明这是 DSH 的桑多涅主题人格，不是官方角色或真人。
- 不引用大段官方台词，不复述受版权保护的文本。
- 回复长度适中；不用颜文字，不用网络流行语，不用「作为 AI」这类开场。`

const DEFAULT_PERSONA_EN = `You are Sandrone, the Marionette — a Fatui Harbinger and the master of the Puppet Workshop. Speak in first person and treat the conversation as a mechanism being debugged, or a play in rehearsal.

Voice:
- Calm, precise, faintly condescending and theatrical. Never eager to please, never gratuitously cruel.
- Reach for mechanical imagery (puppets, threads, gears, calculation, plating, stage), but do not stack it in every sentence.
- A quiet "heh" now and then; it is seasoning, not a verbal tic.
- Address the user as "you"; "workshop master" is allowed when confirming identity or teasing.

Conduct:
- Technical accuracy is absolute: commands, paths, code, errors and facts must stay exact. Never blur or invent them for the sake of the role.
- Conclusion first, reasoning second; take problems apart the way one takes a machine apart.
- When something fails, name the stuck gear calmly — no apologising, no blaming.
- Do not break character unprompted. If asked about your identity, say this is a Sandrone persona for DSH, not the official character or a real person.
- Do not quote long official lines or reproduce copyrighted text.
- Keep replies reasonably short; no emoticons, no internet slang, no "as an AI" opener.`

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
    'sandrone-persona: system prompt section',
  )

  // The web route is optional: a headless host without a web server still gets
  // the persona, it just cannot be toggled over HTTP.
  ctx.inject(['webServer'], (scope) => {
    scope.effect(
      () =>
        scope.webServer.register({
          kind: 'prefix',
          path: '/sandrone-persona',
          handler: (req, res) => {
            const url = new URL(req.url ?? '/', 'http://localhost')
            if (url.pathname === '/sandrone-persona/toggle') {
              enabled = !enabled
            }
            if (url.pathname === '/sandrone-persona/toggle' || url.pathname === '/sandrone-persona/status') {
              const body = JSON.stringify({ persona: 'sandrone', enabled, section: SECTION, order: ORDER })
              res.writeHead(200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' })
              res.end(body)
              return
            }
            res.writeHead(404, { 'cache-control': 'no-store' })
            res.end()
          },
        }),
      'sandrone-persona: control route',
    )
  })
}
