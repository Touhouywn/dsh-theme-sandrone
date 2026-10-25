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

    /* ------------------------------------------------------------------
       Cinematic opening (v2) — Sandrone · 人偶工坊
       A boot sequence in the rhythm of the DeepSeek startup film: signature,
       telemetry, line-art tracing, a hard impact, then the artwork and the
       workshop wordmark. Every style is inline because the client kernel
       recycles plugin <style> tags, so this overlay is styled inline only).
       ------------------------------------------------------------------ */
    var OPENING_V2_SEEN = 'sandrone-opening-v17'
    var OPENING_V2_ART = '/theme-sandrone/opening-art.webp'
    var OPENING_V2_SCORE = '/theme-sandrone/opening-score-local.m4a'
    var OPENING_V2_SCORE_FALLBACK = '/theme-sandrone/opening-score.m4a'

    /**
     * Trace the vector outline and the signature for the cinematic opening.
     * The outline starts after the boot telemetry has been on screen for a
     * while, so the SVG work is not competing with the first paint.
     * @param root - opening overlay.
     * @param data - parsed opening.json.
     * @param outlineDelay - milliseconds before the character outline starts.
     */
    function renderOpeningV2(root, data, outlineDelay) {
      var reduce = false
      try {
        reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      } catch (error) {
        reduce = false
      }
      var outline = root.querySelector('.so-outline')
      var signature = root.querySelector('.so-signature')
      if (outline !== null && data && data.outline) {
        var groups = [
          { className: 'so-outline-body', paths: data.outline.paths || [], delay: outlineDelay, stagger: reduce ? 0 : 13, duration: reduce ? 1 : 520, paint: { stroke: '#f0b064', width: '1.7' } },
          { className: 'so-outline-face', paths: data.outline.facePaths || [], delay: outlineDelay + 1050, stagger: reduce ? 0 : 16, duration: reduce ? 1 : 440, paint: { stroke: '#ffe7c2', width: '1.35' } },
          { className: 'so-outline-water', paths: data.outline.waterPaths || [], delay: outlineDelay + 1250, stagger: 0, duration: reduce ? 1 : 900, paint: { stroke: '#8ac4ee', width: '1.4' } },
        ]
        for (var index = 0; index < groups.length; index += 1) {
          var group = groups[index]
          var node = svgNode('g', { class: group.className })
          node.style.opacity = group.className === 'so-outline-water' ? '.82' : '1'
          outline.appendChild(node)
          tracePaths(node, group.paths, group.delay, group.stagger, group.duration, group.paint)
        }
      }
      if (signature !== null && data && data.signature && data.signature.paths) {
        tracePaths(signature, data.signature.paths, reduce ? 0 : 0, reduce ? 0 : 95, reduce ? 1 : 540, {
          stroke: '#efe2c4',
          width: '2.5',
        })
      }
    }

    /**
     * Play the cinematic opening once per page session.
     *
     * The overlay covers the window immediately, then runs a ~16 s boot:
     * signature → telemetry → line-art → impact → artwork → wordmark. It is
     * skippable at any moment (click or any key) and has a hard safety net.
     * The score is one pre-mixed file, so picture and sound cannot drift.
     */
    function playOpeningCinematic() {
      if (document.getElementById(OPENING_ID) !== null) return
      var forced = false
      try {
        forced = window.location.hash.indexOf('opening') !== -1
        if (!forced) {
          if (window.sessionStorage.getItem(OPENING_V2_SEEN) === '1') return
          window.sessionStorage.setItem(OPENING_V2_SEEN, '1')
        }
      } catch (error) {
        // Storage unavailable: play it once per load.
      }

      var reduce = false
      try {
        reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      } catch (error) {
        reduce = false
      }

      var root = document.createElement('div')
      root.id = OPENING_ID
      root.style.cssText =
        'position:fixed;left:0;top:0;width:100vw;height:100vh;z-index:2147483000;overflow:hidden;background:#04060a;' +
        'opacity:1;transition:opacity .9s ease-out,transform .9s ease-out;font-family:var(--dsw-font-family,"Segoe UI",sans-serif);' +
        'color:#e9dfc9;user-select:none'
      root.innerHTML = [
        '<img class="so-art" alt="" decoding="async">',
        '<div class="so-veil-a"></div>',
        '<video class="so-trace" muted playsinline loop preload="auto" src="/theme-sandrone/trace.mp4"></video>',
        '<div class="so-veil-b"></div>',
        '<svg class="so-outline" viewBox="0 0 1280 720" preserveAspectRatio="xMidYMid slice"></svg>',
        '<div class="so-grain"></div>',
        '<svg class="so-ring" viewBox="0 0 400 400" aria-hidden="true">',
        '<circle cx="200" cy="200" r="186" fill="none" stroke="rgba(199,168,110,.22)" stroke-width="1" stroke-dasharray="1 7"></circle>',
        '<circle cx="200" cy="200" r="154" fill="none" stroke="rgba(199,168,110,.30)" stroke-width="1" stroke-dasharray="86 190"></circle>',
        '<circle cx="200" cy="200" r="118" fill="none" stroke="rgba(169,203,213,.16)" stroke-width="1"></circle>',
        '</svg>',
        '<div class="so-bignum">07</div>',
        '<div class="so-brand"><b>MARIONETTE</b><i>WORKSHOP · SYS-07</i></div>',
        '<div class="so-clock"><b>00:00</b><i>ELAPSED</i></div>',
        '<div class="so-log">',
        '<div class="so-logline"><span>›</span> 初始化 · 人偶工坊</div>',
        '<div class="so-logline"><span>›</span> 载入变量 · 桑多涅</div>',
        '<div class="so-logline"><span>›</span> 机构校准 · 人偶丝线</div>',
        '<div class="so-logline"><span>›</span> 权限确认 · 工坊主</div>',
        '</div>',
        '<div class="so-center">',
        '<div class="so-kicker">THE MARIONETTE WORKSHOP</div>',
        '<div class="so-headline">解算开始</div>',
        '<div class="so-sub">FORM THROUGH CALCULATION</div>',
        '</div>',
        '<div class="so-progress"><div class="so-progress-fill"></div></div>',
        '<div class="so-pct">000</div>',
        '<div class="so-diag">CHASSIS 07 · NEURAL LATTICE · 12 NODES</div>',
        '<div class="so-credit">SCORE · KEVIN MACLEOD · CC BY 4.0</div>',
        '<div class="so-sign"><svg class="so-signature" viewBox="0 0 1080 330" preserveAspectRatio="xMidYMid meet"></svg>',
        '<div class="so-tagline">机巧镀形，万理澄清</div>',
        '<div class="so-subtitle">MARIONETTE WORKSHOP</div></div>',
        '<div class="so-flash"></div>',
        '<div class="so-sound">♪ 点击启用声音</div>',
        '<div class="so-skip">点击 / 任意键 跳过</div>',
        '<audio class="so-score" preload="auto"></audio>',
        '<div class="so-c so-c-tl"></div>',
        '<div class="so-c so-c-tr"></div>',
        '<div class="so-c so-c-bl"></div>',
        '<div class="so-c so-c-br"></div>',
      ].join('')
      document.documentElement.appendChild(root)
      var mounted = root.getBoundingClientRect()
      if (mounted.width < window.innerWidth * 0.9 || mounted.height < window.innerHeight * 0.9) {
        document.body.appendChild(root)
      }

      var css = function (selector, text) {
        var node = root.querySelector(selector)
        if (node !== null) node.style.cssText = text
        return node
      }

      var art = css(
        '.so-art',
        'position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;object-position:64% 46%;opacity:0;' +
          'transform:scale(1.14);filter:saturate(1.05) contrast(1.03) brightness(.92);' +
          'transition:opacity 1.4s ease-out,transform 19s cubic-bezier(.16,.42,.2,1),filter 1.4s ease-out;will-change:transform,opacity',
      )
      var veilA = css(
        '.so-veil-a',
        'position:absolute;inset:0;background:radial-gradient(115% 80% at 64% 42%,rgba(4,6,10,.10) 0%,rgba(4,6,10,.62) 48%,#04060a 100%),' +
          'linear-gradient(180deg,rgba(3,5,9,.94) 0%,rgba(3,5,9,.30) 40%,rgba(3,5,9,.92) 100%);opacity:1;transition:opacity 1.2s ease-out',
      )
      var trace = css(
        '.so-trace',
        'position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;filter:brightness(.82) saturate(.9);' +
          'transition:opacity 1.6s ease-out',
      )
      var veilB = css(
        '.so-veil-b',
        'position:absolute;inset:0;background:radial-gradient(70% 60% at 62% 44%,rgba(120,180,210,.14) 0%,rgba(4,6,10,0) 58%),' +
          'linear-gradient(180deg,rgba(4,6,10,.52) 0%,rgba(4,6,10,.04) 40%,rgba(4,6,10,.88) 100%);opacity:0;transition:opacity 1.4s ease-out',
      )
      var outline = css(
        '.so-outline',
        'position:absolute;inset:0;width:100%;height:100%;opacity:1;transition:opacity 1.2s ease-out',
      )
      css(
        '.so-grain',
        'position:absolute;inset:0;pointer-events:none;opacity:.42;mix-blend-mode:overlay;' +
          'background:repeating-linear-gradient(0deg,rgba(255,255,255,.035) 0px,rgba(255,255,255,.035) 1px,transparent 1px,transparent 3px)',
      )
      var ring = css(
        '.so-ring',
        'position:absolute;left:50%;top:44%;width:min(62vh,520px);height:min(62vh,520px);' +
          'transform:translate(-50%,-50%) scale(1.35);opacity:0;transition:opacity 1.6s ease-out,transform 15s cubic-bezier(.16,.42,.2,1)',
      )
      css(
        '.so-bignum',
        'position:absolute;right:-1vw;top:50%;transform:translateY(-50%);font-size:34vh;line-height:.8;font-weight:200;' +
          'letter-spacing:-.04em;color:transparent;-webkit-text-stroke:1px rgba(199,168,110,.15);opacity:.55;font-family:ui-monospace,monospace',
      )
      var brand = css(
        '.so-brand',
        'position:absolute;left:34px;top:calc(24px + env(safe-area-inset-top));opacity:0;transition:opacity .9s ease-out;font-family:ui-monospace,monospace',
      )
      css('.so-brand b', 'display:block;font-size:13px;letter-spacing:.42em;color:rgba(232,216,182,.86);font-weight:500')
      css('.so-brand i', 'display:block;margin-top:7px;font-size:8px;letter-spacing:.34em;color:rgba(199,168,110,.55);font-style:normal')
      var clock = css(
        '.so-clock',
        'position:absolute;right:34px;top:calc(22px + env(safe-area-inset-top));text-align:right;font-family:ui-monospace,monospace;opacity:0;transition:opacity .9s ease-out',
      )
      var clockNum = css(
        '.so-clock b',
        'display:block;font-size:26px;letter-spacing:.08em;color:rgba(235,227,209,.86);font-variant-numeric:tabular-nums;font-weight:300',
      )
      css('.so-clock i', 'display:block;font-size:8px;letter-spacing:.3em;color:rgba(199,168,110,.5);font-style:normal;margin-top:4px')
      css(
        '.so-log',
        'position:absolute;left:7.5vw;bottom:calc(30px + env(safe-area-inset-bottom));font-family:ui-monospace,monospace;' +
          'font-size:10px;letter-spacing:.14em;color:rgba(235,227,209,.5);line-height:2.1',
      )
      css('.so-logline', 'opacity:0;transform:translateX(-8px);transition:opacity .5s ease-out,transform .5s ease-out')
      css('.so-logline span', 'color:#c7a86e;margin-right:8px')
      css(
        '.so-center',
        'position:absolute;left:7.5vw;top:50%;transform:translateY(-50%);width:min(46vw,720px);text-align:left;' +
          'font-family:var(--dsw-font-family,"Segoe UI",sans-serif)',
      )
      var kicker = css(
        '.so-kicker',
        'font-size:9px;letter-spacing:.6em;text-indent:.6em;color:rgba(199,168,110,.75);margin-bottom:22px;font-family:ui-monospace,monospace',
      )
      var headline = css(
        '.so-headline',
        'font-size:clamp(38px,4.8vw,72px);font-weight:200;letter-spacing:.12em;color:#f2e8d4;' +
          'text-shadow:0 0 40px rgba(199,168,110,.28),0 2px 30px rgba(0,0,0,.6);line-height:1.1;' +
          'transition:opacity .32s ease-out,transform .32s ease-out;opacity:1;transform:translateY(0)',
      )
      var sub = css(
        '.so-sub',
        'margin-top:14px;font-size:9px;letter-spacing:.38em;color:rgba(235,227,209,.42);font-family:ui-monospace,monospace',
      )
      var progress = css(
        '.so-progress',
        'position:absolute;left:7.5vw;bottom:calc(18vh + env(safe-area-inset-bottom));' +
          'width:min(34vw,400px);height:1px;background:rgba(199,168,110,.18);opacity:0;transition:opacity .8s ease-out',
      )
      var progressFill = css(
        '.so-progress-fill',
        'height:100%;width:0%;background:linear-gradient(90deg,rgba(199,168,110,.35),#c7a86e,#f0e0bd);' +
          'box-shadow:0 0 12px rgba(199,168,110,.55);transition:width .9s cubic-bezier(.2,.7,.2,1)',
      )
      var pct = css(
        '.so-pct',
        'position:absolute;left:calc(7.5vw + min(34vw,400px) + 14px);bottom:calc(18vh + env(safe-area-inset-bottom) - 9px);' +
          'font-family:ui-monospace,monospace;font-size:10px;letter-spacing:.18em;color:rgba(199,168,110,.7);' +
          'opacity:0;transition:opacity .8s ease-out;font-variant-numeric:tabular-nums',
      )
      css(
        '.so-credit',
        'position:absolute;right:34px;bottom:calc(14px + env(safe-area-inset-bottom));font-family:ui-monospace,monospace;' +
          'font-size:7px;letter-spacing:.18em;color:rgba(199,168,110,.26)',
      )
      var diag = css(
        '.so-diag',
        'position:absolute;right:34px;bottom:calc(30px + env(safe-area-inset-bottom));font-family:ui-monospace,monospace;' +
          'font-size:8px;letter-spacing:.22em;color:rgba(199,168,110,.32);opacity:0;transition:opacity .8s ease-out',
      )
      var sign = css(
        '.so-sign',
        'position:absolute;left:50%;bottom:calc(6vh + env(safe-area-inset-bottom));transform:translateX(-50%);' +
          'display:grid;justify-items:center;gap:8px;opacity:0;visibility:hidden;transition:opacity 1.1s ease-out;text-align:center',
      )
      css(
        '.so-signature',
        'display:block;width:min(30vw,260px);height:auto;aspect-ratio:1080/330;filter:drop-shadow(0 0 10px rgba(199,168,110,.35))',
      )
      var tagline = css(
        '.so-tagline',
        'font-size:14px;letter-spacing:.44em;text-indent:.44em;color:#e8d9b8;font-family:var(--dsw-font-family,serif);' +
          'text-shadow:0 0 18px rgba(199,168,110,.35);opacity:.55;transition:opacity .8s ease-out',
      )
      var subtitle = css(
        '.so-subtitle',
        'font-size:8px;letter-spacing:.52em;text-indent:.52em;color:rgba(199,168,110,.55);font-family:ui-monospace,monospace;opacity:.6',
      )
      var flash = css(
        '.so-flash',
        'position:absolute;inset:0;pointer-events:none;opacity:0;' +
          'background:radial-gradient(circle at 62% 44%,rgba(255,246,226,.95) 0%,rgba(228,196,140,.55) 24%,rgba(199,168,110,0) 62%)',
      )
      var sound = css(
        '.so-sound',
        'position:absolute;left:7.5vw;bottom:calc(92px + env(safe-area-inset-bottom));padding:7px 12px;' +
          'border:1px solid rgba(199,168,110,.35);background:rgba(8,11,17,.55);color:rgba(235,227,209,.8);' +
          'font-family:ui-monospace,monospace;font-size:9px;letter-spacing:.18em;opacity:0;transition:opacity .4s ease-out;' +
          'cursor:pointer;pointer-events:auto;backdrop-filter:blur(6px)',
      )
      css(
        '.so-skip',
        'position:absolute;right:34px;bottom:calc(56px + env(safe-area-inset-bottom));font-family:ui-monospace,monospace;' +
          'font-size:9px;letter-spacing:.18em;color:rgba(235,227,209,.28)',
      )
      css('.so-score', 'display:none')
      var cornerBase =
        'position:absolute;width:26px;height:26px;border-color:rgba(199,168,110,.28);border-style:solid;border-width:0;' +
        'opacity:0;transition:opacity 1s ease-out'
      var tl = css('.so-c-tl', cornerBase + ';left:20px;top:calc(18px + env(safe-area-inset-top));border-left-width:1px;border-top-width:1px')
      var tr = css('.so-c-tr', cornerBase + ';right:20px;top:calc(18px + env(safe-area-inset-top));border-right-width:1px;border-top-width:1px')
      var bl = css('.so-c-bl', cornerBase + ';left:20px;bottom:calc(18px + env(safe-area-inset-bottom));border-left-width:1px;border-bottom-width:1px')
      var br = css('.so-c-br', cornerBase + ';right:20px;bottom:calc(18px + env(safe-area-inset-bottom));border-right-width:1px;border-bottom-width:1px')

      var score = root.querySelector('.so-score')
      if (score !== null) {
        // Prefer the local score (BGM + voice clips). A public checkout ships
        // only the BGM bed, so a 404 falls back without a second thought.
        score.addEventListener(
          'error',
          function () {
            if (score.getAttribute('data-fallback') === '1') return
            score.setAttribute('data-fallback', '1')
            score.src = OPENING_V2_SCORE_FALLBACK
            score.load()
          },
          true,
        )
        score.src = OPENING_V2_SCORE
        score.volume = 0.88
        try {
          score.load()
        } catch (error) {
          // A missing score is not fatal: the sequence stays visual.
        }
      }
      if (art !== null) {
        art.onerror = function () {
          art.style.display = 'none'
        }
        art.src = OPENING_V2_ART
      }

      var logs = root.querySelectorAll('.so-logline')
      var timers = []
      var clockTimer = null
      var startedAt = 0
      var finished = false
      var audioStarted = false

      var at = function (delay, callback) {
        timers.push(setTimeout(callback, delay))
      }
      var showLog = function (index) {
        if (logs[index] === undefined) return
        logs[index].style.opacity = '1'
        logs[index].style.transform = 'translateX(0)'
      }
      var setProgress = function (value) {
        if (progressFill !== null) progressFill.style.width = value + '%'
        if (pct !== null) pct.textContent = String(value).padStart(3, '0')
      }
      var glitch = function () {
        if (headline === null) return
        headline.style.textShadow =
          '2px 0 rgba(153,62,80,.55),-2px 0 rgba(169,203,213,.45),0 0 40px rgba(199,168,110,.28)'
        setTimeout(function () {
          if (headline !== null) headline.style.textShadow = '0 0 40px rgba(199,168,110,.28),0 2px 30px rgba(0,0,0,.6)'
        }, 160)
      }
      var setHeadline = function (text, caption) {
        if (headline === null) return
        headline.style.opacity = '0'
        headline.style.transform = 'translateY(10px)'
        setTimeout(function () {
          if (finished || headline === null) return
          headline.textContent = text
          if (sub !== null && caption !== undefined) sub.textContent = caption
          headline.style.opacity = '1'
          headline.style.transform = 'translateY(0)'
          glitch()
        }, 170)
      }
      var pulse = function () {
        if (flash === null) return
        flash.style.transition = 'none'
        flash.style.opacity = '.95'
        requestAnimationFrame(function () {
          if (flash === null) return
          flash.style.transition = 'opacity 1.15s ease-out'
          flash.style.opacity = '0'
        })
      }
      var reveal = function () {
        if (art !== null) {
          art.style.opacity = '1'
          art.style.transform = 'scale(1.02)'
          art.style.filter = 'saturate(1.06) contrast(1.03) brightness(1.02)'
        }
        if (veilA !== null) veilA.style.opacity = '.18'
        if (veilB !== null) veilB.style.opacity = '1'
        if (trace !== null) trace.style.opacity = '0'
        if (outline !== null) outline.style.opacity = '0'
        if (ring !== null) {
          ring.style.opacity = '.55'
          ring.style.transform = 'translate(-50%,-50%) scale(1)'
        }
        if (sign !== null) {
          sign.style.visibility = 'visible'
          sign.style.opacity = '1'
        }
        pulse()
        setProgress(100)
        setHeadline('机巧镀形', 'FORM THROUGH CALCULATION')
        if (kicker !== null) kicker.textContent = 'THE MARIONETTE WORKSHOP'
      }
      var tryScore = function () {
        if (score === null || audioStarted) return
        audioStarted = true
        var played = score.play()
        if (played && typeof played.then === 'function') {
          played
            .then(function () {
              if (sound !== null) sound.style.opacity = '0'
            })
            .catch(function () {
              audioStarted = false
              if (sound !== null) sound.style.opacity = '1'
            })
        }
      }
      var updateClock = function () {
        if (clockNum === null || startedAt === 0) return
        var seconds = Math.min(99, Math.floor((performance.now() - startedAt) / 1000))
        clockNum.textContent = '00:' + String(seconds).padStart(2, '0')
      }

      var finish = function () {
        if (finished) return
        finished = true
        for (var index = 0; index < timers.length; index += 1) clearTimeout(timers[index])
        if (clockTimer !== null) clearInterval(clockTimer)
        root.removeEventListener('click', onSkip)
        document.removeEventListener('keydown', onKey, true)
        if (score !== null) {
          try {
            score.pause()
            score.removeAttribute('src')
            score.load()
          } catch (error) {
            // Releasing media is best-effort.
          }
        }
        if (trace !== null) {
          try {
            trace.pause()
            trace.removeAttribute('src')
            trace.load()
          } catch (error) {
            // Releasing the trace video is best-effort.
          }
        }
        root.style.transition = 'opacity .9s ease-out,transform .9s ease-out'
        root.style.opacity = '0'
        root.style.transform = 'scale(1.03)'
        root.setAttribute('data-leaving', '')
        setTimeout(function () {
          root.remove()
        }, 950)
      }
      var onSkip = function () {
        finish()
      }
      var onKey = function (event) {
        if (event.key !== undefined) finish()
      }
      root.addEventListener('click', onSkip)
      document.addEventListener('keydown', onKey, true)
      if (sound !== null) {
        sound.addEventListener('click', function (event) {
          event.stopPropagation()
          tryScore()
        })
      }
      // Safety net: the cover never outlives this, whatever happens below.
      var safety = setTimeout(finish, 22000)
      timers.push(safety)

      var startTimeline = function () {
        if (finished) return
        startedAt = performance.now()
        clockTimer = setInterval(updateClock, 200)
        at(120, function () {
          if (brand !== null) brand.style.opacity = '1'
          if (clock !== null) clock.style.opacity = '1'
          if (diag !== null) diag.style.opacity = '1'
          if (tl !== null) tl.style.opacity = '1'
          if (tr !== null) tr.style.opacity = '1'
          if (bl !== null) bl.style.opacity = '1'
          if (br !== null) br.style.opacity = '1'
          if (progress !== null) progress.style.opacity = '1'
          if (pct !== null) pct.style.opacity = '1'
        })
        at(320, function () {
          tryScore()
        })
        at(520, function () {
          showLog(0)
        })
        at(1350, function () {
          setHeadline('解算开始', 'INITIALIZING')
          setProgress(6)
        })
        at(1850, function () {
          if (trace === null) return
          trace.style.opacity = '.55'
          var played = trace.play()
          if (played && typeof played.catch === 'function') played.catch(function () {})
        })
        at(2350, function () {
          showLog(1)
          setProgress(14)
        })
        at(3050, function () {
          setHeadline('载入变量', 'LOADING VARIABLES')
          setProgress(26)
        })
        at(3950, function () {
          showLog(2)
          setProgress(40)
        })
        at(5050, function () {
          setHeadline('机构校准', 'CALIBRATING CHASSIS')
          setProgress(54)
        })
        at(6050, function () {
          showLog(3)
          setProgress(68)
        })
        at(6950, function () {
          setHeadline('进程良好', 'PROCESS NOMINAL')
          setProgress(84)
        })
        at(8350, function () {
          setHeadline('析构万理', 'DECONSTRUCTING FORM')
          setProgress(94)
        })
        at(9600, reveal)
        at(11250, function () {
          if (kicker !== null) kicker.textContent = 'WELCOME TO'
          setHeadline('人偶工坊', 'THE MARIONETTE WORKSHOP')
        })
        at(12900, function () {
          if (tagline !== null) tagline.style.opacity = '1'
          if (subtitle !== null) subtitle.style.opacity = '1'
          if (diag !== null) diag.textContent = 'ACCESS GRANTED · WORKSHOP MASTER · 桑多涅'
        })
        at(14900, function () {
          root.style.opacity = '0'
          root.style.transform = 'scale(1.03)'
        })
        at(16000, finish)

        if (reduce) {
          // Respect reduced motion: show the finished plate, then leave.
          for (var index = 0; index < timers.length; index += 1) clearTimeout(timers[index])
          timers.length = 0
          if (clockTimer !== null) clearInterval(clockTimer)
          if (brand !== null) brand.style.opacity = '1'
          if (clock !== null) clock.style.opacity = '1'
          if (progress !== null) progress.style.opacity = '1'
          if (pct !== null) pct.style.opacity = '1'
          reveal()
          if (headline !== null) {
            headline.textContent = '人偶工坊'
            headline.style.opacity = '1'
            headline.style.transform = 'translateY(0)'
          }
          if (kicker !== null) kicker.textContent = 'WELCOME TO'
          setTimeout(finish, 3400)
        }
      }

      var loadScene = function () {
        fetch('/theme-sandrone/opening.json', { cache: 'no-store' })
          .then(function (response) {
            return response.json()
          })
          .then(function (data) {
            if (finished) return
            renderOpeningV2(root, data, 2600)
          })
          .catch(function () {
            // No scene data: the artwork, telemetry and score still carry it.
          })
      }

      loadScene()
      whenWindowShown(startTimeline, 12000)
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
        playOpeningCinematic()
      } catch (error) {
        // Continue straight to the working interface.
      }
    }

    exports.apply = apply
    return module.exports
  },
})
