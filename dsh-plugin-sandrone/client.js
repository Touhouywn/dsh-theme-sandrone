/**
 * Sandrone Workshop — the left-sidebar page for the Sandrone theme.
 *
 * The page fetches the theme's own `/theme-sandrone/status` route, shows what
 * the theme actually sees, can replay the opening, and can toggle the companion
 * persona through its own route. It never writes the profile, never alters
 * another plugin, and never touches the DOM outside its own React subtree.
 */
window.__ModuleLoader__.load({
  id: 'dsh-plugin-sandrone',
  factory: (require) => {
    const React = require('react')
    const h = React.createElement

    const NS = 'sandroneHub'
    const PANEL_ID = 'sandrone'
    const STATUS_URL = '/theme-sandrone/status'
    const PERSONA_URL = '/sandrone-persona/status'
    const PERSONA_SET_URL = '/sandrone-persona/enabled'

    const zh = {
      panel: '桑多涅工坊',
      title: '桑多涅 · 人偶工坊',
      subtitle: 'DSH 主题控制台：运行状态、配色与开屏。',
      'status.title': '运行状态',
      'row.route': '主题路由',
      'row.css': '样式表命中',
      'row.reports': '页面自检',
      'row.dark': '深色属性',
      'row.applied': '样式已应用',
      'row.opening': '开屏遮罩',
      'row.persona': '对话语气',
      'persona.on': '桑多涅',
      'persona.off': '关闭',
      'persona.missing': '未安装',
      'on': '已启用',
      'off': '未启用',
      'state.online': '主题在线',
      'state.offline': '主题未响应',
      'state.loading': '读取中…',
      'palette.title': '主题配色',
      'color.canvas': '画布',
      'color.gold': '金铜',
      'color.ivory': '象牙',
      'color.ice': '冰蓝',
      'color.crimson': '绯红',
      'action.title': '操作',
      'action.refresh': '刷新状态',
      'action.replay': '重播开屏',
      'action.persona': '切换语气',
      'action.copy': '复制诊断',
      'action.copied': '已复制',
      'action.hint': '重播会重新加载当前页面，并强制播放一次开屏；切换语气只影响下一条回复。',
      'action.personaHint': '语气插件未响应；确认 dsh-plugin-sandrone-persona 已安装。',
      'note.title': '说明',
      'note.body': '这个入口只读取 /theme-sandrone/status、切换语气插件的开关注册，并可重播开屏；不会修改 DSH 核心、配置文件或其他插件。主题本身仍由 dsh-theme-sandrone 提供。',
      error: '读取状态失败',
    }

    const en = {
      panel: 'Sandrone Workshop',
      title: 'Sandrone · Marionette Workshop',
      subtitle: 'A console for the DSH theme: status, palette, and the opening.',
      'status.title': 'Runtime status',
      'row.route': 'Theme route',
      'row.css': 'Stylesheet hits',
      'row.reports': 'Page checks',
      'row.dark': 'Dark attribute',
      'row.applied': 'Styles applied',
      'row.opening': 'Opening overlay',
      'row.persona': 'Conversation voice',
      'persona.on': 'Sandrone',
      'persona.off': 'off',
      'persona.missing': 'not installed',
      'on': 'on',
      'off': 'off',
      'state.online': 'Theme online',
      'state.offline': 'Theme not responding',
      'state.loading': 'Reading…',
      'palette.title': 'Palette',
      'color.canvas': 'Canvas',
      'color.gold': 'Gold',
      'color.ivory': 'Ivory',
      'color.ice': 'Ice',
      'color.crimson': 'Crimson',
      'action.title': 'Actions',
      'action.refresh': 'Refresh status',
      'action.replay': 'Replay opening',
      'action.persona': 'Toggle voice',
      'action.copy': 'Copy diagnostics',
      'action.copied': 'Copied',
      'action.hint': 'Replay reloads the page and forces the opening once; toggling the voice affects the next reply.',
      'action.personaHint': 'Persona plugin not responding; make sure dsh-plugin-sandrone-persona is installed.',
      'note.title': 'Notes',
      'note.body': 'This page reads /theme-sandrone/status, toggles the persona plugin live registration, and can replay the opening. It does not change DSH core, the profile, or any other plugin. The theme itself is still provided by dsh-theme-sandrone.',
      error: 'Failed to read status',
    }

    const page = {
      padding: '32px 36px 48px',
      maxWidth: '980px',
      margin: '0 auto',
      boxSizing: 'border-box',
      color: 'var(--dsw-alias-label-primary)',
      fontFamily: 'var(--dsw-font-family, system-ui, -apple-system, "Segoe UI", sans-serif)',
    }
    const header = { display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '22px' }
    const emblem = {
      width: '58px',
      height: '58px',
      borderRadius: '50%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(circle at 35% 30%, #e0c795, #4a3820 72%)',
      color: '#f7eeda',
      border: '1px solid rgba(199,168,110,.55)',
      boxShadow: '0 0 22px rgba(199,168,110,.18)',
      flex: 'none',
    }
    const title = { margin: 0, fontSize: '22px', fontWeight: 600, letterSpacing: '.02em' }
    const subtitle = {
      margin: '6px 0 0',
      color: 'var(--dsw-alias-label-tertiary)',
      fontSize: '13px',
      lineHeight: 1.6,
    }
    const grid = {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
      gap: '16px',
      marginBottom: '16px',
    }
    const card = {
      background: 'var(--dsw-alias-bg-layer-1)',
      border: '1px solid var(--dsw-alias-border-l2)',
      borderRadius: '14px',
      padding: '18px 20px',
      boxShadow: 'var(--dsw-shadow-lv1, none)',
    }
    const cardTitle = {
      margin: '0 0 12px',
      fontSize: '12px',
      fontWeight: 600,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      color: 'var(--dsw-alias-label-tertiary)',
    }
    const row = {
      display: 'flex',
      alignItems: 'baseline',
      justifyContent: 'space-between',
      gap: '16px',
      padding: '7px 0',
      borderBottom: '1px solid var(--dsw-alias-border-l1)',
      fontSize: '13px',
    }
    const rowLast = { ...row, borderBottom: 'none' }
    const rowLabel = { color: 'var(--dsw-alias-label-secondary)' }
    const rowValue = {
      color: 'var(--dsw-alias-label-primary)',
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
      fontSize: '12.5px',
      textAlign: 'right',
      overflowWrap: 'anywhere',
    }
    const chip = {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '7px',
      padding: '3px 9px',
      borderRadius: '999px',
      border: '1px solid var(--dsw-alias-border-l2)',
      background: 'var(--dsw-alias-bg-layer-2)',
      fontSize: '11.5px',
      color: 'var(--dsw-alias-label-secondary)',
    }
    const dot = {
      width: '7px',
      height: '7px',
      borderRadius: '50%',
      background: 'var(--dsw-alias-state-success-primary)',
    }
    const swatchGrid = { display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: '10px' }
    const swatch = {
      borderRadius: '10px',
      overflow: 'hidden',
      border: '1px solid var(--dsw-alias-border-l2)',
      background: 'var(--dsw-alias-bg-layer-2)',
    }
    const swatchColor = { height: '46px' }
    const swatchName = {
      padding: '7px 8px',
      fontSize: '11px',
      color: 'var(--dsw-alias-label-tertiary)',
      textAlign: 'center',
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
    }
    const actions = { display: 'flex', flexWrap: 'wrap', gap: '10px', alignItems: 'center' }
    const button = {
      appearance: 'none',
      border: '1px solid var(--dsw-alias-border-l2)',
      background: 'var(--dsw-alias-bg-layer-2)',
      color: 'var(--dsw-alias-label-primary)',
      borderRadius: '8px',
      padding: '8px 14px',
      fontSize: '12.5px',
      fontFamily: 'inherit',
      cursor: 'pointer',
    }
    const buttonDisabled = { ...button, opacity: 0.55, cursor: 'default' }
    const hint = {
      margin: '12px 0 0',
      fontSize: '12px',
      lineHeight: 1.7,
      color: 'var(--dsw-alias-label-tertiary)',
    }
    const note = {
      margin: 0,
      fontSize: '12.5px',
      lineHeight: 1.8,
      color: 'var(--dsw-alias-label-secondary)',
    }
    const errorText = {
      margin: '10px 0 0',
      fontSize: '12px',
      lineHeight: 1.6,
      color: 'var(--dsw-alias-state-error-primary)',
    }

    /** A small original gear mark, drawn in currentColor. */
    function Gear(props) {
      const size = props && props.size ? props.size : 18
      return h(
        'svg',
        {
          viewBox: '0 0 24 24',
          width: size,
          height: size,
          fill: 'none',
          stroke: 'currentColor',
          strokeWidth: 1.7,
          strokeLinecap: 'round',
          strokeLinejoin: 'round',
          'aria-hidden': true,
          style: { display: 'block' },
        },
        h('circle', { cx: 12, cy: 12, r: 3.1 }),
        h('path', {
          d: 'M12 2.4v2.6M12 19v2.6M2.4 12h2.6M19 12h2.6M5.2 5.2l1.8 1.8M17 17l1.8 1.8M18.8 5.2L17 7M7 17l-1.8 1.8',
        }),
      )
    }

    /** Read the theme's live self-check route. */
    function useStatus() {
      const [state, setState] = React.useState({ loading: true, data: null, error: null })
      const reload = React.useCallback(function () {
        setState(function (previous) {
          return { loading: true, data: previous.data, error: null }
        })
        fetch(STATUS_URL, { cache: 'no-store' })
          .then(function (response) {
            if (!response.ok) throw new Error('HTTP ' + response.status)
            return response.json()
          })
          .then(function (data) {
            setState({ loading: false, data: data, error: null })
          })
          .catch(function (error) {
            setState({
              loading: false,
              data: null,
              error: String(error && error.message ? error.message : error),
            })
          })
      }, [])
      React.useEffect(
        function () {
          reload()
        },
        [reload],
      )
      return { state: state, reload: reload }
    }

    /** Read and toggle the companion persona's live registration. */
    function usePersona() {
      const [state, setState] = React.useState({ loading: true, enabled: false, available: false, error: null })
      const apply = function (data) {
        setState({ loading: false, enabled: data && data.enabled === true, available: true, error: null })
      }
      const fail = function (error) {
        setState({
          loading: false,
          enabled: false,
          available: false,
          error: String(error && error.message ? error.message : error),
        })
      }
      const load = React.useCallback(function () {
        setState(function (previous) {
          return { ...previous, loading: true }
        })
        fetch(PERSONA_URL, { cache: 'no-store' })
          .then(function (response) {
            if (!response.ok) throw new Error('HTTP ' + response.status)
            return response.json()
          })
          .then(apply)
          .catch(fail)
      }, [])
      const setEnabled = React.useCallback(function (next) {
        setState(function (previous) {
          return { ...previous, loading: true }
        })
        fetch(PERSONA_SET_URL, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ enabled: next === true }),
          cache: 'no-store',
        })
          .then(function (response) {
            if (!response.ok) throw new Error('HTTP ' + response.status)
            return response.json()
          })
          .then(apply)
          .catch(fail)
      }, [])
      React.useEffect(
        function () {
          load()
        },
        [load],
      )
      return { state: state, load: load, setEnabled: setEnabled }
    }

    /**
     * The page body. `t` arrives through the slot's `inject` contract; the
     * dictionary fallback keeps the page readable if a host build changes it.
     */
    function SandronePage(props) {
      const t =
        props && typeof props.t === 'function'
          ? props.t
          : function (key) {
              return zh[key] || key
            }
      const status = useStatus()
      const persona = usePersona()
      const data = status.state.data
      const report = data && data.lastReport ? data.lastReport : {}
      const online = Boolean(data) && !status.state.error
      const stateLabel = status.state.error
        ? t('state.offline')
        : status.state.loading
          ? t('state.loading')
          : t('state.online')
      const personaLabel = persona.state.loading
        ? t('state.loading')
        : !persona.state.available
          ? t('persona.missing')
          : persona.state.enabled
            ? t('persona.on')
            : t('persona.off')
      const rows = [
        [t('row.route'), data && data.theme ? data.theme : '—'],
        [t('row.css'), data ? String((data.hits && data.hits['theme.css']) || 0) : '—'],
        [t('row.reports'), data ? String(data.reportCount || 0) : '—'],
        [t('row.dark'), String(report.dark) === 'true' ? t('on') : t('off')],
        [t('row.applied'), report.applied || '—'],
        [t('row.opening'), String(report.opening) === 'true' ? t('on') : '—'],
        [t('row.persona'), personaLabel],
      ]
      const palette = [
        { name: t('color.canvas'), value: '#080b11' },
        { name: t('color.gold'), value: '#c7a86e' },
        { name: t('color.ivory'), value: '#ebe3d1' },
        { name: t('color.ice'), value: '#a9cbd5' },
        { name: t('color.crimson'), value: '#993e50' },
      ]
      const [copied, setCopied] = React.useState(false)

      function replay() {
        try {
          window.location.hash = 'opening'
          window.location.reload()
        } catch (error) {
          /* The page still works without the opening. */
        }
      }

      function copy() {
        const payload = data || { error: status.state.error }
        const text = JSON.stringify(payload, null, 2)
        try {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard
              .writeText(text)
              .then(function () {
                setCopied(true)
                setTimeout(function () {
                  setCopied(false)
                }, 1500)
              })
              .catch(function () {})
          }
        } catch (error) {
          /* Clipboard is optional. */
        }
      }

      return h(
        'div',
        { style: page },
        h(
          'header',
          { style: header },
          h('div', { style: emblem }, h(Gear, { size: 30 })),
          h(
            'div',
            null,
            h('h1', { style: title }, t('title')),
            h('p', { style: subtitle }, t('subtitle')),
          ),
        ),
        h(
          'div',
          { style: grid },
          h(
            'section',
            { style: card },
            h('h2', { style: cardTitle }, t('status.title')),
            rows.map(function (pair, index) {
              return h(
                'div',
                { key: pair[0], style: index === rows.length - 1 ? rowLast : row },
                h('span', { style: rowLabel }, pair[0]),
                h('span', { style: rowValue }, pair[1]),
              )
            }),
            h(
              'div',
              { style: { marginTop: '12px' } },
              h(
                'span',
                { style: chip },
                h('span', {
                  style: {
                    ...dot,
                    background: online
                      ? 'var(--dsw-alias-state-success-primary)'
                      : 'var(--dsw-alias-state-warn-primary)',
                  },
                }),
                stateLabel,
              ),
            ),
            status.state.error &&
              h('p', { style: errorText }, t('error') + ': ' + status.state.error),
          ),
          h(
            'section',
            { style: card },
            h('h2', { style: cardTitle }, t('palette.title')),
            h(
              'div',
              { style: swatchGrid },
              palette.map(function (color) {
                return h(
                  'div',
                  { key: color.name, style: swatch },
                  h('div', { style: { ...swatchColor, background: color.value } }),
                  h('div', { style: swatchName }, color.name),
                )
              }),
            ),
          ),
        ),
        h(
          'section',
          { style: { ...card, marginBottom: '16px' } },
          h('h2', { style: cardTitle }, t('action.title')),
          h(
            'div',
            { style: actions },
            h(
              'button',
              {
                type: 'button',
                style: status.state.loading ? buttonDisabled : button,
                onClick: status.reload,
                disabled: status.state.loading,
              },
              t('action.refresh'),
            ),
            h('button', { type: 'button', style: button, onClick: replay }, t('action.replay')),
            h(
              'button',
              {
                type: 'button',
                style: !persona.state.available || persona.state.loading ? buttonDisabled : button,
                onClick: function () {
                  persona.setEnabled(!persona.state.enabled)
                },
                disabled: !persona.state.available || persona.state.loading,
              },
              t('action.persona'),
            ),
            h('button', { type: 'button', style: button, onClick: copy }, t('action.copy')),
            copied && h('span', { style: hint }, t('action.copied')),
          ),
          h('p', { style: hint }, t('action.hint')),
          !persona.state.available && !persona.state.loading && h('p', { style: hint }, t('action.personaHint')),
        ),
        h(
          'section',
          { style: card },
          h('h2', { style: cardTitle }, t('note.title')),
          h('p', { style: note }, t('note.body')),
        ),
      )
    }

    /** Register the sidebar row and its page through the host's own slots. */
    function apply(ctx) {
      ctx.effect(
        () =>
          ctx.locale.register(NS, {
            zh: zh,
            en: en,
          }),
        'sandrone-hub: dictionaries',
      )
      const t = ctx.locale.bind(NS)

      // Report the live panel list to the Host so the row's registration can be
      // checked from outside the window (`/sandrone-hub/status`).
      const report = function () {
        let panels = []
        try {
          panels = ctx.slots
            .entriesOfSlot('sidebar.panellist')
            .map(function (entry) {
              return entry && entry.options ? entry.options.id : undefined
            })
            .filter(Boolean)
        } catch (error) {
          panels = []
        }
        const params = new URLSearchParams({ panel: PANEL_ID, panels: panels.join(',') })
        fetch('/sandrone-hub/ping?' + params.toString(), { cache: 'no-store' }).catch(function () {})
      }

      ctx.slots.inject('sidebar.panellist', function () {
        return ctx.slots.register(
          {
            name: 'sidebar.panellist',
            id: PANEL_ID,
            order: 15,
            label: function () {
              return t('panel')
            },
            locale: NS,
          },
          Gear,
        )
      })

      ctx.slots.inject('main', function* () {
        yield ctx.slots.register(
          {
            name: 'main',
            key: PANEL_ID,
            locale: NS,
            inject: function () {
              return { t: t }
            },
          },
          SandronePage,
        )
      })

      // A one-request beacon lets the Host prove the Client half mounted even
      // when no one is looking at the window's console.
      report()
      ctx.effect(
        function () {
          return ctx.slots.subscribe('sidebar.panellist', report)
        },
        'sandrone-hub: sidebar report',
      )
    }

    return {
      inject: ['slots', 'locale'],
      apply: apply,
    }
  },
})
