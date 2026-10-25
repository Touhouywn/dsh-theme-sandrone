/**
 * Sandrone · 人偶工坊 — DeepSeek Harness theme plugin (browser half).
 *
 * Hand-written bundle in the client-modules format: executing this file only
 * *registers* a factory; the body runs when the kernel materializes the module
 * and mounts it as a Cordis plugin in the page.
 *
 * It exists because the desktop shell serves the page from `dsh-app://app/`
 * and applies the Host's index-injection rows from a snapshot taken at
 * startup. A client half is delivered through the live module graph instead,
 * so it works in both carriers (Electron shell and plain browser) and can be
 * enabled/disabled at runtime like any other client plugin.
 *
 * The heavy lifting stays in `theme/theme.css`, served by the host half, so
 * restyling never requires touching this bundle.
 */
window.__ModuleLoader__.load({
  id: 'dsh-theme-sandrone',
  factory: (require) => {
    var module = { exports: {} }
    var exports = module.exports

    /** Same asset URL the host half serves and the index row points at. */
    var CSS_URL = '/theme-sandrone/theme.css'
    var DARK_ATTRIBUTE = 'data-ds-dark-theme'
    var LINK_MARKER = 'themeSandrone'

    /**
     * Attach the theme stylesheet.
     *
     * The link is always version-stamped: the desktop shell proxies host
     * responses through its custom protocol and drops the cache headers, so a
     * plain URL would be served from the browser cache forever and CSS edits
     * would never reach the window. Any earlier link (for example the one the
     * index-injection row added) is removed first, so only the current sheet
     * styles the page.
     */
    function ensureStylesheet() {
      var stale = document.querySelectorAll('link[href*="' + CSS_URL + '"]')
      for (var index = 0; index < stale.length; index += 1) stale[index].remove()
      var link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = CSS_URL + '?v=' + String(Date.now())
      link.setAttribute('data-' + LINK_MARKER.replace(/[A-Z]/g, function (letter) {
        return '-' + letter.toLowerCase()
      }), '')
      document.head.appendChild(link)
      return function () {
        link.remove()
      }
    }

    /** Hold the dark palette attribute the theme's CSS is scoped to. */
    function holdDarkPalette() {
      var body = document.body
      if (body === null) return function () {}
      var hold = function () {
        if (!body.hasAttribute(DARK_ATTRIBUTE)) body.setAttribute(DARK_ATTRIBUTE, '')
      }
      hold()
      var observer = new MutationObserver(hold)
      observer.observe(body, { attributes: true, attributeFilter: [DARK_ATTRIBUTE] })
      var previousScheme = document.documentElement.style.colorScheme
      document.documentElement.style.colorScheme = 'dark'
      return function () {
        observer.disconnect()
        document.documentElement.style.colorScheme = previousScheme
      }
    }

    /**
     * Mount the theme on the page.
     * @param ctx - the page's Cordis context; `effect` owns the teardown.
     */
    /** Report what the theme sees in the document, for `/theme-sandrone/status`. */
    function reportFacts() {
      try {
        var frame = document.querySelector('#root > div:first-child')
        var text = function (value) { return String(value) }
        // Compact outline of the painted box tree: tag, first class token and
        // the computed background of every element down the first two levels,
        // so an opaque cover can be identified from outside the window.
        var outline = []
        var describe = function (el, depth) {
          if (el === null || depth > 3) return
          var style = getComputedStyle(el)
          var bg = style.backgroundColor
          if (bg === 'rgba(0, 0, 0, 0)' && style.backgroundImage === 'none') return
          var cls = String(el.className || '').split(' ')[0].slice(0, 24)
          outline.push(depth + el.tagName.toLowerCase() + (cls === '' ? '' : '.' + cls) + '=' + bg.replace(/[()\s]/g, ''))
        }
        var walk = function (el, depth) {
          describe(el, depth)
          if (depth >= 3 || el === null) return
          for (var index = 0; index < el.children.length && index < 3; index += 1) walk(el.children[index], depth + 1)
        }
        walk(document.getElementById('root'), 0)

        var facts = new URLSearchParams({
          v: '4',
          from: 'client',
          dark: text(document.body.hasAttribute(DARK_ATTRIBUTE)),
          pref: text(document.documentElement.dataset.dsThemeSource || '-'),
          win: text(document.documentElement.hasAttribute('data-windows-titlebar')),
          kids: text((document.getElementById('root') || { childElementCount: -1 }).childElementCount),
          frame: text(frame !== null),
          fcls: text(frame === null ? '-' : String(frame.className).slice(0, 40)),
          center: text(document.querySelector('[class*="centerCol"]') !== null),
          sidebar: text(document.querySelector('[class*="sidebarCol"]') !== null),
          applied: text(getComputedStyle(document.body).getPropertyValue('--sandrone-theme').trim() || '-'),
          base: text(getComputedStyle(document.body).getPropertyValue('--dsw-alias-bg-base').trim()),
          link: text(document.querySelector('link[href*="theme.css"]') !== null),
          opening: text(document.getElementById('sandrone-opening') !== null),
          opw: text((function () {
            var node = document.getElementById('sandrone-opening')
            return node === null ? -1 : Math.round(node.getBoundingClientRect().width)
          })()),
          opz: text((function () {
            var node = document.getElementById('sandrone-opening')
            return node === null ? '-' : getComputedStyle(node).zIndex
          })()),
          opa: text((function () {
            var node = document.getElementById('sandrone-opening')
            return node === null ? '-' : getComputedStyle(node).opacity
          })()),
          zoom: text(getComputedStyle(document.body).zoom || '-'),
          hzoom: text(getComputedStyle(document.documentElement).zoom || '-'),
          inner: text(window.innerWidth + 'x' + window.innerHeight),
          srect: text((function () {
            var node = document.querySelector('#sandrone-opening .so-stage')
            if (node === null) return '-'
            var r = node.getBoundingClientRect()
            return Math.round(r.left) + ',' + Math.round(r.top) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height)
          })()),
          rect: text((function () {
            var node = document.getElementById('sandrone-opening')
            if (node === null) return '-'
            var r = node.getBoundingClientRect()
            return Math.round(r.left) + ',' + Math.round(r.top) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height)
          })()),
          brand: text(document.querySelector('img[data-sandrone-brand]') !== null),
          brandStatus: text(brandStatus),
          icons: text(iconsPainted),
          toggle: text(toggleOutcome),
          sideDom: text((function () {
            var side = document.querySelector('[class*="sidebarCol"]')
            if (side === null) return '-'
            var out = []
            var walk = function (el, depth) {
              if (el === null || depth > 7) return
              var cls = String(el.className || '').split(' ')
              var short = []
              for (var i = 0; i < cls.length; i += 1) {
                if (cls[i] === '') continue
                var parts = cls[i].split('_')
                short.push(parts[parts.length - 1])
              }
              var tag = el.tagName.toLowerCase()
              if (short.length > 0 || tag === 'svg' || tag === 'img') out.push(tag + '.' + short.join('.'))
              for (var c = 0; c < el.children.length && c < 8; c += 1) walk(el.children[c], depth + 1)
            }
            walk(side, 0)
            return out.join(' ').slice(0, 1500)
          })()),
          counts: text((function () {
            var side = document.querySelector('[class*="sidebarCol"]')
            if (side === null) return '-'
            var names = ['brandMark', 'railMark', 'panelIcon', 'panelGlyph', 'projectRow', 'folder', 'regionArea', 'groupSection', 'logoRow']
            var parts = []
            for (var i = 0; i < names.length; i += 1) {
              parts.push(names[i] + '=' + side.querySelectorAll('[class*="' + names[i] + '"]').length)
            }
            return parts.join(',')
          })()),
          headDom: text((function () {
            // Every button in the window with its place on screen: the sidebar
            // toggle is one of them, and guessing its class name has failed
            // twice, so it is identified by what it is and where it sits.
            var buttons = document.querySelectorAll('button, [role="button"]')
            var out = []
            for (var i = 0; i < buttons.length && out.length < 14; i += 1) {
              var el = buttons[i]
              var rect = el.getBoundingClientRect()
              if (rect.width < 8 || rect.height < 8) continue
              var cls = String(el.className || '').split(' ')
              var short = []
              for (var k = 0; k < cls.length; k += 1) {
                if (cls[k] === '') continue
                var parts = cls[k].split('_')
                short.push(parts[parts.length - 1])
              }
              var label = el.getAttribute('aria-label') || el.getAttribute('title') || ''
              out.push(
                '@' + Math.round(rect.left) + ',' + Math.round(rect.top) +
                ' ' + Math.round(rect.width) + 'x' + Math.round(rect.height) +
                ' [' + short.slice(0, 3).join('.') + ']' +
                (label !== '' ? ' "' + label.slice(0, 18) + '"' : ''),
              )
            }
            var side = document.querySelector('[class*="sidebarCol"]')
            var sideRect = side === null ? null : side.getBoundingClientRect()
            out.push('side=' + (sideRect === null ? 'none' : Math.round(sideRect.width) + 'x' + Math.round(sideRect.height)))
            var bar = document.querySelector('[data-windows-titlebar]')
            out.push('titlebar=' + (bar === null ? 'none' : Math.round(bar.getBoundingClientRect().height)))
            return out.join(' | ')
          })()),
          dom: outline.join(' ').slice(0, 900),
        })
        fetch('/theme-sandrone/report?' + facts.toString(), { cache: 'no-store' }).catch(function () {})
      } catch (error) {
        // A failed self-check must never break the page.
      }
    }

    /* ------------------------------------------------------------------
       Icon set
       The sidebar ships a whale wordmark plus one outline glyph per row. The
       skin replaces them with the workshop's own marks, each row getting a
       different one, and the tab icon with the round portrait. Rows are matched
       by their visible label, and the brand by geometry (an SVG in the header),
       because the CSS-module class names are build-specific.
       ------------------------------------------------------------------ */
    var ICON_URL = '/theme-sandrone/icon.png'
    var ORNAMENTS = {
      gear: '/theme-sandrone/gear.png',
      iris: '/theme-sandrone/iris.png',
      strings: '/theme-sandrone/strings.png',
      burst: '/theme-sandrone/burst.png',
      cryo: '/theme-sandrone/cryo.png',
      skill: '/theme-sandrone/skill.png',
    }

    /**
     * Pick the ornament for one sidebar row.
     * @param label - the row's visible text.
     * @param seen - how many rows have already been themed, for the fallback cycle.
     * @returns the ornament's URL.
     */
    function ornamentFor(label, seen) {
      if (label.indexOf('新会话') !== -1 || label.indexOf('New') !== -1) return ORNAMENTS.burst
      if (label.indexOf('插件') !== -1 || label.indexOf('Plugin') !== -1) return ORNAMENTS.gear
      if (label.indexOf('自动化') !== -1 || label.indexOf('Automation') !== -1) return ORNAMENTS.iris
      if (label.indexOf('更多') !== -1 || label.indexOf('More') !== -1) return ORNAMENTS.strings
      if (label.indexOf('工作区') !== -1 || label.indexOf('Workspace') !== -1) return ORNAMENTS.cryo
      if (label.indexOf('设置') !== -1 || label.indexOf('Settings') !== -1) return ORNAMENTS.skill
      var cycle = [ORNAMENTS.skill, ORNAMENTS.gear, ORNAMENTS.cryo, ORNAMENTS.strings, ORNAMENTS.burst, ORNAMENTS.iris]
      return cycle[seen % cycle.length]
    }

    /**
     * Read the visible label of the row owning a glyph.
     * @param glyph - the SVG being replaced.
     * @returns trimmed label text, possibly empty.
     */
    function labelOf(glyph) {
      var node = glyph.parentElement
      var depth = 0
      while (node !== null && depth < 4) {
        var text = (node.textContent || '').replace(/\s+/g, ' ').trim()
        if (text.length > 0) return text.slice(0, 24)
        node = node.parentElement
        depth += 1
      }
      return ''
    }

    /** Build the replacement image at the size of the glyph it replaces. */
    function iconImage(src, width, height, glow) {
      var image = document.createElement('img')
      image.src = src
      image.alt = ''
      image.setAttribute('data-sandrone-icon', '')
      image.style.cssText =
        'width:' + width + 'px;height:' + height + 'px;object-fit:contain;display:block;' +
        (glow ? 'border-radius:50%;filter:saturate(1.05) drop-shadow(0 0 6px rgba(199,168,110,.35))' : 'opacity:.92')
      return image
    }

    /** Labels of the fixed navigation rows the skin is allowed to restyle. */
    var NAV_LABELS = ['新会话', '插件', '自动化任务', '更多', '设置', '个人', '工作区', 'New chat', 'Plugins', 'Automation', 'More', 'Settings', 'Personal', 'Workspace']

    /**
     * Whether a row is off limits: the account block at the bottom, and anything
     * that looks like a person or an account surface. Those keep their own
     * avatar and name — restyling them reads as a bug, not a theme.
     * @param glyph - the SVG being considered.
     * @param sidebar - the sidebar column that owns it.
     * @returns true when the glyph must be left alone.
     */
    function isProtectedRow(glyph, sidebar) {
      var box = glyph.getBoundingClientRect()
      var frame = sidebar.getBoundingClientRect()
      // Bottom strip: the account row (avatar + user name).
      if (box.top + box.height > frame.bottom - 150) return true
      var node = glyph
      var depth = 0
      while (node !== null && node !== sidebar && depth < 6) {
        var cls = String(node.className || '').toLowerCase()
        if (cls.indexOf('avatar') !== -1 || cls.indexOf('account') !== -1 || cls.indexOf('profile') !== -1 || cls.indexOf('user') !== -1) return true
        node = node.parentElement
        depth += 1
      }
      return false
    }

    /**
     * Find the box that draws a glyph: the nearest ancestor that is about the
     * same size as the glyph itself, so the art lands exactly where the stock
     * icon was.
     * @param glyph - the SVG being restyled.
     * @returns the wrapper element, or null.
     */
    function glyphWrapper(glyph) {
      var box = glyph.getBoundingClientRect()
      var node = glyph.parentElement
      var depth = 0
      while (node !== null && depth < 3) {
        var parentBox = node.getBoundingClientRect()
        if (
          Math.abs(parentBox.width - box.width) <= 12 &&
          Math.abs(parentBox.height - box.height) <= 12
        ) {
          return node
        }
        node = node.parentElement
        depth += 1
      }
      return glyph.parentElement
    }

    /**
     * Paint the theme's art behind a glyph and hide the glyph itself.
     *
     * The node is never replaced or removed: React owns this subtree, and
     * swapping its children made it throw on the next reconcile — the workspace
     * section unmounted and disappeared. Style-only changes are reconciler-safe.
     * @param glyph - the stock SVG to cover.
     * @param src - art URL.
     * @param glow - circular portrait treatment for the brand mark.
     */
    function paintGlyphArt(glyph, src, glow) {
      var wrapper = glyphWrapper(glyph)
      if (wrapper === null) return
      var box = glyph.getBoundingClientRect()
      wrapper.style.backgroundImage = 'url("' + src + '")'
      wrapper.style.backgroundRepeat = 'no-repeat'
      wrapper.style.backgroundPosition = 'center'
      wrapper.style.backgroundSize = 'contain'
      if (glow) wrapper.style.borderRadius = '50%'
      wrapper.setAttribute('data-sandrone-icon', '1')
      glyph.style.visibility = 'hidden'
      glyph.setAttribute('data-sandrone-done', '1')
      glyph.setAttribute('width', String(Math.round(box.width)))
      glyph.setAttribute('height', String(Math.round(box.height)))
    }

    /** Restyle the glyphs of the fixed navigation rows, once per glyph. */
    function applyIconSet() {
      try {
        var sidebar = document.querySelector('[class*="sidebarCol"]')
        if (sidebar !== null) {
          var glyphs = Array.prototype.slice.call(sidebar.querySelectorAll('svg'))
          var themed = 0
          for (var index = 0; index < glyphs.length; index += 1) {
            var glyph = glyphs[index]
            if (glyph.getAttribute('data-sandrone-done') === '1') continue
            var box = glyph.getBoundingClientRect()
            if (box.width < 10 || box.height < 10) continue
            if (isProtectedRow(glyph, sidebar)) continue
            var isBrand = box.top < 150 && Math.abs(box.width - box.height) <= 8 && box.width >= 18
            var label = isBrand ? '' : labelOf(glyph)
            // Only the fixed navigation rows are restyled. Session rows,
            // workspaces and utility buttons keep their own icons.
            if (!isBrand) {
              var matched = false
              for (var navIndex = 0; navIndex < NAV_LABELS.length; navIndex += 1) {
                if (label.indexOf(NAV_LABELS[navIndex]) !== -1) { matched = true; break }
              }
              if (!matched) continue
            }
            paintGlyphArt(glyph, isBrand ? ICON_URL : ornamentFor(label, themed), isBrand)
            themed += 1
          }
        }

        // The shell ships favicon links too; point them at the theme art.
        var icons = document.querySelectorAll('link[rel="icon"], link[rel="shortcut icon"]')
        for (var iconIndex = 0; iconIndex < icons.length; iconIndex += 1) {
          var link = icons[iconIndex]
          if (link.getAttribute('href') !== ICON_URL) link.setAttribute('href', ICON_URL)
        }
      } catch (error) {
        // A missing glyph must never break the page.
      }
    }

    /**
     * Keep the icon set applied. The sidebar re-renders with React (new
     * sessions, workspace switches, hover popovers), which puts the stock
     * glyphs back, so the swap is re-armed on every mutation rather than run
     * once at mount — that is why a one-shot pass left it "not fully replaced".
     */
    function watchIconSet() {
      applyIconSet()
      var sidebar = document.querySelector('[class*="sidebarCol"]')
      if (sidebar === null) {
        setTimeout(watchIconSet, 400)
        return
      }
      if (typeof window.MutationObserver !== 'function') return
      var pending = false
      var observer = new MutationObserver(function () {
        if (pending) return
        pending = true
        setTimeout(function () {
          pending = false
          applyIconSet()
        }, 120)
      })
      observer.observe(sidebar, { childList: true, subtree: true })
      // The header also re-renders on session-title changes outside the column.
      setTimeout(applyIconSet, 1200)
      setTimeout(applyIconSet, 3000)
    }

    /* ------------------------------------------------------------------
       Opening animation
       The Codex skin opens in its own window: the environment traces itself
       in a video, the character is drawn as a vector outline over it, then a
       handwritten signature and the workshop tagline fade in. DSH has no
       startup hook, so the same sequence runs as a one-shot overlay above the
       (already booted) UI, and leaves on its own.
       ------------------------------------------------------------------ */
    var OPENING_ID = 'sandrone-opening'
    var OPENING_SEEN = 'sandrone-opening-v16'
    /** Result of the brand-slot registration, surfaced by the self-check. */
    var brandStatus = 'idle'
    /** Navigation glyphs painted with theme art so far. */
    var iconsPainted = 0
    /** Result of the last title-bar toggle attempt, surfaced by the self-check. */
    var toggleOutcome = 'idle'
    var SVG_NS = 'http://www.w3.org/2000/svg'

    var svgNode = function (tag, attributes) {
      var node = document.createElementNS(SVG_NS, tag)
      for (var key in attributes) if (Object.prototype.hasOwnProperty.call(attributes, key)) node.setAttribute(key, attributes[key])
      return node
    }

    /**
     * Append traced paths and animate them from "not drawn" to drawn.
     * Every paint property is inline: the opening must not depend on a
     * stylesheet surviving in this document.
     * @param parent - SVG group receiving the paths.
     * @param paths - path data strings.
     * @param delay - milliseconds before the first stroke starts.
     * @param stagger - milliseconds between consecutive strokes.
     * @param duration - milliseconds per stroke.
     * @param paint - stroke colour, width and glow for this group.
     */
    function tracePaths(parent, paths, delay, stagger, duration, paint) {
      for (var index = 0; index < paths.length; index += 1) {
        var path = svgNode('path', { d: paths[index] })
        path.style.fill = 'none'
        path.style.stroke = paint.stroke
        path.style.strokeWidth = paint.width
        path.style.strokeLinecap = 'round'
        path.style.strokeLinejoin = 'round'
        if (paint.glow !== undefined) path.style.filter = paint.glow
        parent.appendChild(path)
        try {
          var length = path.getTotalLength()
          path.style.strokeDasharray = length + ' ' + length
          path.style.strokeDashoffset = String(length)
          path.getBoundingClientRect()
          path.style.transition = 'stroke-dashoffset ' + duration + 'ms cubic-bezier(.22,.61,.36,1) ' + (delay + index * stagger) + 'ms'
          path.style.strokeDashoffset = '0'
        } catch (error) {
          // No geometry API: the stroke simply appears already drawn.
        }
      }
    }

    /** Draw the full opening scene from `opening.json`. */
    function renderOpening(root, data) {
      var reduce = false
      try {
        reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      } catch (error) {
        reduce = false
      }

      var outline = root.querySelector('.so-outline')
      var signature = root.querySelector('.so-signature')
      if (outline !== null && data.outline) {
        // No per-path drop-shadow: 70 animated filters over a full-window SVG was
        // the main source of stutter. Strokes are slightly thicker to keep the
        // visual weight the glow used to provide.
        var groups = [
          { className: 'so-outline', paths: data.outline.paths || [], delay: 300, stagger: reduce ? 0 : 16, duration: reduce ? 1 : 620, paint: { stroke: '#f6ab5a', width: '1.8' } },
          { className: 'so-face', paths: data.outline.facePaths || [], delay: 1500, stagger: reduce ? 0 : 18, duration: reduce ? 1 : 480, paint: { stroke: '#ffe3bb', width: '1.4' } },
          { className: 'so-water', paths: data.outline.waterPaths || [], delay: 1700, stagger: 0, duration: reduce ? 1 : 900, paint: { stroke: '#8ac4ee', width: '1.5' } },
        ]
        for (var index = 0; index < groups.length; index += 1) {
          var group = groups[index]
          var node = svgNode('g', { class: group.className })
          node.style.opacity = group.className === 'so-water' ? '.85' : '1'
          outline.appendChild(node)
          tracePaths(node, group.paths, reduce ? 0 : group.delay, group.stagger, group.duration, group.paint)
        }
      }
      if (signature !== null && data.signature && data.signature.paths) {
        tracePaths(signature, data.signature.paths, reduce ? 0 : 1350, reduce ? 0 : 100, reduce ? 1 : 560, {
          stroke: '#e9dcbd',
          width: '2.6',
        })
      }
    }

    /**
     * Play the opening once per page session, then restore the UI underneath.
     * Skips on click or Escape/Enter/Space; a hard timeout guarantees removal.
     */
    function playOpening() {
      if (document.getElementById(OPENING_ID) !== null) return
      var forced = false
      try {
        forced = window.location.hash.indexOf('opening') !== -1
        if (!forced && OPENING_SEEN !== null) {
          if (window.sessionStorage.getItem(OPENING_SEEN) === '1') return
          window.sessionStorage.setItem(OPENING_SEEN, '1')
        }
      } catch (error) {
        // Storage unavailable: play it once per load.
      }

      // No stylesheet at all: every element is laid out with inline styles
      // below. A <style> tag here proved unreliable — the client kernel recycles
      // tags it considers plugin-owned, which silently left the raw 1920x1080
      // films unstyled and cropped by the window.
      var root = document.createElement('div')
      root.id = OPENING_ID
      root.style.cssText =
        'position:fixed;left:0;top:0;width:100vw;height:100vh;z-index:2147483000;overflow:hidden;transition:opacity .75s ease-out;' +
          'background:radial-gradient(120% 85% at 50% 40%,#0c1219 0%,#05070b 70%),linear-gradient(180deg,rgba(3,5,9,0) 52%,rgba(3,5,9,.78) 100%)'
      root.innerHTML = [
        '<video class="so-color" src="/theme-sandrone/opening.mp4" muted playsinline preload="auto"></video>',
        '<div class="so-stage">',
        '<video class="so-trace" src="/theme-sandrone/trace.mp4" muted playsinline preload="auto"></video>',
        '<svg class="so-outline" viewBox="0 0 1280 720" preserveAspectRatio="xMidYMid slice"></svg>',
        '</div>',
        '<div class="so-sign">',
        '<svg class="so-signature" viewBox="0 0 1080 330" preserveAspectRatio="xMidYMid meet"></svg>',
        '<div class="so-tagline">机巧镀形，万理澄清</div>',
        '<div class="so-subtitle">MARIONETTE WORKSHOP</div>',
        '</div>',
        '<div class="so-skip">点击任意处 / 任意键 继续</div>',
      ].join('')
      // Mount on <html>: the app puts a transform on <body>, which makes that
      // element the containing block for `position: fixed` and would size the
      // overlay against the whole page instead of the window. If <html> turns
      // out to be the transformed one, fall back to <body>.
      document.documentElement.appendChild(root)
      var mounted = root.getBoundingClientRect()
      if (mounted.width < window.innerWidth * 0.9 || mounted.height < window.innerHeight * 0.9) {
        document.body.appendChild(root)
      }

      /** Lay out one opening element inline; the overlay owns no stylesheet. */
      var styleOf = function (selector, css) {
        var node = root.querySelector(selector)
        if (node !== null) node.style.cssText = css
        return node
      }
      var stageNode = styleOf(
        '.so-stage',
        'position:absolute;left:0;top:0;width:100%;height:100%;transition:opacity 1.1s ease-out',
      )
      styleOf(
        '.so-trace',
        // No mask and no blend mode: masking a full-window video and screening it
        // over another full-window video is the single most expensive thing this
        // overlay could do, and it showed up as visible stutter mid-sequence.
        'position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.95',
      )
      styleOf('.so-outline', 'position:absolute;inset:0;width:100%;height:100%')
      var signNode = styleOf(
        '.so-sign',
        'position:absolute;left:50%;bottom:5vh;transform:translateX(-50%);display:grid;justify-items:center;gap:6px;opacity:0;visibility:hidden;transition:opacity .9s ease-out',
      )
      styleOf('.so-signature', 'display:block;width:min(34vw,300px);height:auto;aspect-ratio:1080/330')
      styleOf(
        '.so-tagline',
        'font-size:15px;letter-spacing:.42em;text-indent:.42em;color:#e3d4b1;font-family:var(--dsw-font-family,serif)',
      )
      styleOf('.so-subtitle', 'font-size:9px;letter-spacing:.5em;text-indent:.5em;color:rgba(199,168,110,.55)')
      styleOf(
        '.so-skip',
        'position:absolute;right:22px;bottom:16px;font-size:11px;letter-spacing:.18em;color:rgba(235,227,209,.26)',
      )

      // The colour film is revealed once the trace has finished drawing; it is
      // only started shortly before that, so two 1080p decoders never compete
      // for the whole sequence.
      var colorFilm = root.querySelector('.so-color')
      if (colorFilm !== null) {
        colorFilm.style.cssText =
          'position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;visibility:hidden;transition:opacity 1s ease-out'
      }
      var traceFilm = root.querySelector('.so-trace')

      var finished = false
      var timer = null
      var reveal = null
      var finish = function () {
        if (finished) return
        finished = true
        if (timer !== null) clearTimeout(timer)
        if (reveal !== null) clearTimeout(reveal)
        root.removeEventListener('click', onSkip)
        document.removeEventListener('keydown', onKey, true)
        // Hand over the way the skin does: the whole plate eases back and
        // dissolves instead of cutting, so skipping lands in the app smoothly.
        root.style.transition = 'opacity .95s ease-out, transform .95s ease-out'
        root.style.transform = 'scale(1.025)'
        root.setAttribute('data-leaving', '')
        setTimeout(function () {
          var playing = root.querySelectorAll('video')
          for (var index = 0; index < playing.length; index += 1) {
            try {
              playing[index].pause()
              playing[index].removeAttribute('src')
              playing[index].load()
            } catch (error) {
              // Releasing media is best-effort.
            }
          }
          root.remove()
        }, 1000)
      }
      var onSkip = function () { finish() }
      var onKey = function (event) {
        // Any key continues, the way the skin's opening accepts a keystroke.
        if (event.key !== undefined) finish()
      }
      root.addEventListener('click', onSkip)
      document.addEventListener('keydown', onKey, true)
      // Safety net: the cover never outlives this, whatever happens below.
      timer = setTimeout(finish, 14000)

      /**
       * Start the sequence. The cover is already opaque on screen while the
       * app finishes its first paint, so the conversation page is never shown
       * before the opening — the animation just needs the shell to be ready
       * for its timing to be visible.
       */
      var startSequence = function () {
        if (finished) return
        // Only the trace plays for the first stretch. The colour film is 1080p
        // too, and decoding both at once starved the compositor — that is what
        // the visible stutter mid-sequence came from.
        if (traceFilm !== null) {
          traceFilm.muted = true
          // Only the first 2.6 s are used, so there is no loop point to glitch
          // on and no re-decode of the clip's tail.
          traceFilm.loop = false
          var traceStarted = traceFilm.play()
          if (traceStarted && typeof traceStarted.catch === 'function') traceStarted.catch(function () {})
        }
        if (colorFilm !== null) {
          setTimeout(function () {
            if (finished) return
            colorFilm.muted = true
            var colorStarted = colorFilm.play()
            if (colorStarted && typeof colorStarted.catch === 'function') colorStarted.catch(function () {})
          }, 1800)
        }
        reveal = setTimeout(function () {
          if (colorFilm !== null) {
            colorFilm.style.visibility = 'visible'
            colorFilm.style.opacity = '1'
          }
          if (stageNode !== null) stageNode.style.opacity = '0'
          if (signNode !== null) {
            signNode.style.visibility = 'visible'
            signNode.style.opacity = '1'
          }
          root.setAttribute('data-color', '')
          // The trace is invisible after its fade; stop decoding it.
          if (traceFilm !== null) setTimeout(function () { traceFilm.pause() }, 1200)
        }, 2600)

        fetch('/theme-sandrone/opening.json', { cache: 'no-store' })
          .then(function (response) { return response.json() })
          .then(function (data) {
            if (finished) return
            renderOpening(root, data)
            setTimeout(finish, 5600)
          })
          .catch(function () {
            // No scene data: the colour film still carries the opening.
            setTimeout(finish, 5200)
          })
      }

      whenWindowShown(startSequence, 12000)
    }

    /**
     * Run `callback` once the window is really on screen and painting.
     *
     * "The DOM has a frame element" is not the same as "the person can see the
     * window": the shell builds the page before it shows the window, so starting
     * on DOM readiness let the whole sequence play while the window was still
     * hidden — the first thing anyone saw was its last frame.
     *
     * The signal used here is real compositing plus focus: `requestAnimationFrame`
     * only ticks for a visible, drawing document, and `document.hasFocus()` adds
     * the case of a shown-and-focused window. A long cap keeps a hidden window
     * from leaving the cover up forever.
     * @param callback - receives control when the window is on screen.
     * @param maxWait - longest wait in milliseconds before proceeding anyway.
     */
    function whenWindowShown(callback, maxWait) {
      var started = false
      var cap = null
      var fire = function () {
        if (started) return
        started = true
        if (cap !== null) clearTimeout(cap)
        callback()
      }
      cap = setTimeout(fire, typeof maxWait === 'number' ? maxWait : 12000)

      // Three compositor frames: the document is visible and drawing.
      var frames = 0
      var frameStep = function () {
        if (started) return
        frames += 1
        var shell = document.querySelector('[data-shell-bottom]')
        if (shell === null) shell = document.querySelector('[class*="frame"]')
        if (frames >= 3 && shell !== null) {
          fire()
          return
        }
        if (typeof window.requestAnimationFrame === 'function') window.requestAnimationFrame(frameStep)
        else setTimeout(frameStep, 60)
      }

      var focusStep = function () {
        if (started) return
        if (document.hasFocus() && document.visibilityState === 'visible') {
          // Focus proves the window is shown; the frames prove it paints.
          if (typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(function () {
              window.requestAnimationFrame(fire)
            })
          } else {
            setTimeout(fire, 60)
          }
          return
        }
        setTimeout(focusStep, 120)
      }

      if (typeof window.requestAnimationFrame === 'function') window.requestAnimationFrame(frameStep)
      focusStep()
    }

    /**
     * Fill the sidebar's brand-mark slot with the workshop portrait.
     *
     * The slot is a *single* outlet that renders its highest-priority live
     * entry, so registering with `order: -1` shadows the official whale instead
     * of competing with it. If this component ever throws, the outlet abdicates
     * the entry and falls back to the whale — the failure mode is a stock icon,
     * not a missing section. This is the supported extension point; the earlier
     * DOM replacement broke React's reconciliation.
     * @param ctx - client root context carrying the slot registry.
     */
    function applyBrandSlot(ctx, attempt) {
      var tries = attempt === undefined ? 0 : attempt
      if (attempt === undefined) brandStatus = 'retry'
      try {
        // Cordis *throws* on an undeclared service ("cannot get property
        // "slots" without inject"), so it is not enough to test `ctx.slots`:
        // read the registry through the reflection API first, then fall back to
        // the plain property, each inside its own guard. Declaring `inject`
        // would make an absent slot service take the whole theme down with it.
        var slots
        if (typeof ctx.get === 'function') {
          try {
            slots = ctx.get('slots')
          } catch (error) {
            slots = undefined
          }
        }
        if (slots === undefined) {
          try {
            slots = ctx.slots
          } catch (error) {
            slots = undefined
          }
        }
        if (slots === undefined) {
          if (tries < 40) setTimeout(function () { applyBrandSlot(ctx, tries + 1) }, 250)
          else brandStatus = 'no-service'
          return
        }
        var react = require('react')
        var SandroneBrandMark = function (props) {
          var size = props !== undefined && props.size !== undefined ? props.size : 24
          return react.createElement('img', {
            src: ICON_URL,
            width: size,
            height: size,
            alt: '',
            'data-sandrone-brand': '',
            style: {
              width: size + 'px',
              height: size + 'px',
              borderRadius: '50%',
              objectFit: 'contain',
              display: 'block',
              filter: 'drop-shadow(0 0 6px rgba(199,168,110,.35))',
            },
          })
        }
        slots.inject('sidebar.brand.mark', function () {
          var release = slots.register(
            { name: 'sidebar.brand.mark', id: 'sandrone.brand.mark', order: -1 },
            SandroneBrandMark,
          )
          brandStatus = 'registered'
          return release
        })
      } catch (error) {
        brandStatus = 'error:' + String(error && error.message).slice(0, 60)
        // Keeping the official mark is an acceptable outcome.
      }
    }

    /**
     * Put a sidebar toggle in the title bar, left of the app menu.
     *
     * The shell's own control lives inside the sidebar, and that column sets
     * `backdrop-filter` — which makes it the containing block for `position:
     * fixed` descendants. Pinning the real button therefore only reached the
     * column's own top edge, and its `overflow` clipped it there. A dedicated
     * button on `<html>` (a layer React never reconciles, same as the opening
     * overlay) can sit anywhere; it forwards the click to the shell's control so
     * the shell keeps owning the state and the Ctrl+B shortcut.
     */
    function installTitlebarToggle() {
      try {
        if (document.querySelector('[data-sandrone-titlebar-toggle]') !== null) return
        var button = document.createElement('button')
        button.setAttribute('data-sandrone-titlebar-toggle', '')
        button.setAttribute('aria-label', '切换侧边栏')
        button.title = '切换侧边栏（Ctrl+B）'
        button.style.cssText = [
          'position:fixed',
          'left:8px',
          'top:5px',
          'width:26px',
          'height:26px',
          'padding:0',
          'display:flex',
          'align-items:center',
          'justify-content:center',
          'z-index:2147483000',
          'border:none',
          'border-radius:7px',
          'background:rgba(18,24,32,.55)',
          'color:#d9bd86',
          'cursor:pointer',
          '-webkit-app-region:no-drag',
          'transition:background .18s ease-out,color .18s ease-out',
        ].join(';')
        button.innerHTML =
          '<svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">' +
          '<rect x="1.25" y="2.25" width="13.5" height="11.5" rx="2.2" stroke="currentColor" stroke-width="1.3"/>' +
          '<path d="M6.1 2.5v11" stroke="currentColor" stroke-width="1.3"/>' +
          '</svg>'
        button.addEventListener('mouseenter', function () {
          button.style.background = 'rgba(199,168,110,.22)'
          button.style.color = '#f0dcb2'
        })
        button.addEventListener('mouseleave', function () {
          button.style.background = 'rgba(18,24,32,.55)'
          button.style.color = '#d9bd86'
        })
        /**
         * Width of the sidebar column, used to tell whether a toggle did anything.
         * The collapsed rail keeps the same element, only narrower.
         * @returns the column's width in pixels, or -1 when it is not mounted.
         */
        var sidebarWidth = function () {
          var column = document.querySelector('[class*="sidebarCol"]')
          return column === null ? -1 : Math.round(column.getBoundingClientRect().width)
        }

        /**
         * Find the shell's own sidebar control in whatever state it is in.
         *
         * The label flips between the two states, and the button is not always
         * mounted (the sidebar header can unmount with the column), which is why
         * a plain `click()` on a fixed selector silently did nothing once the
         * sidebar was collapsed.
         * @returns the toggle button, or null.
         */
        var findSidebarToggle = function () {
          var direct = document.querySelector(
            'button[aria-label="收起侧边栏"],button[aria-label="展开侧边栏"]',
          )
          if (direct !== null) return direct
          // Any control that mentions the sidebar but not the right-hand one.
          var candidates = document.querySelectorAll('button[aria-label*="侧边栏"],button[title*="侧边栏"]')
          for (var index = 0; index < candidates.length; index += 1) {
            var label = String(candidates[index].getAttribute('aria-label') || candidates[index].title || '')
            if (label.indexOf('右侧') === -1 && label.indexOf('右') === -1) return candidates[index]
          }
          return null
        }

        /**
         * Press the shell's keyboard shortcut for the same action.
         *
         * Dispatched on every plausible target: shells bind shortcuts on the
         * window, on the document, or on the app root, and a listener attached to
         * the root never sees an event fired at `window` after it stopped
         * bubbling. A synthetic event is not trusted, so the payload carries every
         * field a matcher may read (`key`, `code`, both key codes, modifiers).
         */
        var pressCtrlB = function () {
          var targets = [document.documentElement, document.body, document, window]
          for (var index = 0; index < targets.length; index += 1) {
            var node = targets[index]
            if (node === null || node === undefined) continue
            try {
              node.dispatchEvent(
                new KeyboardEvent('keydown', {
                  key: 'b',
                  code: 'KeyB',
                  keyCode: 66,
                  which: 66,
                  ctrlKey: true,
                  bubbles: true,
                  cancelable: true,
                  composed: true,
                }),
              )
              node.dispatchEvent(
                new KeyboardEvent('keyup', {
                  key: 'b',
                  code: 'KeyB',
                  keyCode: 66,
                  which: 66,
                  ctrlKey: true,
                  bubbles: true,
                  cancelable: true,
                  composed: true,
                }),
              )
            } catch (error) {
              // A read-only target is skipped; the next one is tried.
            }
          }
        }

        /** Report what the toggle attempt did, surfaced by the self-check. */
        var reportToggle = function (outcome, before, after) {
          toggleOutcome = outcome + ' ' + before + '->' + after
          try {
            var facts = new URLSearchParams()
            facts.set('v', '4')
            facts.set('from', 'toggle')
            facts.set('outcome', toggleOutcome)
            fetch('/theme-sandrone/report?' + facts.toString(), { cache: 'no-store' }).catch(function () {})
          } catch (error) {
            // Diagnostics are optional.
          }
        }

        /**
         * Try every way of opening the sidebar until its width actually changes.
         *
         * Clicking the shell's control works while the sidebar is open; once it
         * collapses, that control unmounts and the click goes nowhere. So each
         * strategy is followed by a measurement, and the next one runs only if the
         * column did not move.
         */
        var strategies = [
          function () {
            var target = findSidebarToggle()
            if (target !== null) target.click()
          },
          function () {
            pressCtrlB()
          },
          function () {
            // The collapsed rail itself may be the control.
            var rail = document.querySelector('[class*="railMark"]')
            var host = rail === null ? null : rail.closest('button, [role="button"]')
            if (host !== null) host.click()
          },
          function () {
            // Last resort: anything that looks like the sidebar entry point.
            var candidates = document.querySelectorAll('button[aria-label*="栏"],button[title*="栏"]')
            for (var index = 0; index < candidates.length; index += 1) {
              var label = String(candidates[index].getAttribute('aria-label') || candidates[index].title || '')
              if (label.indexOf('右侧') === -1 && label.indexOf('右 ') === -1) {
                candidates[index].click()
                return
              }
            }
          },
        ]

        button.addEventListener('click', function () {
          var before = sidebarWidth()
          var step = 0
          var attempt = function () {
            if (step >= strategies.length) {
              reportToggle('failed', before, sidebarWidth())
              return
            }
            strategies[step]()
            step += 1
            setTimeout(function () {
              if (sidebarWidth() !== before) reportToggle('ok@' + step, before, sidebarWidth())
              else attempt()
            }, 180)
          }
          attempt()
        })
        document.documentElement.appendChild(button)
      } catch (error) {
        // The shell's own control still works if this fails.
      }
    }

    /**
     * Mount the theme on the page.
     * @param ctx - the page's Cordis context; `effect` owns the teardown.
     */
    function apply(ctx) {
      ctx.effect(function () {
        var release = [ensureStylesheet(), holdDarkPalette()]
        return function () {
          for (var index = release.length - 1; index >= 0; index -= 1) release[index]()
        }
      }, 'theme-sandrone: stylesheet and palette')
      setTimeout(reportFacts, 1200)
      installTitlebarToggle()
      // Sidebar marks (brand portrait and the per-row ornaments) are painted by
      // theme.css: the brand slot is a hard single-occupant outlet that rejects
      // a second registration, and any node surgery here broke React.
      // Keep the tab icon on the theme art: a <link> href is not part of the tree.
      try {
        var tabIcons = document.querySelectorAll('link[rel="icon"], link[rel="shortcut icon"]')
        for (var tabIndex = 0; tabIndex < tabIcons.length; tabIndex += 1) {
          tabIcons[tabIndex].setAttribute('href', ICON_URL)
        }
      } catch (error) {
        // The tab icon is decoration.
      }
      // Cover the window immediately: the opening is the first thing on screen,
      // never the conversation page. The timeline starts once the shell paints.
      // A theme bug must never take the renderer down with it: a missing or
      // failed opening is an acceptable outcome, a thrown mount is not.
      try {
        playOpening()
      } catch (error) {
        // Continue straight to the working interface.
      }
    }

    exports.apply = apply
    return module.exports
  },
})
