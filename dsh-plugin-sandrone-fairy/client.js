/**
 * sandrone-fairy — client half (browser).
 *
 * One overlay owns three things:
 *   1. the boot splash (deep navy + violet clockwork, ~3.6s or click to skip),
 *   2. the floating marionette (draggable, idle murmur, click to talk),
 *   3. the transcript panel with voice mode (speechSynthesis, zh-CN).
 *
 * The model call lives in the host half behind POST /sandrone/chat, streaming
 * newline-delimited JSON so the reply renders while it is being written.
 */

window.__ModuleLoader__.load({
  id: 'sandrone-fairy',
  factory: (require) => {
    const React = require('react')
    const h = React.createElement
    const { useCallback, useEffect, useMemo, useRef, useState } = React

    const CSS_ID = 'sandrone-fairy-styles'
    const STORAGE_KEY = 'sandrone-fairy:v1'
    const CHAT_PATH = '/sandrone/chat'
    const PING_PATH = '/sandrone/ping'

    /* ──────────────────────────── palette / CSS ──────────────────────────── */

    const CSS = `
.sdf-root {
  --sdf-w: min(400px, 29vw);
  --sdf-h: var(--sdf-w);
  position: fixed; inset: 0; z-index: 900; pointer-events: none;
}
.sdf-ambient {
  position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background:
    radial-gradient(58% 46% at 8% -6%, rgba(96, 52, 210, .30), rgba(96, 52, 210, 0) 68%),
    radial-gradient(46% 42% at 96% 2%, rgba(28, 78, 178, .26), rgba(28, 78, 178, 0) 70%),
    radial-gradient(64% 52% at 52% 112%, rgba(124, 62, 210, .22), rgba(124, 62, 210, 0) 70%);
  mix-blend-mode: screen;
  opacity: .9;
}
.sdf-root * { box-sizing: border-box; }

/* ---------- fairy ---------- */
.sdf-fairy {
  position: fixed; width: 168px; height: 216px;
  pointer-events: auto; cursor: grab; touch-action: none;
  filter: drop-shadow(0 18px 34px rgba(60, 18, 120, .55));
  transition: filter .35s ease, transform .18s ease;
  will-change: transform;
}
.sdf-fairy:hover { filter: drop-shadow(0 20px 44px rgba(150, 96, 255, .6)); }
.sdf-fairy.sdf-dragging { cursor: grabbing; transform: scale(1.04); }
.sdf-fairy.sdf-enter { animation: sdf-materialize 1.1s cubic-bezier(.2,.9,.2,1) both; }
@keyframes sdf-materialize {
  0% { opacity: 0; transform: translateY(26px) scale(.82); filter: blur(10px) drop-shadow(0 0 0 transparent); }
  60% { opacity: 1; transform: translateY(-6px) scale(1.02); filter: blur(0) drop-shadow(0 18px 34px rgba(60,18,120,.5)); }
  100% { opacity: 1; transform: translateY(0) scale(1); }
}
.sdf-bob { width: 100%; height: 100%; animation: sdf-float 6.4s ease-in-out infinite; }
.sdf-fairy-burst {
  position: absolute; left: 50%; top: 48%; width: 118px; height: 118px; margin: -59px 0 0 -59px;
  border-radius: 50%; border: 1px solid rgba(178, 224, 255, .9); opacity: 0; pointer-events: none;
  box-shadow: 0 0 30px rgba(140, 200, 255, .35) inset;
  animation: sdf-fairy-pop 1.55s cubic-bezier(.15, .75, .3, 1) .12s both;
}
@keyframes sdf-fairy-pop {
  0% { opacity: .92; transform: scale(.22); }
  58% { opacity: .3; }
  100% { opacity: 0; transform: scale(2); }
}
@keyframes sdf-float {
  0%, 100% { transform: translateY(0) rotate(-.6deg); }
  50% { transform: translateY(-11px) rotate(.8deg); }
}
.sdf-fairy.sdf-speaking .sdf-bob { animation-duration: 3.1s; }
.sdf-art { width: 100%; height: 100%; overflow: visible; }
.sdf-halo-slow { animation: sdf-spin 26s linear infinite; transform-origin: 100px 118px; }
.sdf-halo-fast { animation: sdf-spin-rev 16s linear infinite; transform-origin: 100px 118px; }
.sdf-gear-a { animation: sdf-spin 34s linear infinite; transform-origin: 100px 152px; }
.sdf-gear-b { animation: sdf-spin-rev 11s linear infinite; transform-origin: 44px 196px; }
.sdf-gear-c { animation: sdf-spin 12s linear infinite; transform-origin: 124px 66px; }
@keyframes sdf-spin { to { transform: rotate(360deg); } }
@keyframes sdf-spin-rev { to { transform: rotate(-360deg); } }
.sdf-eye-glow { animation: sdf-pulse 4.2s ease-in-out infinite; transform-origin: center; }
.sdf-hair-tail { transform-origin: 100px 40px; animation: sdf-sway 6.2s ease-in-out infinite; }
@keyframes sdf-sway { 0%, 100% { transform: rotate(-1.4deg); } 50% { transform: rotate(1.4deg); } }
.sdf-ribbon { transform-origin: 126px 47px; animation: sdf-flutter 3.6s ease-in-out infinite; }
@keyframes sdf-flutter { 0%, 100% { transform: rotate(-3deg) skewX(2deg); } 50% { transform: rotate(4deg) skewX(-3deg); } }
.sdf-cup { transform-origin: 131px 137px; animation: sdf-cup-bob 4.6s ease-in-out infinite; }
@keyframes sdf-cup-bob { 0%, 100% { transform: translateY(0) rotate(-1deg); } 50% { transform: translateY(-1.8px) rotate(1.4deg); } }
@keyframes sdf-pulse { 0%,100% { opacity: .55; } 50% { opacity: 1; } }
.sdf-mouth { transform-origin: 100px 80px; }
.sdf-fairy.sdf-speaking .sdf-mouth { animation: sdf-talk .42s ease-in-out infinite; }
@keyframes sdf-talk { 0%,100% { transform: scaleY(1); } 50% { transform: scaleY(2.1); } }
.sdf-blink { transform-origin: center; animation: sdf-blink 7.5s ease-in-out infinite; }
@keyframes sdf-blink { 0%, 94%, 100% { transform: scaleY(1); } 96% { transform: scaleY(.08); } }
.sdf-fairy:focus-visible { outline: 2px solid rgba(178,132,255,.8); outline-offset: 6px; border-radius: 90px; }

/* ---------- whisper bubble above the fairy ---------- */
.sdf-fairy.sdf-right .sdf-whisper { left: auto; right: calc(var(--sdf-w) * .42); border-radius: 14px 14px 14px 4px; }
.sdf-whisper {
  position: absolute; left: calc(var(--sdf-w) * .58); bottom: calc(var(--sdf-h) * .52); width: max-content; max-width: 232px;
  padding: 10px 14px; border-radius: 14px 14px 14px 4px;
  background: linear-gradient(150deg, rgba(28, 20, 66, .96), rgba(10, 14, 40, .96));
  border: 1px solid rgba(160, 107, 255, .32);
  color: #ece7ff; font-size: 13px; line-height: 1.65; letter-spacing: .02em;
  box-shadow: 0 12px 34px rgba(0, 0, 0, .5), inset 0 0 24px rgba(120, 70, 220, .12);
  animation: sdf-whisper-in .5s cubic-bezier(.2,.9,.2,1) both;
  pointer-events: auto; cursor: pointer; white-space: pre-wrap;
}
@keyframes sdf-whisper-in { from { opacity: 0; transform: translateY(8px) scale(.96); } to { opacity: 1; transform: none; } }

/* ---------- panel ---------- */
.sdf-panel {
  position: fixed; right: 22px; top: 20px; width: 372px; max-width: calc(100vw - 28px);
  height: min(520px, calc(100vh - 44px));
  display: flex; flex-direction: column; pointer-events: auto;
  border-radius: 18px; overflow: hidden;
  background:
    radial-gradient(120% 80% at 100% 0%, rgba(126, 70, 220, .26), transparent 62%),
    radial-gradient(90% 60% at 0% 100%, rgba(40, 60, 160, .22), transparent 70%),
    linear-gradient(165deg, rgba(14, 18, 48, .97), rgba(6, 8, 24, .98));
  border: 1px solid rgba(150, 104, 255, .3);
  box-shadow: 0 28px 70px rgba(0, 0, 0, .62), inset 0 1px 0 rgba(190, 160, 255, .14);
  backdrop-filter: blur(16px) saturate(1.1);
  animation: sdf-panel-in .34s cubic-bezier(.2,.9,.2,1) both;
  font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", system-ui, sans-serif;
  color: #eae5ff;
}
@keyframes sdf-panel-in { from { opacity: 0; transform: translateY(14px) scale(.97); } to { opacity: 1; transform: none; } }
.sdf-panel::before {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background:
    repeating-linear-gradient(115deg, rgba(255,255,255,.022) 0 1px, transparent 1px 9px);
  opacity: .6;
}
.sdf-head {
  position: relative; display: flex; align-items: center; gap: 10px;
  padding: 13px 14px 12px 16px;
  border-bottom: 1px solid rgba(150, 104, 255, .18);
  background: linear-gradient(180deg, rgba(46, 30, 92, .5), rgba(12, 14, 38, 0));
}
.sdf-mark {
  width: 30px; height: 30px; border-radius: 50%; flex: 0 0 auto;
  display: grid; place-items: center;
  background: radial-gradient(circle at 34% 30%, #3b2a72, #0e1030 72%);
  border: 1px solid rgba(190, 150, 255, .42);
  box-shadow: 0 0 16px rgba(140, 80, 240, .38);
}
.sdf-name { font-size: 14.5px; letter-spacing: .3em; font-weight: 600; color: #f2ecff; }
.sdf-sub { margin-top: 2px; font-size: 10.5px; letter-spacing: .16em; color: #968ec4; }
.sdf-head-actions { margin-left: auto; display: flex; align-items: center; gap: 6px; }
.sdf-icon-btn {
  width: 28px; height: 28px; display: grid; place-items: center;
  border-radius: 9px; border: 1px solid rgba(150, 120, 230, .22);
  background: rgba(255,255,255,.03); color: #bdb2e6; cursor: pointer;
  transition: all .18s ease;
}
.sdf-icon-btn:hover { color: #f0e9ff; border-color: rgba(180, 140, 255, .5); background: rgba(140, 90, 240, .16); }
.sdf-icon-btn.sdf-on { color: #cbb0ff; border-color: rgba(178, 132, 255, .55); background: rgba(140, 90, 240, .2); box-shadow: 0 0 14px rgba(150, 90, 250, .3); }
.sdf-log {
  flex: 1 1 auto; overflow-y: auto; overscroll-behavior: contain;
  padding: 16px 16px 8px; display: flex; flex-direction: column; gap: 11px;
  scrollbar-width: thin; scrollbar-color: rgba(150, 110, 240, .5) transparent;
}
.sdf-log::-webkit-scrollbar { width: 6px; }
.sdf-log::-webkit-scrollbar-thumb { background: rgba(150, 110, 240, .45); border-radius: 4px; }
.sdf-row { display: flex; flex-direction: column; gap: 4px; max-width: 100%; }
.sdf-row.sdf-me { align-items: flex-end; }
.sdf-bubble {
  position: relative; max-width: 86%; padding: 9px 13px;
  font-size: 13.2px; line-height: 1.78; letter-spacing: .015em; white-space: pre-wrap; word-break: break-word;
  border-radius: 13px 13px 13px 4px;
  background: linear-gradient(160deg, rgba(58, 38, 112, .55), rgba(14, 18, 46, .8));
  border: 1px solid rgba(150, 108, 255, .22);
  box-shadow: inset 0 1px 0 rgba(200, 175, 255, .08);
}
.sdf-row.sdf-me .sdf-bubble {
  border-radius: 13px 13px 4px 13px;
  background: linear-gradient(160deg, rgba(96, 54, 180, .34), rgba(28, 24, 66, .8));
  border-color: rgba(168, 122, 255, .34);
  color: #f4efff;
}
.sdf-bubble.sdf-err { border-color: rgba(255, 130, 170, .4); color: #ffc9dc; background: rgba(70, 20, 44, .5); }
.sdf-tag { font-size: 10px; letter-spacing: .18em; color: #7f78ad; padding-left: 3px; }
.sdf-row.sdf-me .sdf-tag { padding-left: 0; padding-right: 3px; }
.sdf-caret { display: inline-block; width: 6px; height: 13px; margin-left: 2px; vertical-align: -2px; background: #b285ff; opacity: .85; animation: sdf-caret 1s steps(2, start) infinite; }
@keyframes sdf-caret { to { opacity: 0; } }
.sdf-empty { margin: auto 0; padding: 6px 4px 10px; color: #8e87b8; font-size: 12.5px; line-height: 1.9; letter-spacing: .04em; }
.sdf-chips { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 12px; }
.sdf-chip {
  padding: 6px 11px; font-size: 12px; letter-spacing: .04em; cursor: pointer;
  color: #c9b9f2; border-radius: 999px; border: 1px solid rgba(150, 108, 255, .28);
  background: rgba(120, 74, 210, .1); transition: all .16s ease;
}
.sdf-chip:hover { color: #f6efff; border-color: rgba(190, 150, 255, .6); background: rgba(140, 90, 240, .22); }
.sdf-compose { padding: 10px 12px 12px; border-top: 1px solid rgba(150, 104, 255, .16); background: linear-gradient(0deg, rgba(20, 16, 52, .7), transparent); }
.sdf-input-wrap {
  display: flex; align-items: flex-end; gap: 8px; padding: 8px 8px 8px 12px;
  border-radius: 14px; border: 1px solid rgba(150, 108, 255, .26);
  background: rgba(8, 10, 32, .72); transition: border-color .2s ease, box-shadow .2s ease;
}
.sdf-input-wrap:focus-within { border-color: rgba(190, 150, 255, .6); box-shadow: 0 0 0 3px rgba(140, 90, 240, .14); }
.sdf-input {
  flex: 1 1 auto; resize: none; border: 0; outline: 0; background: transparent;
  color: #eae5ff; font-size: 13.2px; line-height: 1.7; max-height: 92px; min-height: 22px;
  font-family: inherit; padding: 0;
}
.sdf-input::placeholder { color: #6f689b; }
.sdf-send {
  flex: 0 0 auto; width: 32px; height: 32px; border-radius: 10px; border: 1px solid rgba(190, 150, 255, .45);
  background: linear-gradient(160deg, rgba(150, 90, 250, .55), rgba(70, 40, 150, .5));
  color: #fff; display: grid; place-items: center; cursor: pointer; transition: all .18s ease;
}
.sdf-send:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(120, 60, 230, .4); }
.sdf-send:disabled { opacity: .4; cursor: default; }
.sdf-foot { display: flex; align-items: center; gap: 10px; margin-top: 8px; padding: 0 3px; }
.sdf-link { display: inline-flex; align-items: center; gap: 5px; font-size: 10.5px; letter-spacing: .1em; color: #867fae; }
.sdf-dot { width: 5px; height: 5px; border-radius: 50%; background: #6b6590; }
.sdf-link.sdf-ok .sdf-dot { background: #9d7bff; box-shadow: 0 0 8px rgba(160, 120, 255, .9); }
.sdf-link.sdf-bad .sdf-dot { background: #ff9a7a; box-shadow: 0 0 8px rgba(255, 140, 110, .8); }
.sdf-foot-spacer { flex: 1 1 auto; }
.sdf-voice-tag {
  font: inherit; font-size: 11px; color: rgba(188, 172, 224, .62); margin-right: 12px;
  white-space: nowrap; background: none; border: 0; padding: 2px 4px; border-radius: 6px;
  cursor: pointer; transition: color .2s ease, background .2s ease;
}
.sdf-voice-tag:hover { color: #d9c9f8; background: rgba(126, 96, 226, .16); }
.sdf-voice-tag.is-clone { color: #c7a6ff; }
.sdf-text-btn {
  border: 0; background: transparent; color: #8b84b4; font-size: 11px; letter-spacing: .08em;
  cursor: pointer; padding: 3px 5px; border-radius: 6px; font-family: inherit;
}
.sdf-text-btn:hover { color: #d8ccff; background: rgba(140, 100, 230, .12); }

/* ---------- splash ---------- */
.sdf-splash {
  position: fixed; inset: 0; z-index: 2200; pointer-events: auto;
  display: grid; place-items: center; overflow: hidden;
  background:
    radial-gradient(120% 90% at 50% 118%, rgba(96, 48, 190, .34), transparent 60%),
    radial-gradient(80% 70% at 82% -10%, rgba(44, 118, 210, .30), transparent 62%),
    radial-gradient(70% 62% at 8% 22%, rgba(150, 70, 220, .20), transparent 60%),
    radial-gradient(52% 44% at 50% 44%, rgba(52, 148, 214, .16), transparent 68%),
    linear-gradient(175deg, #05081b 0%, #08122f 46%, #04061a 100%);
  animation: sdf-splash-art 9s ease-in-out infinite alternate;
  transition: opacity .9s ease, filter .9s ease;
}
@keyframes sdf-splash-art { from { background-position: 0 0, 0 0, 0 0, 0 0, 0 0; } to { background-position: 12px -8px, -10px 6px, 8px 4px, 0 0, 0 0; } }
.sdf-splash.sdf-leaving { opacity: 0; filter: blur(14px); pointer-events: none; }
.sdf-splash::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background:
    repeating-linear-gradient(0deg, rgba(255,255,255,.024) 0 1px, transparent 1px 3px),
    radial-gradient(90% 80% at 50% 50%, transparent 40%, rgba(0,0,0,.72) 100%);
  mix-blend-mode: screen; opacity: .55;
}
.sdf-splash-inner { position: relative; display: flex; flex-direction: column; align-items: center; gap: 4px; transform: translateY(-2vh); }
.sdf-splash-art-wrap { position: relative; display: grid; place-items: center; width: 340px; height: 340px; margin-bottom: 2px; }
.sdf-splash-stage { position: absolute; inset: 0; display: grid; place-items: center; }
.sdf-splash-ring { position: absolute; inset: -9%; width: 118%; height: 118%; overflow: visible; }
.sdf-splash-glow {
  position: absolute; width: 118%; height: 118%; border-radius: 50%;
  background: radial-gradient(circle, rgba(126, 208, 255, .22) 0%, rgba(96, 66, 210, .16) 42%, transparent 68%);
  filter: blur(10px); animation: sdf-fade 2.6s ease .1s both;
}
.sdf-gear-big { transform-origin: 170px 170px; animation: sdf-spin 84s linear infinite, sdf-gear-in 2.2s ease .15s both; }
.sdf-gear-mid { transform-origin: 170px 170px; animation: sdf-spin-rev 46s linear infinite, sdf-gear-in 2.4s ease .35s both; }
.sdf-gear-hair { transform-origin: 170px 170px; animation: sdf-spin 130s linear infinite, sdf-gear-in 2.6s ease .55s both; }
@keyframes sdf-gear-in { from { opacity: 0; } to { opacity: 1; } }
.sdf-snow { position: absolute; inset: -6%; pointer-events: none; overflow: hidden; }
.sdf-snow i {
  position: absolute; top: 0; display: block; border-radius: 50%; background: #d6ecff;
  box-shadow: 0 0 9px rgba(150, 214, 255, .95); animation: sdf-snowfall linear infinite;
}
@keyframes sdf-snowfall {
  0% { opacity: 0; transform: translate3d(0, -16vh, 0); }
  12% { opacity: .9; }
  86% { opacity: .6; }
  100% { opacity: 0; transform: translate3d(var(--sdf-drift, 0px), 76vh, 0); }
}
.sdf-beam {
  position: absolute; left: 50%; top: 46%; width: 128vw; height: 130px;
  transform: translate(-50%, -50%) rotate(-27deg);
  background: linear-gradient(90deg, transparent, rgba(120, 194, 255, .13) 32%, rgba(196, 152, 255, .2) 52%, rgba(120, 194, 255, .12) 68%, transparent);
  filter: blur(20px); opacity: 0; animation: sdf-beam-in 3.6s ease .3s both; pointer-events: none;
}
@keyframes sdf-beam-in { 0% { opacity: 0; } 32% { opacity: .85; } 100% { opacity: .28; } }
.sdf-splash-figure { position: relative; width: 238px; height: 309px; opacity: .97; animation: sdf-pop-in 1.6s cubic-bezier(.2, .9, .25, 1) .4s both; }
@keyframes sdf-pop-in {
  0% { opacity: 0; transform: translateY(40px) scale(.56); filter: blur(18px); }
  46% { opacity: 1; transform: translateY(-9px) scale(1.07); filter: blur(0); }
  66% { transform: translateY(3px) scale(.985); }
  84% { transform: translateY(-2px) scale(1.012); }
  100% { opacity: .97; transform: translateY(0) scale(1); filter: blur(0); }
}
.sdf-burst {
  position: absolute; width: 150px; height: 150px; border-radius: 50%;
  border: 1px solid rgba(168, 224, 255, .9); opacity: 0;
  animation: sdf-burst 1.9s cubic-bezier(.15, .75, .3, 1) .44s both; pointer-events: none;
}
@keyframes sdf-burst { 0% { opacity: .95; transform: scale(.32); } 56% { opacity: .32; } 100% { opacity: 0; transform: scale(2.95); } }
.sdf-title {
  font-family: "Songti SC", "STSong", "Noto Serif SC", "SimSun", serif;
  font-size: 44px; letter-spacing: .42em; text-indent: .42em; font-weight: 600;
  color: #f3eeff; margin: 10px 0 0;
  text-shadow: 0 0 26px rgba(160, 110, 255, .6), 0 0 70px rgba(100, 60, 220, .4);
  animation: sdf-title-in 1.5s cubic-bezier(.2,.9,.2,1) .95s both;
}
@keyframes sdf-title-in { from { opacity: 0; letter-spacing: .8em; filter: blur(8px); } to { opacity: 1; letter-spacing: .42em; filter: blur(0); } }
.sdf-subtitle { margin-top: 14px; font-size: 10.5px; letter-spacing: .5em; text-indent: .5em; color: #9c8fd0; animation: sdf-fade 1.6s ease 1.3s both; }
.sdf-rule { width: 240px; height: 1px; margin-top: 22px; background: linear-gradient(90deg, transparent, rgba(180, 140, 255, .55), transparent); animation: sdf-fade 1.4s ease 1.2s both; }
.sdf-bar { width: 240px; height: 2px; margin-top: 20px; background: rgba(120, 96, 210, .18); border-radius: 2px; overflow: hidden; animation: sdf-fade 1s ease 1.3s both; }
.sdf-bar > i { display: block; height: 100%; width: 0; border-radius: 2px; background: linear-gradient(90deg, #6c3ce0, #b285ff 70%, #e9cf94); box-shadow: 0 0 14px rgba(160, 110, 255, .8); animation: sdf-bar-fill 2.4s cubic-bezier(.35,.05,.25,1) 1.4s forwards; }
@keyframes sdf-bar-fill { to { width: 100%; } }
.sdf-boot-line { margin-top: 12px; font-size: 10.5px; letter-spacing: .3em; color: #7c74a8; height: 14px; animation: sdf-fade 1s ease 1.7s both; }
@keyframes sdf-fade { from { opacity: 0; } to { opacity: 1; } }
.sdf-skip { position: fixed; right: 26px; bottom: 22px; font-size: 10.5px; letter-spacing: .26em; color: #6d6694; }
.sdf-corner { position: fixed; left: 26px; bottom: 22px; font-size: 10px; letter-spacing: .32em; color: #5c5680; }
@media (max-width: 480px) {
  .sdf-splash-art-wrap { width: 236px; height: 236px; }
  .sdf-splash-figure { width: 168px; height: 218px; }
  .sdf-title { font-size: 34px; }
  .sdf-root { --sdf-w: min(280px, 58vw); }
  .sdf-fairy { width: var(--sdf-w); height: var(--sdf-h); }
  .sdf-panel { right: 10px; left: 10px; width: auto; top: 12px; bottom: auto; height: min(420px, calc(100vh - var(--sdf-h) - 24px)); }
}

/* ── v3: real artwork from the 4K wallpaper ---- */
.sdf-splash { background: #05060f; }
.sdf-splash-inner { display: block; transform: none; }
.sdf-art {
  position: fixed; inset: -7%; z-index: 0; width: auto; height: auto;
  object-fit: cover; object-position: center 44%; display: block; background: #05060f;
  animation: sdf-ken 36s ease-in-out infinite alternate, sdf-art-in 2.6s cubic-bezier(.16, .84, .24, 1) both;
  will-change: transform;
}
@keyframes sdf-art-in {
  0% { opacity: 0; transform: scale(1.2) translateY(8%); filter: blur(14px) saturate(.75); }
  100% { opacity: .97; transform: scale(1.045) translateY(0); filter: blur(0) saturate(1.05); }
}
@keyframes sdf-ken { from { transform: scale(1.045) translate3d(0, 0, 0); } to { transform: scale(1.12) translate3d(-1.2%, -1.5%, 0); } }
.sdf-veil {
  position: fixed; inset: 0; z-index: 1; pointer-events: none;
  background:
    radial-gradient(122% 88% at 52% 40%, rgba(6, 8, 22, 0) 32%, rgba(5, 7, 20, .58) 72%, rgba(3, 4, 12, .96) 100%),
    linear-gradient(180deg, rgba(6, 8, 24, .74) 0%, rgba(6, 8, 24, 0) 24%, rgba(5, 7, 20, 0) 54%, rgba(4, 5, 16, .93) 100%);
}
.sdf-ringwrap { position: fixed; left: 50%; top: 42%; width: 640px; height: 640px; z-index: 2; transform: translate(-50%, -50%); opacity: .45; mix-blend-mode: screen; pointer-events: none; }
.sdf-ringwrap .sdf-splash-ring { position: absolute; inset: 0; width: 100%; height: 100%; }
.sdf-ringwrap .sdf-splash-glow { display: none; }
.sdf-copy {
  position: fixed; left: 0; right: 0; bottom: 10.5%; z-index: 4; width: 100%;
  display: flex; flex-direction: column; align-items: center; text-align: center; pointer-events: none;
}
.sdf-copy > div { white-space: nowrap; }
.sdf-copy::before {
  content: ''; position: absolute; left: -10%; right: -10%; bottom: -18%; height: 260px; z-index: -1;
  background: radial-gradient(58% 100% at 50% 100%, rgba(4, 5, 16, .94) 0%, rgba(4, 5, 16, .55) 52%, rgba(4, 5, 16, 0) 78%);
  pointer-events: none;
}
.sdf-copy .sdf-title { text-shadow: 0 2px 18px rgba(4, 5, 16, .95), 0 0 60px rgba(4, 5, 16, .85), 0 0 22px rgba(150, 110, 240, .55); }
.sdf-copy .sdf-subtitle, .sdf-copy .sdf-boot-line { text-shadow: 0 1px 12px rgba(4, 5, 16, .95), 0 0 24px rgba(4, 5, 16, .8); }
.sdf-copy .sdf-title { font-size: 47px; }
.sdf-splash .sdf-splash-scan { z-index: 3; }
.sdf-fairy { display: flex; align-items: flex-end; justify-content: center;
  width: var(--sdf-w); height: var(--sdf-h); }
@keyframes sdf-ring-spin { to { transform: rotate(360deg); } }
.sdf-speaking .sdf-speaking @keyframes sdf-pulse {
  0% { box-shadow: 0 0 0 0 rgba(170, 120, 255, .5); }
  70% { box-shadow: 0 0 0 18px rgba(170, 120, 255, 0); }
  100% { box-shadow: 0 0 0 0 rgba(170, 120, 255, 0); }
}
.sdf-fairy .sdf-bob, .sdf-fairy .sdf-fairy-burst { display: none; }

/* ── cinematic re-telling of the wallpaper, then her portrait ── */
.sdf-cinebox { position: fixed; inset: 0; overflow: hidden; z-index: 0; background: #05060f; }
.sdf-art {
  position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: cover; object-position: center 46%; display: block;
  animation: sdf-cine 6.2s cubic-bezier(.45, .02, .25, 1) both;
  will-change: transform, filter;
}
@keyframes sdf-cine {
  0%   { transform: scale(2.62) translate(-29%, 9%); filter: blur(10px) saturate(.85); opacity: 0; }
  7%   { opacity: 1; filter: blur(0) saturate(1.02); }
  30%  { transform: scale(2.28) translate(-25%, 3%); }
  46%  { transform: scale(1.88) translate(-3%, 4%); }
  63%  { transform: scale(1.16) translate(0, 0); }
  79%  { transform: scale(1.045) translate(0, 0); }
  100% { transform: scale(1.08) translate(0, -1.2%); }
}
.sdf-reveal {
  position: fixed; inset: 0; z-index: 3; display: flex; align-items: center; justify-content: center;
  pointer-events: none; opacity: 0;
  animation: sdf-reveal-in 1.5s cubic-bezier(.2, .9, .22, 1) 4.3s both;
}
@keyframes sdf-reveal-in { from { opacity: 0; } to { opacity: 1; } }
.sdf-reveal-glow {
  position: absolute; width: 1180px; height: 1180px; border-radius: 50%;
  background: radial-gradient(50% 50% at 50% 50%, rgba(7, 5, 20, .92) 0%, rgba(9, 7, 24, .72) 38%, rgba(9, 7, 24, .3) 64%, rgba(9, 7, 24, 0) 78%);
  animation: sdf-reveal-in 1.4s ease 4.25s both;
}
.sdf-reveal-figure {
  position: relative; height: min(680px, 68vh); width: auto; max-width: 88vw; object-fit: contain;
  transform: translate(0, -7vh);
  filter: drop-shadow(0 18px 40px rgba(3, 4, 14, .7)) drop-shadow(0 0 46px rgba(126, 88, 232, .5));
  animation: sdf-reveal-card 1.7s cubic-bezier(.2, .9, .2, 1) 4.3s both;
}
.sdf-reveal-card {
  position: relative; width: 268px; height: 348px; border-radius: 20px; overflow: hidden;
  border: 1px solid rgba(232, 206, 152, .55); background: #0a0d1f;
  box-shadow: 0 0 0 1px rgba(130, 86, 226, .35), 0 0 60px rgba(122, 74, 226, .55), 0 26px 60px rgba(0, 0, 0, .6);
  animation: sdf-reveal-card 1.7s cubic-bezier(.2, .9, .2, 1) 4.3s both;
}
@keyframes sdf-reveal-card {
  0% { opacity: 0; transform: scale(.74) translateY(26px); filter: blur(14px); }
  62% { opacity: 1; transform: scale(1.035) translateY(-4px); filter: blur(0); }
  100% { opacity: 1; transform: scale(1) translateY(0); filter: blur(0); }
}
.sdf-reveal-img { width: 100%; height: 100%; object-fit: cover; object-position: 50% 8%; display: block; }
.sdf-reveal-card::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background:
    radial-gradient(118% 92% at 50% 22%, rgba(126, 96, 226, .1) 0%, rgba(10, 10, 30, .38) 62%, rgba(6, 7, 20, .78) 100%),
    linear-gradient(180deg, rgba(6, 8, 22, 0) 46%, rgba(6, 8, 22, .52) 100%);
  box-shadow: inset 0 0 0 1px rgba(168, 138, 255, .18);
}
.sdf-reveal-card::before {
  content: ''; position: absolute; inset: -14px; z-index: -1; border-radius: 26px;
  background: radial-gradient(60% 60% at 50% 50%, rgba(126, 88, 232, .38), rgba(126, 88, 232, 0) 72%);
  filter: blur(12px);
}
.sdf-reveal-burst {
  position: absolute; width: 300px; height: 300px; border-radius: 50%;
  border: 1px solid rgba(206, 176, 255, .5);
  animation: sdf-burst 2.1s cubic-bezier(.15, .7, .3, 1) 4.35s both;
}
.sdf-splash .sdf-copy { bottom: 2.4%; }
.sdf-splash .sdf-copy .sdf-title { font-size: clamp(24px, 4.2vw, 34px); }

/* ── the framed living portrait (from the character card) ── */
.sdf-card-img {
  display: block; height: 100%; width: 100%; object-fit: contain; object-position: center bottom;
  filter: drop-shadow(0 6px 14px rgba(4, 6, 18, .55)) drop-shadow(0 0 18px rgba(122, 84, 226, .35));
  animation: sdf-card-ken 26s ease-in-out infinite alternate;
}
@keyframes sdf-card-ken {
  0%   { transform: scale(1) translateY(0); }
  100% { transform: scale(1.035) translateY(-4px); }
}
.sdf-card-pulse { position: absolute; inset: 12% 8% 10% 8%; border-radius: 50%; pointer-events: none; }
.sdf-speaking .sdf-card-pulse { animation: sdf-pulse 1.5s ease-out infinite; }
.sdf-card::before {
  content: ''; position: absolute; inset: 0; z-index: 1; pointer-events: none;
  background: radial-gradient(120% 90% at 50% 0%, rgba(255, 255, 255, .1), rgba(6, 8, 22, 0) 42%),
              linear-gradient(180deg, rgba(6, 8, 22, 0) 58%, rgba(6, 8, 22, .55) 100%);
}

.sdf-fairy-mote { position: absolute; inset: -4px; border-radius: 50%; pointer-events: none; }

/* ── workshop 皮肤：黑金面板（aurora 走上面的深蓝紫） ── */
.sdf-root.sdf-skin-workshop .sdf-ambient {
  background:
    radial-gradient(58% 46% at 8% -6%, rgba(199, 168, 110, .12), rgba(199, 168, 110, 0) 68%),
    radial-gradient(46% 42% at 96% 2%, rgba(169, 203, 213, .08), rgba(169, 203, 213, 0) 70%),
    radial-gradient(64% 52% at 52% 112%, rgba(199, 168, 110, .09), rgba(199, 168, 110, 0) 70%);
  opacity: .75;
}
.sdf-root.sdf-skin-workshop .sdf-whisper {
  background: linear-gradient(150deg, rgba(13, 17, 23, .98), rgba(6, 9, 13, .98)) !important;
  border-color: rgba(199, 168, 110, .34) !important;
  color: #ebe3d1 !important;
}
.sdf-root.sdf-skin-workshop .sdf-panel {
  background:
    radial-gradient(120% 80% at 100% 0%, rgba(199, 168, 110, .10), transparent 62%),
    radial-gradient(90% 60% at 0% 100%, rgba(169, 203, 213, .06), transparent 70%),
    linear-gradient(165deg, rgba(14, 18, 24, .985), rgba(6, 9, 13, .99)) !important;
  border-color: rgba(199, 168, 110, .30) !important;
  box-shadow: 0 28px 70px rgba(0, 0, 0, .62), inset 0 1px 0 rgba(235, 227, 209, .10) !important;
  color: #ebe3d1 !important;
}
.sdf-root.sdf-skin-workshop .sdf-panel::before { background: repeating-linear-gradient(115deg, rgba(235, 227, 209, .02) 0 1px, transparent 1px 9px); }
.sdf-root.sdf-skin-workshop .sdf-head {
  border-bottom-color: rgba(199, 168, 110, .18) !important;
  background: linear-gradient(180deg, rgba(199, 168, 110, .08), rgba(12, 14, 18, 0)) !important;
}
.sdf-root.sdf-skin-workshop .sdf-mark {
  background: radial-gradient(circle at 34% 30%, #3a2f1e, #0b0d0f 72%) !important;
  border-color: rgba(199, 168, 110, .45) !important;
}
.sdf-root.sdf-skin-workshop .sdf-name { color: #f0e6d2 !important; }
.sdf-root.sdf-skin-workshop .sdf-sub { color: rgba(199, 168, 110, .70) !important; }
.sdf-root.sdf-skin-workshop .sdf-icon-btn {
  border-color: rgba(199, 168, 110, .22) !important;
  background: rgba(199, 168, 110, .04) !important;
  color: #c7a86e !important;
}
.sdf-root.sdf-skin-workshop .sdf-icon-btn:hover {
  color: #f0e6d2 !important;
  border-color: rgba(199, 168, 110, .55) !important;
  background: rgba(199, 168, 110, .12) !important;
}
.sdf-root.sdf-skin-workshop .sdf-icon-btn.sdf-on {
  color: #f0e6d2 !important;
  border-color: rgba(199, 168, 110, .65) !important;
  background: rgba(199, 168, 110, .16) !important;
  box-shadow: 0 0 14px rgba(199, 168, 110, .18) !important;
}
.sdf-root.sdf-skin-workshop .sdf-log::-webkit-scrollbar-thumb { background: rgba(199, 168, 110, .35) !important; }
.sdf-root.sdf-skin-workshop .sdf-bubble {
  background: linear-gradient(160deg, rgba(24, 28, 34, .90), rgba(10, 13, 18, .92)) !important;
  border-color: rgba(199, 168, 110, .18) !important;
  color: #ebe3d1 !important;
}
.sdf-root.sdf-skin-workshop .sdf-row.sdf-me .sdf-bubble {
  background: linear-gradient(160deg, rgba(199, 168, 110, .12), rgba(24, 22, 18, .90)) !important;
  border-color: rgba(199, 168, 110, .34) !important;
  color: #f0e6d2 !important;
}
.sdf-root.sdf-skin-workshop .sdf-bubble.sdf-err {
  border-color: rgba(153, 62, 80, .50) !important;
  color: #f2c4ce !important;
  background: rgba(60, 16, 26, .50) !important;
}
.sdf-root.sdf-skin-workshop .sdf-tag { color: #8f887a !important; }
.sdf-root.sdf-skin-workshop .sdf-caret { background: #c7a86e !important; }
.sdf-root.sdf-skin-workshop .sdf-empty { color: #8f887a !important; }
.sdf-root.sdf-skin-workshop .sdf-chip {
  color: #d9bd86 !important;
  border-color: rgba(199, 168, 110, .28) !important;
  background: rgba(199, 168, 110, .06) !important;
}
.sdf-root.sdf-skin-workshop .sdf-chip:hover {
  color: #f0e6d2 !important;
  border-color: rgba(199, 168, 110, .60) !important;
  background: rgba(199, 168, 110, .14) !important;
}
.sdf-root.sdf-skin-workshop .sdf-compose {
  border-top-color: rgba(199, 168, 110, .16) !important;
  background: linear-gradient(0deg, rgba(10, 13, 18, .75), transparent) !important;
}
.sdf-root.sdf-skin-workshop .sdf-input-wrap {
  border-color: rgba(199, 168, 110, .22) !important;
  background: rgba(6, 9, 13, .75) !important;
}
.sdf-root.sdf-skin-workshop .sdf-input-wrap:focus-within {
  border-color: rgba(199, 168, 110, .58) !important;
  box-shadow: 0 0 0 3px rgba(199, 168, 110, .12) !important;
}
.sdf-root.sdf-skin-workshop .sdf-input { color: #ebe3d1 !important; }
.sdf-root.sdf-skin-workshop .sdf-input::placeholder { color: #6f6a5f !important; }
.sdf-root.sdf-skin-workshop .sdf-send {
  background: linear-gradient(160deg, rgba(199, 168, 110, .50), rgba(74, 56, 32, .55)) !important;
  color: #0b0d0f !important;
}
.sdf-root.sdf-skin-workshop .sdf-send:hover:not(:disabled) { box-shadow: 0 8px 20px rgba(199, 168, 110, .25) !important; }
.sdf-root.sdf-skin-workshop .sdf-link { color: #8f887a !important; }
.sdf-root.sdf-skin-workshop .sdf-dot { background: #6e6a5f !important; }
.sdf-root.sdf-skin-workshop .sdf-link.sdf-ok .sdf-dot { background: #c7a86e !important; box-shadow: 0 0 8px rgba(199, 168, 110, .8) !important; }
.sdf-root.sdf-skin-workshop .sdf-link.sdf-bad .sdf-dot { background: #993e50 !important; box-shadow: 0 0 8px rgba(153, 62, 80, .8) !important; }
.sdf-root.sdf-skin-workshop .sdf-voice-tag {
  color: #c7a86e !important;
  border-color: rgba(199, 168, 110, .28) !important;
  background: rgba(199, 168, 110, .06) !important;
}
.sdf-root.sdf-skin-workshop .sdf-voice-tag:hover { color: #f0e6d2 !important; background: rgba(199, 168, 110, .14) !important; }
.sdf-root.sdf-skin-workshop .sdf-voice-tag.is-clone { color: #a9cbd5 !important; }
.sdf-root.sdf-skin-workshop .sdf-text-btn { color: #8f887a !important; }
.sdf-root.sdf-skin-workshop .sdf-text-btn:hover { color: #f0e6d2 !important; background: rgba(199, 168, 110, .10) !important; }
.sdf-root.sdf-skin-workshop .sdf-fairy:hover { filter: drop-shadow(0 20px 44px rgba(199, 168, 110, .35)) !important; }
.sdf-root.sdf-skin-workshop .sdf-fairy:focus-visible { outline-color: rgba(199, 168, 110, .75) !important; }
.sdf-root.sdf-skin-workshop .sdf-card-img { filter: drop-shadow(0 6px 14px rgba(4, 6, 18, .55)) drop-shadow(0 0 18px rgba(199, 168, 110, .25)) !important; }
.sdf-root.sdf-skin-workshop .sdf-corner { color: #6f6a5f !important; }
`

    /* ──────────────────────────── art ──────────────────────────── */

    const GEAR_TEETH = 8

    function gear(cx, cy, radius, tooth, fill, key) {
      const teeth = []
      for (let i = 0; i < GEAR_TEETH; i += 1) {
        teeth.push(h('rect', {
          key: 't' + i,
          x: -tooth * 0.42,
          y: -radius - tooth * 0.62,
          width: tooth * 0.84,
          height: tooth * 0.8,
          rx: tooth * 0.26,
          fill,
          transform: `rotate(${(360 / GEAR_TEETH) * i})`,
        }))
      }
      return h('g', { key, transform: `translate(${cx},${cy})` },
        h('circle', { r: radius, fill }),
        h('circle', { r: radius * 0.62, fill: 'rgba(10,12,36,.92)' }),
        teeth)
    }

    function SandroneArt(props) {
      const speaking = !!(props && props.speaking)
      const detailed = !!(props && props.detailed)

      const teeth = (cx, cy, radius, count, width, height, fill, key) => {
        const items = []
        for (let i = 0; i < count; i += 1) {
          items.push(h('rect', {
            key: key + '-' + i,
            x: -width / 2,
            y: -radius - height / 2,
            width,
            height,
            rx: height * 0.12,
            fill,
            transform: `rotate(${(360 / count) * i})`,
          }))
        }
        return items
      }

      return h('svg', {
        className: 'sdf-art',
        viewBox: '0 0 200 260',
        xmlns: 'http://www.w3.org/2000/svg',
        'aria-hidden': 'true',
      },
        h('defs', null,
          h('linearGradient', { id: 'sd-hair', x1: '0', y1: '0', x2: '0.3', y2: '1' },
            h('stop', { offset: '0', stopColor: '#ab8a6a' }),
            h('stop', { offset: '.45', stopColor: '#86664f' }),
            h('stop', { offset: '1', stopColor: '#563c2e' })),
          h('linearGradient', { id: 'sd-hair-hi', x1: '0', y1: '0', x2: '0', y2: '1' },
            h('stop', { offset: '0', stopColor: '#dcc0a0' }),
            h('stop', { offset: '1', stopColor: '#a9885f' })),
          h('linearGradient', { id: 'sd-skin', x1: '0', y1: '0', x2: '0', y2: '1' },
            h('stop', { offset: '0', stopColor: '#fdf3ec' }),
            h('stop', { offset: '1', stopColor: '#f2dbd1' })),
          h('linearGradient', { id: 'sd-white', x1: '0', y1: '0', x2: '0', y2: '1' },
            h('stop', { offset: '0', stopColor: '#ffffff' }),
            h('stop', { offset: '.62', stopColor: '#efeaf7' }),
            h('stop', { offset: '1', stopColor: '#cbc2dd' })),
          h('linearGradient', { id: 'sd-black', x1: '0', y1: '0', x2: '0.4', y2: '1' },
            h('stop', { offset: '0', stopColor: '#2b2440' }),
            h('stop', { offset: '1', stopColor: '#0e0b1a' })),
          h('linearGradient', { id: 'sd-red', x1: '0', y1: '0', x2: '0.4', y2: '1' },
            h('stop', { offset: '0', stopColor: '#d23a52' }),
            h('stop', { offset: '1', stopColor: '#8a172c' })),
          h('linearGradient', { id: 'sd-gold', x1: '0', y1: '0', x2: '1', y2: '1' },
            h('stop', { offset: '0', stopColor: '#f7e6b6' }),
            h('stop', { offset: '.5', stopColor: '#d8b271' }),
            h('stop', { offset: '1', stopColor: '#a37a34' })),
          h('linearGradient', { id: 'sd-eye', x1: '0', y1: '0', x2: '0', y2: '1' },
            h('stop', { offset: '0', stopColor: '#b9c4ff' }),
            h('stop', { offset: '.38', stopColor: '#7181e0' }),
            h('stop', { offset: '.78', stopColor: '#3d47b4' }),
            h('stop', { offset: '1', stopColor: '#211f63' })),
          h('linearGradient', { id: 'sd-gem', x1: '0', y1: '0', x2: '0', y2: '1' },
            h('stop', { offset: '0', stopColor: '#cdf6ff' }),
            h('stop', { offset: '1', stopColor: '#2f86bd' })),
          h('radialGradient', { id: 'sd-glow', cx: '50%', cy: '50%', r: '50%' },
            h('stop', { offset: '0', stopColor: '#7b6cff', stopOpacity: '.55' }),
            h('stop', { offset: '.55', stopColor: '#5a3fd0', stopOpacity: '.22' }),
            h('stop', { offset: '1', stopColor: '#3a2a90', stopOpacity: '0' }))),

        /* ambient glow */
        h('ellipse', { cx: '100', cy: '150', rx: '94', ry: '98', fill: 'url(#sd-glow)' }),

        /* mechanical halo behind her back */
        h('g', { className: 'sdf-gear-a', opacity: '.95' },
          h('g', { transform: 'translate(100 144)' },
            teeth(0, 0, 75, 10, 10, 13, 'url(#sd-gold)', 'halo'),
            h('circle', { r: '72', fill: 'none', stroke: 'url(#sd-gold)', strokeWidth: '2.2', opacity: '.8' }),
            h('circle', { r: '65', fill: 'none', stroke: 'rgba(250, 232, 186, .5)', strokeWidth: '.8' }),
            h('circle', { r: '55', fill: 'none', stroke: 'rgba(150, 120, 220, .5)', strokeWidth: '.9', strokeDasharray: '18 10' }),
            h('circle', { r: '43', fill: 'none', stroke: 'rgba(210, 190, 255, .32)', strokeWidth: '.7', strokeDasharray: '1 7' }),
            h('path', { d: 'M0 -65 L0 -55 M0 65 L0 55 M-65 0 L-55 0 M65 0 L55 0', stroke: 'url(#sd-gold)', strokeWidth: '1', opacity: '.5' }))),
        detailed
          ? h('g', { className: 'sdf-gear-b', opacity: '.55' },
            h('g', { transform: 'translate(44 196)' },
              teeth(0, 0, 20, 8, 6, 7, 'rgba(196, 168, 240, .8)', 'gear-l'),
              h('circle', { r: '18', fill: 'none', stroke: 'rgba(196, 168, 240, .8)', strokeWidth: '1.6' })))
          : null,

        /* hair: back mass */
        h('g', { className: 'sdf-hair-tail' },
          h('path', {
            d: 'M100 30 C 74 30 66 52 68 76 C 69 96 64 120 60 138 C 58 148 62 152 68 150 C 74 148 78 140 80 128 C 82 116 84 104 84 92 L 116 92 C 116 104 118 116 120 128 C 122 140 126 148 132 150 C 138 152 142 148 140 138 C 136 120 131 96 132 76 C 134 52 126 30 100 30 Z',
            fill: 'url(#sd-hair)',
          }),
          /* two long side tails with a curl */
          h('path', {
            d: 'M70 92 C 62 112 56 136 54 156 C 52 168 46 174 42 170 C 38 166 42 158 46 150 C 50 138 52 120 54 104 Z',
            fill: 'url(#sd-hair)',
          }),
          h('path', {
            d: 'M130 92 C 138 112 144 136 146 156 C 148 168 154 174 158 170 C 162 166 158 158 154 150 C 150 138 148 120 146 104 Z',
            fill: 'url(#sd-hair)',
          }),
          h('path', {
            d: 'M76 44 C 84 38 94 36 100 36 C 106 36 116 38 124 44',
            fill: 'none', stroke: 'url(#sd-hair-hi)', strokeWidth: '1.6', strokeLinecap: 'round', opacity: '.8',
          })),

        /* legs + shoes (she sits in the air) */
        h('g', null,
          h('path', { d: 'M87 206 C 85 220 85 232 86 240 L 97 240 C 97 232 97 220 98 206 Z', fill: 'url(#sd-white)', stroke: 'rgba(180, 168, 205, .55)', strokeWidth: '.5' }),
          h('path', { d: 'M102 206 C 103 220 103 232 103 240 L 114 240 C 115 232 115 220 113 206 Z', fill: 'url(#sd-white)', stroke: 'rgba(180, 168, 205, .55)', strokeWidth: '.5' }),
          h('path', { d: 'M85.5 219 C 89 221.5 95 221.5 97.5 219 M102.5 219 C 105 221.5 111 221.5 114.5 219', stroke: 'rgba(170, 156, 200, .45)', strokeWidth: '.7', fill: 'none' }),
          h('ellipse', { cx: '89.5', cy: '245', rx: '8.6', ry: '4.4', fill: 'url(#sd-black)' }),
          h('ellipse', { cx: '110.5', cy: '245', rx: '8.6', ry: '4.4', fill: 'url(#sd-black)' }),
          h('ellipse', { cx: '93', cy: '242.6', rx: '2.6', ry: '1.6', fill: 'rgba(255,255,255,.22)' }),
          h('ellipse', { cx: '107', cy: '242.6', rx: '2.6', ry: '1.6', fill: 'rgba(255,255,255,.22)' })),

        /* skirt: white apron over red underskirt */
        h('path', {
          d: 'M62 196 C 58 206 56 214 56 220 L 144 220 C 144 214 142 206 138 196 Z',
          fill: 'url(#sd-red)',
        }),
        h('path', {
          d: 'M78 150 C 66 168 60 186 58 204 C 58 208 60 210 64 210 L 136 210 C 140 210 142 208 142 204 C 140 186 134 168 122 150 Z',
          fill: 'url(#sd-white)',
        }),
        h('path', {
          d: 'M100 156 L100 210 M88 158 L84 210 M112 158 L116 210',
          stroke: 'rgba(186, 174, 212, .6)', strokeWidth: '.7',
        }),
        h('path', {
          d: 'M64 206 L136 206',
          stroke: 'rgba(170, 156, 200, .7)', strokeWidth: '1',
        }),

        /* torso: white chemise, black corset */
        h('path', {
          d: 'M84 106 C 90 100 110 100 116 106 L 114 118 L 86 118 Z',
          fill: 'url(#sd-white)',
        }),
        h('path', {
          d: 'M82 112 C 86 108 114 108 118 112 C 120 130 117 144 112 154 L 88 154 C 83 144 80 130 82 112 Z',
          fill: 'url(#sd-black)',
        }),
        h('path', {
          d: 'M94 118 C 98 122 102 122 106 118',
          fill: 'none', stroke: 'rgba(212, 190, 255, .55)', strokeWidth: '.8',
        }),
        h('path', {
          d: 'M100 122 L100 150',
          stroke: 'rgba(212, 190, 255, .45)', strokeWidth: '.8',
        }),
        h('g', { fill: 'url(#sd-gold)', opacity: '.9' },
          h('circle', { cx: '100', cy: '128', r: '1.1' }),
          h('circle', { cx: '100', cy: '136', r: '1.1' }),
          h('circle', { cx: '100', cy: '144', r: '1.1' })),
        /* red waist bow */
        h('path', { d: 'M100 108.5 C 96.5 105 91.5 106 91.5 109 C 92.2 112.5 97.5 111.5 100 109.5 Z', fill: 'url(#sd-red)' }),
        h('path', { d: 'M100 108.5 C 103.5 105 108.5 106 108.5 109 C 107.8 112.5 102.5 111.5 100 109.5 Z', fill: 'url(#sd-red)' }),
        h('circle', { cx: '100', cy: '109.4', r: '1.3', fill: '#e0566d' }),

        /* arms: right hand lifts a teacup */
        h('ellipse', { cx: '77', cy: '112', rx: '9', ry: '8.5', fill: 'url(#sd-white)', transform: 'rotate(-12 77 112)' }),
        h('ellipse', { cx: '123', cy: '112', rx: '9', ry: '8.5', fill: 'url(#sd-white)', transform: 'rotate(12 123 112)' }),
        h('path', {
          d: 'M71 117 C 67 127 65 137 66 146',
          stroke: 'url(#sd-white)', strokeWidth: '5.8', strokeLinecap: 'round', fill: 'none',
        }),
        h('path', {
          d: 'M129 117 C 133 124 136 130 136 136',
          stroke: 'url(#sd-white)', strokeWidth: '5.8', strokeLinecap: 'round', fill: 'none',
        }),
        h('path', {
          d: 'M71 117 C 67 127 65 137 66 146',
          stroke: 'rgba(176, 164, 204, .5)', strokeWidth: '.5', fill: 'none',
        }),
        h('path', {
          d: 'M129 117 C 133 124 136 130 136 136',
          stroke: 'rgba(176, 164, 204, .5)', strokeWidth: '.5', fill: 'none',
        }),
        h('ellipse', { cx: '66', cy: '149', rx: '4.9', ry: '5.9', fill: 'url(#sd-white)', stroke: 'rgba(176, 164, 204, .45)', strokeWidth: '.5' }),
        h('ellipse', { cx: '136', cy: '140', rx: '4.7', ry: '5.5', fill: 'url(#sd-white)', stroke: 'rgba(176, 164, 204, .45)', strokeWidth: '.5' }),
        /* teacup */
        h('g', { className: 'sdf-cup' },
          h('path', {
            d: 'M130 128 C 138 128 142 131 142 135 C 142 139 138 141 130 141 Z',
            fill: 'url(#sd-white)', stroke: 'url(#sd-gold)', strokeWidth: '.8',
          }),
          h('ellipse', { cx: '136', cy: '128', rx: '6.4', ry: '2', fill: 'url(#sd-gold)', opacity: '.9' }),
          h('ellipse', { cx: '136', cy: '128.4', rx: '5.2', ry: '1.4', fill: '#a8542f', opacity: '.85' }),
          h('path', {
            d: 'M142 131 C 145.6 131 146.4 135.4 142 136',
            fill: 'none', stroke: 'url(#sd-gold)', strokeWidth: '.9',
          }),
          h('path', {
            d: 'M133 126 C 132 122 134 120 133 117',
            stroke: 'rgba(235, 225, 255, .5)', strokeWidth: '.9', fill: 'none',
          })),

        /* neck + head */
        h('rect', { x: '95.5', y: '92', width: '9', height: '12', rx: '4.2', fill: 'url(#sd-skin)' }),
        h('ellipse', { cx: '100', cy: '64', rx: '25', ry: '26.5', fill: 'url(#sd-skin)' }),
        h('ellipse', { cx: '100', cy: '70', rx: '24', ry: '20', fill: 'rgba(240, 214, 205, .35)' }),

        /* fringe */
        h('path', {
          d: 'M75 62 C 74 38 86 28 100 28 C 114 28 126 38 125 62 C 122 48 114 42 106 44 C 102 45 98 47 94 44 C 86 40 78 46 75 62 Z',
          fill: 'url(#sd-hair)',
        }),
        h('path', {
          d: 'M96 30 C 98 40 96 48 92 54',
          stroke: 'rgba(220, 192, 160, .55)', strokeWidth: '1.2', fill: 'none', strokeLinecap: 'round',
        }),

        /* brows + eyes */
        h('path', { d: 'M83 58 Q 88.5 55.4 94 57.6', stroke: '#7a5c47', strokeWidth: '1.1', fill: 'none', strokeLinecap: 'round', opacity: '.8' }),
        h('path', { d: 'M106 57.6 Q 111.5 55.4 117 58', stroke: '#7a5c47', strokeWidth: '1.1', fill: 'none', strokeLinecap: 'round', opacity: '.8' }),
        h('g', { className: 'sdf-blink' },
          h('ellipse', { cx: '88.5', cy: '67', rx: '4.8', ry: '6.2', fill: 'url(#sd-eye)' }),
          h('ellipse', { cx: '111.5', cy: '67', rx: '4.8', ry: '6.2', fill: 'url(#sd-eye)' }),
          h('ellipse', { cx: '88.5', cy: '68.4', rx: '2.1', ry: '3', fill: '#1b1c4d' }),
          h('ellipse', { cx: '111.5', cy: '68.4', rx: '2.1', ry: '3', fill: '#1b1c4d' }),
          h('ellipse', { cx: '86.9', cy: '64.4', rx: '1.5', ry: '1.9', fill: '#ffffff', opacity: '.95' }),
          h('ellipse', { cx: '109.9', cy: '64.4', rx: '1.5', ry: '1.9', fill: '#ffffff', opacity: '.95' }),
          h('ellipse', { cx: '90', cy: '70.4', rx: '.9', ry: '1.1', fill: 'rgba(210, 220, 255, .8)' }),
          h('ellipse', { cx: '113', cy: '70.4', rx: '.9', ry: '1.1', fill: 'rgba(210, 220, 255, .8)' }),
          h('path', { d: 'M83 61.6 Q 88.5 58.4 94 61.4', stroke: '#3a2a3c', strokeWidth: '1.5', fill: 'none', strokeLinecap: 'round' }),
          h('path', { d: 'M106 61.4 Q 111.5 58.4 117 61.6', stroke: '#3a2a3c', strokeWidth: '1.5', fill: 'none', strokeLinecap: 'round' })),
        h('ellipse', { cx: '80', cy: '75', rx: '4.4', ry: '2.4', fill: 'rgba(238, 152, 160, .45)' }),
        h('ellipse', { cx: '120', cy: '75', rx: '4.4', ry: '2.4', fill: 'rgba(238, 152, 160, .45)' }),
        speaking
          ? h('ellipse', { className: 'sdf-mouth', cx: '100', cy: '80.5', rx: '2.4', ry: '1.8', fill: '#a2495a' })
          : h('path', { d: 'M97.4 80.2 Q 100 82.2 102.6 80.2', stroke: '#b7657a', strokeWidth: '1.1', fill: 'none', strokeLinecap: 'round' }),

        /* white-and-gold headdress with two flaps + red ribbon */
        h('path', {
          d: 'M74 44 C 78 30 92 24 100 24 C 108 24 122 30 126 44 C 118 40 110 38 100 38 C 90 38 82 40 74 44 Z',
          fill: 'url(#sd-white)',
        }),
        h('path', {
          d: 'M74 44 C 78 30 92 24 100 24 C 108 24 122 30 126 44',
          fill: 'none', stroke: 'url(#sd-gold)', strokeWidth: '1.5', opacity: '.9',
        }),
        h('path', {
          d: 'M81 45 C 75 34 62 24 52 20 C 44 17 41 22 47 28 C 56 37 68 43 81 46 Z',
          fill: 'url(#sd-white)', stroke: 'url(#sd-gold)', strokeWidth: '1',
        }),
        h('path', {
          d: 'M119 45 C 125 34 138 24 148 20 C 156 17 159 22 153 28 C 144 37 132 43 119 46 Z',
          fill: 'url(#sd-white)', stroke: 'url(#sd-gold)', strokeWidth: '1',
        }),
        h('path', {
          d: 'M60 28 C 67 33 73 38 79 42 M140 28 C 133 33 127 38 121 42',
          fill: 'none', stroke: 'rgba(196, 160, 92, .55)', strokeWidth: '.8',
        }),
        h('g', { fill: 'url(#sd-gold)', opacity: '.85' },
          h('circle', { cx: '84', cy: '34', r: '1.4' }),
          h('circle', { cx: '100', cy: '30.5', r: '1.6' }),
          h('circle', { cx: '116', cy: '34', r: '1.4' })),
        h('g', { className: 'sdf-ribbon' },
          h('path', {
            d: 'M124 44 C 134 42 142 46 146 52 C 141 50 135 50 129 52 Z',
            fill: 'url(#sd-red)',
          }),
          h('path', {
            d: 'M128 48 C 140 56 150 70 152 84 C 148 72 140 62 130 56 Z',
            fill: 'url(#sd-red)',
          }),
          h('path', {
            d: 'M126 50 C 136 62 142 76 143 90 C 141 78 134 66 125 58 Z',
            fill: 'url(#sd-red)', opacity: '.8',
          })),
        h('circle', { cx: '128', cy: '47', r: '2', fill: '#e0566d' }),

        /* sparkles */
        h('g', { fill: '#f4e2b4', opacity: '.85' },
          h('circle', { cx: '48', cy: '86', r: '1.2' }),
          h('circle', { cx: '154', cy: '120', r: '1' }),
          h('circle', { cx: '40', cy: '150', r: '.9' }),
          h('circle', { cx: '160', cy: '176', r: '1.1' })),
        h('g', { fill: '#cdb4ff', opacity: '.6' },
          h('circle', { cx: '56', cy: '118', r: '.8' }),
          h('circle', { cx: '146', cy: '70', r: '.8' }),
          h('circle', { cx: '36', cy: '112', r: '.7' })))
    }

    const SNOW = Array.from({ length: 18 }, (_, i) => {
      const seed = (i * 37 + 11) % 29
      return {
        left: (i * 61 + 7) % 94,
        size: 2 + (seed % 3),
        dur: 9 + (seed % 8),
        delay: -((i * 2.3) % 14),
        drift: (seed % 2 === 0 ? 1 : -1) * (14 + (seed % 22)),
      }
    })

    function SplashStage() {
      return h('div', { className: 'sdf-splash-stage' },
        h('div', { className: 'sdf-splash-glow' }),
        h('svg', { className: 'sdf-splash-ring', viewBox: '0 0 340 340', 'aria-hidden': 'true' },
          h('defs', null,
            h('linearGradient', { id: 'sdf-cyan', x1: '0', y1: '0', x2: '1', y2: '1' },
              h('stop', { offset: '0', stopColor: '#a8ecff' }),
              h('stop', { offset: '.42', stopColor: '#57b2ec' }),
              h('stop', { offset: '1', stopColor: '#2b4aa8' })),
            h('linearGradient', { id: 'sdf-gold-s', x1: '0', y1: '0', x2: '1', y2: '1' },
              h('stop', { offset: '0', stopColor: '#f2dfae' }),
              h('stop', { offset: '1', stopColor: '#8a6428' }))),
          h('g', { className: 'sdf-gear-big' },
            h('circle', { cx: '170', cy: '170', r: '139', fill: 'none', stroke: 'url(#sdf-gold-s)', strokeWidth: '.8', strokeDasharray: '1 12', opacity: '.42' }),
            h('circle', { cx: '170', cy: '170', r: '128', fill: 'none', stroke: 'url(#sdf-cyan)', strokeWidth: '7', strokeDasharray: '16 10', opacity: '.42' }),
            h('circle', { cx: '170', cy: '170', r: '120', fill: 'none', stroke: 'rgba(150, 214, 255, .46)', strokeWidth: '1.5' })),
          h('g', { className: 'sdf-gear-mid' },
            h('circle', { cx: '170', cy: '170', r: '101', fill: 'none', stroke: 'rgba(164, 116, 255, .5)', strokeWidth: '3.4', strokeDasharray: '26 11', opacity: '.6' }),
            h('circle', { cx: '170', cy: '170', r: '93', fill: 'none', stroke: 'rgba(140, 214, 255, .3)', strokeWidth: '.8', strokeDasharray: '2 8' })),
          h('g', { className: 'sdf-gear-hair' },
            h('circle', { cx: '170', cy: '170', r: '72', fill: 'none', stroke: 'rgba(196, 232, 255, .45)', strokeWidth: '.8', strokeDasharray: '30 210', strokeLinecap: 'round' }),
            h('circle', { cx: '170', cy: '170', r: '58', fill: 'none', stroke: 'rgba(180, 140, 255, .42)', strokeWidth: '.7', strokeDasharray: '1 7' })),
          h('g', { className: 'sdf-gear-far' },
            h('circle', { cx: '44', cy: '78', r: '33', fill: 'none', stroke: 'rgba(96, 158, 226, .34)', strokeWidth: '5', strokeDasharray: '11 8' }),
            h('circle', { cx: '44', cy: '78', r: '26', fill: 'none', stroke: 'rgba(96, 158, 226, .22)', strokeWidth: '.8', strokeDasharray: '2 7' })),
          h('g', { className: 'sdf-gear-far-rev' },
            h('circle', { cx: '300', cy: '270', r: '25', fill: 'none', stroke: 'rgba(158, 118, 255, .3)', strokeWidth: '4', strokeDasharray: '9 7' }),
            h('circle', { cx: '300', cy: '270', r: '18', fill: 'none', stroke: 'rgba(158, 118, 255, .22)', strokeWidth: '.7', strokeDasharray: '1 6' }))),
        h('div', { className: 'sdf-burst' }),
        h('div', { className: 'sdf-snow' },
          SNOW.map((flake, index) => h('i', {
            key: 'flake' + index,
            style: {
              left: flake.left + '%',
              width: flake.size + 'px',
              height: flake.size + 'px',
              animationDuration: flake.dur + 's',
              animationDelay: flake.delay + 's',
              '--sdf-drift': flake.drift + 'px',
            },
          }))))
    }

    /* ──────────────────────────── speech ──────────────────────────── */

    const SPEAKER = {
      enabled: true,
      queue: [],
      speaking: false,
      listeners: new Set(),
      voice: null,
      neural: 'zh-CN-XiaoxiaoNeural',
      neuralOk: false,
      audio: null,
      engine: (() => {
        try {
          const saved = window.localStorage.getItem('sandrone-fairy:engine')
          return saved === 'clone' || saved === 'neural' || saved === 'auto' ? saved : 'auto'
        } catch (error) {
          return 'auto'
        }
      })(),
      playingQueue: false,
      streamOn: true,          // false 时退回「整句合成再播」的老路
    lockPool: '',            // 导演层按轮锁定的情绪池
      cloneFailed: false,
      notify() {
        for (const fn of this.listeners) {
          try { fn(this.speaking) } catch (error) { /* listener gone */ }
        }
      },
      // 给 UI 层的广播：主题包可以只监听这个事件做波形/口型/背景律动，
      // 不必读我们的 DOM。契约：{ phase: 'start'|'end', text, speaking }
      signal(phase, detail) {
        try {
          window.dispatchEvent(new window.CustomEvent('sandrone:voice', {
            detail: Object.assign({ phase, speaking: phase !== 'end' }, detail || {}),
          }))
        } catch (error) { /* CustomEvent 不可用就算了 */ }
      },
      // 句间停顿：按标点分级，比「等 onended 再下一句」自然
      gapFor(line) {
        const text = String(line || '').trim()
        if (/[。！？…!?]["'”』」]?$/.test(text)) return 320
        if (/[；;]$/.test(text)) return 260
        if (/[，,、：:]$/.test(text)) return 140
        return 80
      },
      pauseFor(line) {
        const text = String(line || '').trim()
        let ms = 80
        if (/[。！？…!?]["'”』」]?$/.test(text)) ms = 320
        else if (/[；;]$/.test(text)) ms = 260
        else if (/[，,、：:]$/.test(text)) ms = 140
        return new Promise((resolve) => window.setTimeout(resolve, ms))
      },
      setEnabled(value) {
        this.enabled = !!value
        if (!value) this.stop()
      },
      stop() {
        this.stopStream()
        if (this.scheduled) {
          for (const node of this.scheduled) {
            try { node.stop() } catch (error) { /* already ended */ }
          }
          this.scheduled = []
        }
        /* 被中断的句子也要把文字放出来，否则那几句会永远看不见 */
        for (const entry of this.queue) {
          if (entry && entry.onStart) {
            try { entry.onStart() } catch (error) { /* ignore */ }
          }
        }
        this.queue.length = 0
        this.playingQueue = false
        if (this.audio) {
          try { this.audio.pause() } catch (error) { /* already stopped */ }
          try { this.audio.src = '' } catch (error) { /* ignore */ }
          this.audio = null
        }
        try { window.speechSynthesis.cancel() } catch (error) { /* no synthesis */ }
        if (this.speaking) {
          this.speaking = false
          this.notify()
        }
        this.signal('end', { interrupted: true })
      },
      pickVoice() {
        let voices = []
        try { voices = window.speechSynthesis.getVoices() || [] } catch (error) { voices = [] }
        const zh = voices.filter((v) => /^zh/i.test(String(v.lang || '')) || /Chinese|中文|Xiaoxiao|Yaoyao|Huihui|Yunxi|Tingting/i.test(String(v.name || '')))
        const pool = zh.length ? zh : voices
        // 桑多涅：偏低、偏慢、不甜的成年女声。雅瑶/晓晓/慧慧优先，康康（男声）与英文声一律避开。
        const prefer = [/Yaoyao|瑶瑶/i, /Xiaoxiao|晓晓/i, /Huihui|慧慧/i, /Xiaoyi|晓伊/i, /Tingting|婷婷/i, /Yunxi|云希/i]
        const avoid = [/Kangkang|康康/i, /Yunyang|云扬/i, /Zira|David|Mark|Guy|Ryan|Hazel|Susan/i]
        const scored = pool.filter((v) => !avoid.some((re) => re.test(String(v.name || '')))).map((v) => {
          const name = String(v.name || '')
          let s = 0
          prefer.forEach((re, index) => { if (re.test(name)) s += 30 - index * 3 })
          if (/Natural|Online|Neural/i.test(name)) s += 12
          if (/Female|女/i.test(name)) s += 4
          if (/zh[-_]CN/i.test(String(v.lang || ''))) s += 4
          return { v, s }
        })
        scored.sort((a, b) => b.s - a.s)
        this.voice = scored.length ? scored[0].v : (pool[0] || null)
        return this.voice
      },
      // 'auto' 交给作息表决定；'clips' 只播固定台词；'neural'/'clone' 是手动锁定
      resolvedEngine() {
        if (this.engine === 'off') return 'none'
        if (this.engine === 'clips') return 'clips'
        if (this.engine === 'clone' || this.engine === 'neural') return 'clone'
        return sandronePhase().engine
      },
      resting() {
        return this.resolvedEngine() === 'none'
      },
      voiceLabel() {
        if (this.engine === 'off') return '静音'
        if (this.engine === 'clips') return '固定语音'
        if (sandronePhase().kind === 'rest') return '休息 · 静音'
        if (this.cloneFailed) return '原声未就绪'
        return '桑多涅 · 原声'
      },
      demo() {
        this.sayClip('voice-demo', '语音回路已接通。……听得到吗。')
      },
      // 供面板底部状态用：一句话说明「现在为什么是这个声音」
      phaseHint() {
        const phase = sandronePhase()
        if (this.engine === 'off') return '已静音。'
        if (this.engine === 'clips') return '只播固定台词。'
        if (phase.kind === 'rest') return '这个点，不说话。'
        if (this.engine === 'clone') return '锁在原声。'
        return '一直用原声。'
      },
      async playClip(name) {
        if (!this.enabled || this.resting()) return false
        try {
          this.stop()
          const audio = new window.Audio('/sandrone/asset/voice/' + name + '.m4a?v=gs5')
          audio.volume = 0.95
          this.audio = audio
          audio.addEventListener('ended', () => {
            if (this.audio === audio) this.audio = null
            this.notify()
          })
          this.speaking = true
          this.notify()
          await audio.play()
          return true
        } catch (error) {
          this.speaking = false
          this.notify()
          return false
        }
      },
      sayClip(name, fallbackText) {
        if (!this.enabled) return
        this.playClip(name).then((ok) => {
          if (!ok && fallbackText) this.speak(fallbackText)
        })
      },
      chunk(text) {
        const clean = String(text)
          .replace(/```[\s\S]*?```/g, ' 代码略过 ')
          .replace(/[*_`#>~|]/g, '')
          .replace(/\[(.*?)\]\(.*?\)/g, '$1')
          .replace(/\s+/g, ' ')
          .trim()
        if (!clean) return []
        const parts = clean.split(/(?<=[。！？!?；;…])/u)
        const out = []
        let buf = ''
        for (const part of parts) {
          if ((buf + part).length > 62 && buf) { out.push(buf); buf = part } else { buf += part }
        }
        if (buf.trim()) out.push(buf)
        return out.slice(0, 12)
      },
      speak(text) {
        if (!this.enabled || this.resting()) return
        const chunks = this.chunk(text)
        if (!chunks.length) return
        this.stop()
        for (const part of chunks) this.queue.push(part)
        this.pumpQueue()
      },
      // 场景反应：想说话时直接插一条预制台词进队列（在回复之前播）
      sayReaction(name, text, onStart) {
        if (!name || !this.enabled || this.resting()) {
          if (onStart) { try { onStart() } catch (error) { /* ignore */ } }
          return false
        }
        this.queue.push({ clip: name, text: text || '', onStart })
        this.pumpQueue()
        return true
      },
      enqueue(sentence, onStart) {
        if (!this.enabled || this.resting()) {
          if (onStart) { try { onStart() } catch (error) { /* ignore */ } }
          return
        }
        const chunks = this.chunk(sentence)
        if (!chunks.length) {
          if (onStart) { try { onStart() } catch (error) { /* ignore */ } }
          return
        }
        chunks.forEach((part, index) => {
          this.queue.push({ line: part, onStart: index === 0 ? onStart : null })
        })
        this.pumpQueue()
      },
      // 播放队列：先把下一句的音频请求发出去，等当前这句播完立刻接上 —— 句间不留空档
      async pumpQueue() {
        if (this.playingQueue) return
        this.playingQueue = true
        try {
          let pending = null          // 上一句的「生成」任务（不是播放）
          let pendingLine = null
          while (this.queue.length && this.enabled && !this.resting()) {
            const current = this.queue.shift()
            // 锁：模型一次只能合成一句，所以这里等的是「上一句生成完」，
            // 而不是「上一句播完」——播放继续在时间轴上跑，合成已经往下走了。
            if (pending) await pending
            if (current.clip) {
              // 预制音频：直接排时间轴，不需要合成
              pending = this.beginClip(current.clip, current.text, current.onStart)
              pendingLine = current.text || ''
              continue
            }
            if (this.streamOn !== false) {
              // 句间停顿排进时间轴，避免两句黏在一起
              this.nextAt = (this.nextAt || 0) + this.gapFor(pendingLine || '') / 1000
              const first = pendingLine === null
              pendingLine = current.line
              pending = this.beginStream(current.line, current.onStart)
              // 第一句必须确认成功，否则「整段没声音」；后面几句允许后台跑。
              if (first) {
                const ok = await pending
                pending = null
                if (!ok) {
                  const blob = await this.fetchAudio(current.line)
                  if (blob) await this.playBlob(blob, current.line, current.onStart)
                  pendingLine = null
                }
              }
              continue
            }
            const blob = this.bufferLine(current).blob
            if (blob) {
              await this.playBlob(await blob, current.line, current.onStart)
            } else if (current.onStart) {
              try { current.onStart() } catch (error) { /* ignore */ }
              await new Promise((resolve) => window.setTimeout(resolve, 250))
            }
            if (this.queue.length && this.enabled && !this.resting()) await this.pauseFor(current.line)
          }
          if (pending) await pending
          await this.flushPlayback()
        } finally {
          this.playingQueue = false
          if (!this.queue.length && this.speaking) {
            this.speaking = false
            this.notify()
          }
          // 收尾瞬间又有人入队（比如回复还没到、场景反应先到）：
          // 这里补一次，否则那条会一直躺在队列里没人播。
          if (this.queue.length && this.enabled && !this.resting()) {
            window.setTimeout(() => { if (!this.playingQueue) this.pumpQueue() }, 0)
          }
        }
      },
      bufferLine(entry) {
        const item = typeof entry === "string" ? { line: entry, onStart: null } : entry
        // 流式模式下不预取整句，否则同一句会被合成两遍（一次流式、一次整句）
        if (this.streamOn === false) item.blob = this.fetchAudio(item.line)
        return item
      },
      // 只要音频，先不播：拿到 Blob 就返回
      async fetchAudio(line, engineOverride) {
        try {
          const engine = engineOverride || this.resolvedEngine()
          if (engine === 'none' || engine === 'clips') return null
          this.speaking = true
          this.notify()
          // 克隆在 CPU 上每句要十几到几十秒：超时就退回晓晓，别让她哑着
          const controller = window.AbortController ? new window.AbortController() : null
          const cap = window.setTimeout(() => { if (controller) controller.abort() }, 90000)
          let res
          try {
            res = await window.fetch('/sandrone/tts', {
              method: 'POST',
              headers: { 'content-type': 'application/json' },
              body: JSON.stringify({ text: line, engine, pool: this.lockPool || '' }),
              signal: controller ? controller.signal : undefined,
            })
          } finally {
            window.clearTimeout(cap)
          }
          if (!res.ok) {
            if (engine === 'clone') this.cloneFailed = true
            return null
          }
          const blob = await res.blob()
          if (!blob || !blob.size) {
            if (engine === 'clone') this.cloneFailed = true
            return null
          }
          this.neuralOk = true
          return blob
        } catch (error) {
          const engine = engineOverride || this.resolvedEngine()
          if (engine === 'clone') this.cloneFailed = true
          return null
        }
      },
      /* ── 流式播放 ─────────────────────────────────────────────────────
       * 宿主把 GPT-SoVITS 的 int16 PCM（32k 单声道）原样透传，这里分块塞进
       * Web Audio 的时间轴。第一块到了就能出声（≈0.7s），不用等整句。
       * 失败一律回落到「整句合成 + Audio」，不影响可用性。
       */
      ensureCtx() {
        const AC = window.AudioContext || window.webkitAudioContext
        if (!AC) return null
        if (!this.ctx) {
          try {
            this.ctx = new AC()
            this.gainNode = this.ctx.createGain()
            this.gainNode.gain.value = 0.95
            this.gainNode.connect(this.ctx.destination)
            this.nextAt = 0
          } catch (error) {
            return null
          }
        }
        if (this.ctx.state === 'suspended') this.ctx.resume().catch(() => {})
        return this.ctx
      },
      stopStream() {
        if (this.streamCtrl) {
          try { this.streamCtrl.abort() } catch (error) { /* ignore */ }
          this.streamCtrl = null
        }
        if (this.streamNodes) {
          for (const node of this.streamNodes) {
            try { node.stop() } catch (error) { /* ignore */ }
          }
          this.streamNodes = []
        }
        if (this.ctx) this.nextAt = this.ctx.currentTime
      },
      // 只负责「把这一句合成出来、并按时间轴排进播放」，不等它播完。
      // 返回 true 表示成功排入；false 表示这条路走不通，调用方回落到整句合成。
      // 预制台词（assets/voice/*.m4a）也排进同一条时间轴：
      // 这样「先放一句反应，再播回复」不会互相盖住。
      async beginClip(name, text, onStart) {
        if (!this.enabled || this.resting()) {
          if (onStart) { try { onStart() } catch (error) { /* ignore */ } }
          return false
        }
        const ctx = this.ensureCtx()
        if (!ctx) return false
        try {
          const res = await window.fetch('/sandrone/asset/voice/' + name + '.m4a?v=gs5', { cache: 'force-cache' })
          if (!res.ok) throw new Error('clip ' + res.status)
          const buf = await ctx.decodeAudioData(await res.arrayBuffer())
          const at = Math.max(ctx.currentTime + 0.06, this.nextAt || 0)
          const node = ctx.createBufferSource()
        this.scheduled = this.scheduled || []
        this.scheduled.push(node)
          node.buffer = buf
          node.connect(this.gain || ctx.destination)
          node.start(at)
          this.nextAt = at + buf.duration
          this.speaking = true
          const fire = () => {
            this.speaking = false
            this.notify()
            if (onStart) { try { onStart() } catch (error) { /* ignore */ } }
          }
          const delay = Math.max(0, (at - ctx.currentTime) * 1000)
          window.setTimeout(fire, delay)
          this.notify()
          return delay + buf.duration * 1000
        } catch (error) {
          if (onStart) { try { onStart() } catch (ignored) { /* ignore */ } }
          return false
        }
      },
      async beginStream(line, onStart) {
        if (!this.enabled || this.resting()) {
          if (onStart) { try { onStart() } catch (error) { /* ignore */ } }
          return false
        }
        if (this.resolvedEngine() === 'clips') {
          if (onStart) { try { onStart() } catch (error) { /* ignore */ } }
          return false
        }
        const ctx = this.ensureCtx()
        if (!ctx) return false
        const controller = window.AbortController ? new window.AbortController() : null
        this.streamCtrl = controller
        const cap = window.setTimeout(() => { if (controller) controller.abort() }, 90000)
        let res
        try {
          res = await window.fetch('/sandrone/tts', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ text: line, stream: true, pool: this.lockPool || '' }),
            signal: controller ? controller.signal : undefined,
          })
        } catch (error) {
          window.clearTimeout(cap)
          return false
        }
        window.clearTimeout(cap)
        if (!res.ok || !res.body || !res.body.getReader) return false

        this.speaking = true
        this.notify()
        const reader = res.body.getReader()
        this.streamNodes = []
        let carry = null
        let started = false
        try {
          for (;;) {
            const { done, value } = await reader.read()
            if (done) break
            if (!value || !value.length) continue
            let bytes = value
            if (carry) {
              const merged = new Uint8Array(carry.length + bytes.length)
              merged.set(carry, 0)
              merged.set(bytes, carry.length)
              bytes = merged
              carry = null
            }
            if (bytes.length % 2) {
              carry = bytes.slice(bytes.length - 1)
              bytes = bytes.subarray(0, bytes.length - 1)
            }
            if (!bytes.length) continue
            const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.length)
            const frames = bytes.length / 2
            const buf = ctx.createBuffer(1, frames, 32000)
            const channel = buf.getChannelData(0)
            for (let i = 0; i < frames; i += 1) channel[i] = view.getInt16(i * 2, true) / 32768
            const node = ctx.createBufferSource()
            node.buffer = buf
            node.connect(this.gainNode)
            const at = Math.max(ctx.currentTime + 0.06, this.nextAt || 0)
            node.start(at)
            this.nextAt = at + buf.duration
            this.streamNodes.push(node)
            if (!started) {
              started = true
              // 按排定的起播时刻放文字：预取下一句时，它的文字不会提前冒出来
              const delay = Math.max(0, (at - ctx.currentTime) * 1000)
              const fire = () => {
                this.signal('start', { text: line })
                if (onStart) {
                  try { onStart() } catch (error) { /* ignore */ }
                  onStart = null
                }
              }
              if (delay < 30) fire()
              else window.setTimeout(fire, delay)
            }
          }
        } catch (error) {
          /* 超时/中断：已排进时间轴的部分继续播完 */
        }
        if (!started) {
          if (onStart) { try { onStart() } catch (error) { /* ignore */ } }
          return false
        }
        this.signal('end', { text: line })
        return true
      },
      // 等时间轴上已排好的音频播完（不再发请求）
      async flushPlayback() {
        const ctx = this.ctx
        if (!ctx) return
        const remainMs = Math.max(0, ((this.nextAt || 0) - ctx.currentTime) * 1000) + 160
        if (remainMs > 0) await new Promise((resolve) => window.setTimeout(resolve, remainMs))
      },
      // 兼容旧调用：合成一句 + 等它播完
      async speakStream(line, onStart) {
        const ok = await this.beginStream(line, onStart)
        if (ok) await this.flushPlayback()
        return ok
      },
      // 播一段已合成好的音频，播完才 resolve
      async playBlob(blob, line, onStart) {
        try {
          const url = URL.createObjectURL(blob)
          const audio = new Audio(url)
          audio.volume = 0.95
          this.audio = audio
          const finished = new Promise((resolve) => {
            const done = () => resolve(true)
            audio.onended = done
            audio.onerror = done
            audio.onpause = () => { if (audio.ended) done() }
          })
          await audio.play()
          this.signal('start', { text: line })
          /* 声音真正响起的这一刻才放文字：对齐由播放而不是请求决定 */
          if (onStart) {
            try { onStart() } catch (error) { /* ignore */ }
            onStart = null
          }
          const played = await Promise.race([
            finished,
            new Promise((resolve) => {
              const timer = window.setTimeout(() => resolve(true), Math.max(4000, (line || '').length * 420))
              audio.addEventListener('ended', () => window.clearTimeout(timer))
            }),
          ])
          try { URL.revokeObjectURL(url) } catch (error) { /* ignore */ }
          if (this.audio === audio) this.audio = null
          this.signal('end', { text: line })
          return !!played
        } catch (error) {
          return false
        }
      },
      // 兼容旧调用点：一句合成 + 播放
      async sayLine(line, engineOverride) {
        const blob = await this.fetchAudio(line, engineOverride)
        if (!blob) return false
        return this.playBlob(blob, line)
      },
      // 浏览器本地语音兜底（宿主 TTS 不可用时）
      sayLocal(line) {
        return new Promise((resolve) => {
          const synthesis = window.speechSynthesis
          if (!synthesis || typeof window.SpeechSynthesisUtterance !== 'function') {
            resolve(false)
            return
          }
          const utterance = new window.SpeechSynthesisUtterance(line)
          const voice = this.voice || this.pickVoice()
          if (voice) {
            utterance.voice = voice
            utterance.lang = voice.lang || 'zh-CN'
          } else {
            utterance.lang = 'zh-CN'
          }
          utterance.rate = 0.88
          utterance.pitch = 0.66
          utterance.onstart = () => { this.speaking = true; this.notify() }
          utterance.onend = () => { this.speaking = false; this.notify(); resolve(true) }
          utterance.onerror = () => { this.speaking = false; this.notify(); resolve(false) }
          try { synthesis.speak(utterance) } catch (error) { resolve(false) }
        })
      },
      async neuralSay(line) {
        try {
          const res = await window.fetch('/sandrone/tts', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ text: line, voice: this.neural, rate: '-8%', pitch: '-12Hz' }),
          })
          if (!res.ok) return false
          const blob = await res.blob()
          if (!blob || !blob.size) return false
          const url = URL.createObjectURL(blob)
          const audio = new Audio(url)
          this.audio = audio
          this.neuralOk = true
          audio.onplay = () => { this.speaking = true; this.notify() }
          audio.onended = () => {
            this.speaking = false
            this.audio = null
            this.notify()
            try { URL.revokeObjectURL(url) } catch (error) { /* ignore */ }
          }
          audio.onerror = () => {
            this.speaking = false
            this.audio = null
            this.notify()
          }
          await audio.play()
          return true
        } catch (error) {
          return false
        }
      },
      pump() {
        const synthesis = window.speechSynthesis
        if (!synthesis) return
        if (!this.queue.length) {
          if (this.speaking) { this.speaking = false; this.notify() }
          return
        }
        const next = this.queue.shift()
        const utterance = new window.SpeechSynthesisUtterance(next)
        const voice = this.voice || this.pickVoice()
        if (voice) { utterance.voice = voice; utterance.lang = voice.lang || 'zh-CN' } else { utterance.lang = 'zh-CN' }
        utterance.rate = 0.88
        utterance.pitch = 0.66
        utterance.volume = 1
        utterance.onstart = () => { this.speaking = true; this.notify() }
        utterance.onend = () => { this.pump() }
        utterance.onerror = () => { this.speaking = false; this.notify(); this.queue.length = 0 }
        this.speaking = true
        this.notify()
        try { synthesis.speak(utterance) } catch (error) { this.speaking = false; this.notify() }
      },
    }

    /* ──────────────────────────── copy ──────────────────────────── */

    const GREET_CLIPS = {
      morning: 'greet-morning',
      noon: 'greet-noon',
      afternoon: 'greet-afternoon',
      evening: 'greet-evening',
      night: 'greet-night',
    }

    function greetSlot(hour) {
      if (hour >= 5 && hour < 10) return 'morning'
      if (hour >= 10 && hour < 13) return 'noon'
      if (hour >= 13 && hour < 18) return 'afternoon'
      if (hour >= 18 && hour < 23) return 'evening'
      return 'night'
    }

    function greetClip(hour) {
      return GREET_CLIPS[greetSlot(hour)]
    }

    // 法定节假日（只影响「要不要用原声」，不追求逐年精确；跨年后补下一年的表即可）
    const HOLIDAYS = new Set([
      '2025-01-01',
      '2025-01-28', '2025-01-29', '2025-01-30', '2025-01-31', '2025-02-01', '2025-02-02', '2025-02-03', '2025-02-04',
      '2025-04-04', '2025-04-05', '2025-04-06',
      '2025-05-01', '2025-05-02', '2025-05-03', '2025-05-04', '2025-05-05',
      '2025-05-31', '2025-06-01', '2025-06-02',
      '2025-10-01', '2025-10-02', '2025-10-03', '2025-10-04', '2025-10-05', '2025-10-06', '2025-10-07', '2025-10-08',
      '2026-01-01', '2026-01-02', '2026-01-03',
      '2026-02-16', '2026-02-17', '2026-02-18', '2026-02-19', '2026-02-20', '2026-02-21', '2026-02-22',
      '2026-04-04', '2026-04-05', '2026-04-06',
      '2026-05-01', '2026-05-02', '2026-05-03', '2026-05-04', '2026-05-05',
      '2026-06-19', '2026-06-20', '2026-06-21',
      '2026-09-25', '2026-09-26', '2026-09-27',
      '2026-10-01', '2026-10-02', '2026-10-03', '2026-10-04', '2026-10-05', '2026-10-06', '2026-10-07',
    ])

    function dateKey(date) {
      const pad = (n) => (n < 10 ? '0' + n : String(n))
      return date.getFullYear() + '-' + pad(date.getMonth() + 1) + '-' + pad(date.getDate())
    }

    // 作息：23:00–05:00 休息（不出原声、不说话）；周末与节假日可用原声；工作日只用快速神经语音
    function sandronePhase(now) {
      const date = now || new Date()
      const hour = date.getHours()
      if (hour >= 23 || hour < 5) return { kind: 'rest', engine: 'none', label: '休息 · 静音' }
      const day = date.getDay()
      const holiday = HOLIDAYS.has(dateKey(date))
      if (holiday || day === 0 || day === 6) return { kind: 'holiday', engine: 'clone', label: '假期 · 原声' }
      return { kind: 'workday', engine: 'clone', label: '日常 · 原声' }
    }

    // 场景反应：用户说了什么，就先回一句预制台词（文字 + 声音同时出）。
// 只在有配音时才播，休息时段直接跳过。
const REACTIONS = [
      // —— 更具体的先匹配，避免被宽泛规则吃掉 ——
      { test: /(早上好|早安|早啊)/, clip: 'react-morning', text: '早。……我顺手泡的。不是特意等你。' },
      { test: /(晚安|睡了|去睡|我先睡)/, clip: 'react-goodnight', text: '晚安。……明天见。' },
      { test: /(醒了|刚起|起床)/, clip: 'react-wake', text: '……几点。再躺三十秒，别叫我。' },
      { test: /(加班|通宵|熬到|熬夜)/, clip: 'react-overtime', text: '这个点还亮着屏，你是打算熬到天亮？' },
      { test: /(没吃|饿了|吃饭|晚饭|午饭)/, clip: 'react-meal', text: '先去吃饭。别等我算完这组数据。' },
      { test: /(腰疼|脖子|久坐|坐太久|站起来)/, clip: 'react-stretch', text: '起来动动。你的腰不是机偶的轴。' },
      { test: /(头疼|发烧|不舒服|感冒|难受)/, clip: 'react-sick', text: '声音不对。去睡，剩下的我记着。' },
      { test: /(难过|想哭|委屈|崩溃|emo)/i, clip: 'react-comfort', text: '……过来。什么都不用说，坐这儿。' },
      { test: /(对不起|抱歉|我的错|怪我)/, clip: 'react-sorry', text: '道歉收下了。下不为例。' },
      { test: /(失败|报错|崩了|没成|卡住)/, clip: 'react-fail', text: '没成。复盘一遍，别急着再来一次。' },
      { test: /(成功了|成了|跑通了|过了|搞定|做完了|完成了)/, clip: 'react-win', text: '成了。……我就说这条路能走通。' },
      { test: /(不想做|放弃|撂挑子|摆烂|算了不干)/, clip: 'react-giveup', text: '想撂挑子？可以。先把这页收尾。' },
      { test: /(歇会|休息|撑不住|太久了|停一下)/, clip: 'react-rest10', text: '再撑十分钟，然后必须停。' },
      { test: /(灯|刺眼|好亮|太暗)/, clip: 'react-nightlight', text: '灯调暗一点。眼睛比进度条重要。' },
      { test: /(你懂我|还是你|果然是你)/, clip: 'react-agree', text: '行。按你说的办。' },
      { test: /(为什么|怎么回事|奇怪|不对劲)/, clip: 'react-curious', text: '这个结论……有点意思。' },
      { test: /(差不多|基本|大概齐)/, clip: 'react-tease', text: '你又把「差不多」当「完成」了。' },
      { test: /(谢谢|多谢|感谢|thx|thanks)/i, clip: 'react-thanks', text: '谢什么。举手之劳，别弄得像多大的事。' },
      { test: /(好累|累死|撑不住|好困|想睡)/, clip: 'react-tired', text: '累了就靠一会儿。剩下的我来。' },
      { test: /(厉害|好强|牛|太强了|真棒|牛啊)/, clip: 'react-praise', text: '夸我也没用。……不过，你说得不算难听。' },
      { test: /(夸你|好看|可爱|喜欢你)/, clip: 'react-flatter', text: '……少来。你上次也这么说。' },
      { test: /(没空|稍后|等一下|忙|半小时)/, clip: 'react-busy', text: '现在不行。半小时后我找你。' },
      { test: /(你好|在吗|我回来了|我来了)/, clip: 'react-hello', text: '来了。坐。茶还热着。' },
      { test: /(今天就这样|收工|下班|明天再说)/, clip: 'react-wrapup', text: '今天到这儿。剩下的明天不会跑。' },
    ]

const GREET_TEXT = {
      morning: '醒了？……我不是特意来催你的。早。',
      noon: '午间了。先吃点东西——别拿「不饿」搪塞我。',
      afternoon: '下午了。有什么想让我一起想的，说吧。……今天心情还不错。',
      evening: '天黑了。今天还剩什么没做完？说清楚，我陪你收尾。',
      night: '还没睡。……哼，我又不是来管你的。……我陪着，你慢慢说。',
    }

    function greetingFor(hour) {
      return GREET_TEXT[greetSlot(hour)]
    }

    const CHIPS = ['你在忙什么？', '帮我把思路理一理', '今天有点累']

    const MURMURS = [
      { text: '……我在。', clip: 'whisper-listen' },
      { text: '齿轮还转着，别急。', clip: 'whisper-gear' },
      { text: '你今天安静得有点久。', clip: 'whisper-idle' },
      { text: '推演结束了。结论是你该歇一会儿。', clip: 'whisper-rest' },
      { text: '机偶不需要睡眠。你需要。', clip: 'whisper-rest' },
      { text: '有件事我算不准——你刚才在想什么。', clip: 'whisper-idle' },
      { text: '把一个难题拆开，它就没那么吓人了。放过来。', clip: 'whisper-listen' },
    ]

    /* 时段台词：不需要你说话，靠时间和概率自己冒出来。
       每条带一个权重，同一时段里随机挑；长时间没交互还会额外挑 idle-long。 */
    const AMBIENT = [
      { from: 5, to: 8, weight: 3, text: '天刚亮。……你醒得比齿轮还早。', clip: 'idle-dawn' },
      { from: 11, to: 13, weight: 3, text: '午饭时间。别又拿一杯水糊弄过去。', clip: 'idle-noon' },
      { from: 13, to: 17, weight: 2, text: '这个点最容易走神。……要说话就说，别硬撑。', clip: 'idle-afternoon' },
      { from: 17, to: 21, weight: 2, text: '天要黑了。今天想做的，还剩几件？', clip: 'idle-dusk' },
      { from: 23, to: 29, weight: 4, text: '这么晚还不睡？……我没催你，只是提醒一句。', clip: 'idle-late' },
    ]

    const AMBIENT_MIN_GAP = 600000   // 两条主动台词之间至少 10 分钟
    let ambientAt = 0

    function idleMurmur(idleMs) {
      const nowMs = Date.now()
      if (nowMs - ambientAt < AMBIENT_MIN_GAP) return null
      const hour = new Date().getHours()
      const slotHour = hour < 5 ? hour + 24 : hour
      const pool = AMBIENT.filter((item) => slotHour >= item.from && slotHour < item.to)
      // 长时间没动：优先说「你安静了挺久」
      if (idleMs && idleMs > 45 * 60 * 1000 && Math.random() < 0.45) {
        ambientAt = nowMs
        return { text: '你安静了挺久。……不是催你，只是我这边的齿轮空转着。', clip: 'idle-long' }
      }
      // 时段台词：60% 走时段，40% 走通用低语
      if (pool.length && Math.random() < 0.6) {
        const total = pool.reduce((sum, item) => sum + item.weight, 0)
        let roll = Math.random() * total
        const hit = pool.find((item) => (roll -= item.weight) <= 0) || pool[pool.length - 1]
        ambientAt = nowMs
        return { text: hit.text, clip: hit.clip }
      }
      ambientAt = nowMs
      return MURMURS[Math.floor(Math.random() * MURMURS.length)]
    }

    /* ──────────────────────────── storage ──────────────────────────── */

    function loadStored() {
      try {
        const raw = window.localStorage.getItem(STORAGE_KEY)
        if (!raw) return null
        const parsed = JSON.parse(raw)
        if (!parsed || typeof parsed !== 'object') return null
        return parsed
      } catch (error) { return null }
    }

    function saveStored(value) {
      try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value)) } catch (error) { /* private mode */ }
    }

    /* ──────────────────────────── panel ──────────────────────────── */

    const ICON_SPEAKER = h('svg', { viewBox: '0 0 24 24', width: '15', height: '15', fill: 'none', stroke: 'currentColor', strokeWidth: '1.7', strokeLinecap: 'round', strokeLinejoin: 'round' },
      h('path', { d: 'M4 9.5v5h3l4.5 3.5v-12L7 9.5z' }),
      h('path', { d: 'M16 8.5a5 5 0 0 1 0 7' }),
      h('path', { d: 'M18.8 6a8.5 8.5 0 0 1 0 12' }))

    const ICON_MUTE = h('svg', { viewBox: '0 0 24 24', width: '15', height: '15', fill: 'none', stroke: 'currentColor', strokeWidth: '1.7', strokeLinecap: 'round', strokeLinejoin: 'round' },
      h('path', { d: 'M4 9.5v5h3l4.5 3.5v-12L7 9.5z' }),
      h('path', { d: 'M16 9.5l5 5' }),
      h('path', { d: 'M21 9.5l-5 5' }))

    const ICON_MODEL = h('svg', {
      viewBox: '0 0 24 24', width: '15', height: '15', fill: 'none', stroke: 'currentColor',
      strokeWidth: '1.7', strokeLinecap: 'round', strokeLinejoin: 'round',
    },
    h('circle', { cx: '12', cy: '8', r: '3.4' }),
    h('path', { d: 'M5.5 20c0-3.4 2.9-5.6 6.5-5.6s6.5 2.2 6.5 5.6' }))

    const ICON_CLOSE = h('svg', { viewBox: '0 0 24 24', width: '14', height: '14', fill: 'none', stroke: 'currentColor', strokeWidth: '1.8', strokeLinecap: 'round' },
      h('path', { d: 'M6 6l12 12' }), h('path', { d: 'M18 6L6 18' }))

const ICON_CONSOLE = h('svg', { width: 15, height: 15, viewBox: '0 0 16 16', fill: 'none' },
  h('circle', { cx: 8, cy: 8, r: 2.3, stroke: 'currentColor', strokeWidth: 1.3 }),
  h('path', {
    d: 'M8 1.5v1.8M8 12.7v1.8M1.5 8h1.8M12.7 8h1.8M3.4 3.4l1.3 1.3M11.3 11.3l1.3 1.3M12.6 3.4l-1.3 1.3M4.7 11.3l-1.3 1.3',
    stroke: 'currentColor', strokeWidth: 1.15, strokeLinecap: 'round',
  }))

    const ICON_SEND = h('svg', { viewBox: '0 0 24 24', width: '15', height: '15', fill: 'none', stroke: 'currentColor', strokeWidth: '1.8', strokeLinecap: 'round', strokeLinejoin: 'round' },
      h('path', { d: 'M4 12l15-7-6.2 15-1.8-6.2z' }))

    function Panel(props) {
      const { messages, busy, link, voice, onVoice, onSend, onClose, onStop, model, onModel } = props
      const [draft, setDraft] = useState('')
      const logRef = useRef(null)
      const inputRef = useRef(null)

      useEffect(() => {
        const node = logRef.current
        if (node) node.scrollTop = node.scrollHeight
      }, [messages.length, messages[messages.length - 1] && messages[messages.length - 1].text])

      useEffect(() => {
        const node = inputRef.current
        if (!node) return
        node.style.height = 'auto'
        node.style.height = Math.min(node.scrollHeight, 92) + 'px'
      }, [draft])

      useEffect(() => { if (inputRef.current) inputRef.current.focus() }, [])

      const submit = () => {
        const text = draft.trim()
        if (!text || busy) return
        setDraft('')
        onSend(text)
      }

      const empty = messages.length === 0

      return h('div', { className: 'sdf-panel', role: 'dialog', 'aria-label': '桑多涅' },
        h('div', { className: 'sdf-head' },
          h('div', { className: 'sdf-mark' },
            h('svg', { viewBox: '0 0 24 24', width: '17', height: '17', fill: 'none', stroke: '#d9c9f8', strokeWidth: '1.4' },
              h('circle', { cx: '12', cy: '12', r: '6.4' }),
              h('circle', { cx: '12', cy: '12', r: '2', fill: '#d9c9f8', stroke: 'none' }),
              h('path', { d: 'M12 3.2v2.4M12 18.4v2.4M3.2 12h2.4M18.4 12h2.4' }))),
          h('div', null,
            h('div', { className: 'sdf-name' }, '桑多涅'),
            h('div', { className: 'sdf-sub' }, busy ? '推演中…' : '第七席 · 木偶')),
          h('div', { className: 'sdf-head-actions' },
            h('button', {
              className: 'sdf-icon-btn' + (voice ? ' sdf-on' : ''),
              title: voice ? '语音模式：开' : '语音模式：关',
              'aria-pressed': voice,
              onClick: () => {
                if (voice) { onStop(); onVoice(false); return }
                onVoice(true);
                window.setTimeout(() => SPEAKER.demo(), 80)
              },
            }, voice ? ICON_SPEAKER : ICON_MUTE),
            h('button', {
              className: 'sdf-icon-btn',
              title: '换形象（当前：' + petModel(model).label + '）',
              onClick: () => {
                const index = PET_MODELS.findIndex((item) => item.key === model)
                onModel(PET_MODELS[(index + 1) % PET_MODELS.length].key)
              },
            }, ICON_MODEL),
            h('button', {
              className: 'sdf-icon-btn',
              title: '打开控制台',
              onClick: () => { try { window.open('/sandrone/ui', '_blank') } catch (ignored) { /* noop */ } },
            }, ICON_CONSOLE),
            h('button', { className: 'sdf-icon-btn', title: '关闭', onClick: onClose }, ICON_CLOSE))),

        h('div', { className: 'sdf-log', ref: logRef },
          empty
            ? h('div', { className: 'sdf-empty' },
              greetingFor(new Date().getHours()),
              h('div', { className: 'sdf-chips' }, CHIPS.map((chip) => h('button', {
                key: chip, className: 'sdf-chip', onClick: () => onSend(chip),
              }, chip))))
            : messages.map((message, index) => h('div', {
              key: index,
              className: 'sdf-row' + (message.role === 'user' ? ' sdf-me' : ''),
            },
              h('div', { className: 'sdf-tag' }, message.role === 'user' ? USER_NAME : '桑多涅'),
              h('div', { className: 'sdf-bubble' + (message.error ? ' sdf-err' : '') },
                message.text || ' ',
                busy && index === messages.length - 1 && message.role === 'assistant'
                  ? h('span', { className: 'sdf-caret' })
                  : null)))),

        h('div', { className: 'sdf-compose' },
          h('div', { className: 'sdf-input-wrap' },
            h('textarea', {
              ref: inputRef,
              className: 'sdf-input',
              rows: 1,
              value: draft,
              placeholder: '和桑多涅说点什么…',
              onChange: (event) => setDraft(event.target.value),
              onKeyDown: (event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  submit()
                }
              },
            }),
            h('button', { className: 'sdf-send', disabled: busy || !draft.trim(), onClick: submit, title: '发送' }, ICON_SEND)),
          h('div', { className: 'sdf-foot' },
            h('span', { className: 'sdf-link' + (link === 'ok' ? ' sdf-ok' : link === 'bad' ? ' sdf-bad' : '') },
              h('span', { className: 'sdf-dot' }),
              link === 'ok' ? '回路已通' : link === 'bad' ? '回路中断' : '接通中'),
            h('div', { className: 'sdf-foot-spacer' }),
            h('button', {
            className: 'sdf-voice-tag' + (SPEAKER.resolvedEngine() === 'clone' ? ' is-clone' : ''),
            type: 'button',
            title: '点一下切换：固定台词 → 锁原声 → 跟随作息 → 静音',
            onClick: () => {
              const order = ['clips', 'clone', 'auto', 'off']
              const next = order[(order.indexOf(SPEAKER.engine) + 1) % order.length]
              SPEAKER.engine = next
              try { window.localStorage.setItem('sandrone-fairy:engine', next) } catch (error) { /* ignore */ }
              onVoice(voice)
              if (next === 'clone') SPEAKER.sayClip('voice-demo', '语音回路已接通。……听得到吗。')
            },
          }, voice ? '语音 · ' + SPEAKER.voiceLabel() : '语音关'),
            h('button', { className: 'sdf-text-btn', onClick: onStop }, '停声'),
            h('button', { className: 'sdf-text-btn', onClick: () => { onStop(); onClose() } }, '收起'))))
    }

    /* ──────────────────────────── overlay ──────────────────────────── */

    // 每次页面加载都放一次开屏：模块级变量随刷新重置，但 SPA 内导航不会重播。
    let bootedThisLoad = false
    const BOOT_KEY = 'sandrone-fairy:booted'

    function bootedBefore() {
      return bootedThisLoad
    }

    /* 机偶尺寸与 CSS 的 min(400px, 29vw) 保持一致 */
    function fairySize() {
      const cap = Math.max(160, Math.min(560, Number((PLUGIN_CFG && PLUGIN_CFG.pet && PLUGIN_CFG.pet.size) || 400)))
      const w = Math.min(cap, window.innerWidth * 0.29)
      return { w, h: w }
    }

    /* 常驻位置：左下角 */
    function defaultPos() {
      const size = fairySize()
      const y = Math.max(10, Math.round(window.innerHeight - size.h - 16))
      const x = PET_CORNER === 'bottom-right'
        ? Math.max(10, Math.round(window.innerWidth - size.w - 18))
        : 18
      return { x, y }
    }

    /* ── 桌宠形象：四张图可切换，选择写回宿主配置 ── */
    const PET_MODELS = [
      { key: 'classic', label: '立绘', src: 'figure.png' },
      { key: 'sit', label: '侧坐', src: 'figure-sit.png' },
      { key: 'cake', label: '甜点', src: 'figure-cake.png' },
      { key: 'pout', label: '嘟嘴', src: 'figure-pout.png' },
    ]
    let USER_NAME = '雪'
  /* 运行档位：宿主按显存自动判定，客户端据此收紧「念几句、念多长、要不要流式」 */
  let VOICE_TIER = null
let PLUGIN_CFG = null

const PET_ASSET_VERSION = 'm1'

    function petModel(key) {
      return PET_MODELS.find((item) => item.key === key) || PET_MODELS[0]
    }

    function petSrc(key) {
      return '/sandrone/asset/' + petModel(key).src + '?v=' + PET_ASSET_VERSION
    }

    /* ── 部件开关：宿主 /sandrone/config 下发，浏览器半边启动时读一次 ── */
    const CONFIG_FALLBACK = {
      version: 1,
      parts: { splash: false, pet: true, voice: true },
      splash: { everyLoad: true, greeting: true },
      pet: { corner: 'bottom-left', panel: 'top-right', model: 'classic' },
      voice: { mode: 'clips', userName: '你' },
      ui: { skin: 'workshop' },
    }

    function usePluginConfig() {
      const [cfg, setCfg] = useState(null)
      useEffect(() => {
        let alive = true
        const settle = window.setTimeout(() => { if (alive) setCfg((cur) => cur || CONFIG_FALLBACK) }, 900)
        fetch('/sandrone/config', { headers: { accept: 'application/json' } })
          .then((response) => (response.ok ? response.json() : null))
          .then((json) => { if (alive && json && json.parts) { window.clearTimeout(settle); setCfg(json) } })
          .catch(() => {})
        return () => { alive = false; window.clearTimeout(settle) }
      }, [])
      return cfg
    }

    let PET_CORNER = 'bottom-left'

    function Overlay(props) {
      const stored = useMemo(() => loadStored(), [])
      const cfg = usePluginConfig()
      const applySkinTheme = props && props.applySkinTheme
      const parts = (cfg && cfg.parts) || { splash: false, pet: true, voice: true }
      const skin = (cfg && cfg.ui && cfg.ui.skin) || 'workshop'
      PLUGIN_CFG = cfg
      const [stage, setStage] = useState('boot')
      const [leaving, setLeaving] = useState(false)
      const [open, setOpen] = useState(false)
      const [messages, setMessages] = useState(() => (stored && Array.isArray(stored.messages) ? stored.messages.slice(-40) : []))
      const [busy, setBusy] = useState(false)
      const [link, setLink] = useState('')
      const [voice, setVoice] = useState(() => (stored && typeof stored.voice === 'boolean' ? stored.voice : true))
      const [speaking, setSpeaking] = useState(false)
      const [whisper, setWhisper] = useState(null)
      const [model, setModel] = useState('classic')
      const [petEnabled, setPetEnabled] = useState(true)
      const [pos, setPos] = useState(() => {
        const saved = stored && stored.pos
        if (saved && typeof saved.x === 'number' && typeof saved.y === 'number') return saved
        return null
      })
      const dragRef = useRef({ active: false, moved: false, dx: 0, dy: 0 })
      const fairyRef = useRef(null)
      const lastTouch = useRef(Date.now())
      const messagesRef = useRef(messages)
      messagesRef.current = messages

      /* 配置到手后再决定播不播开屏；同时同步语音开关与桌宠角落 */
      useEffect(() => {
        if (!cfg || stage !== 'boot') return
        if (cfg.pet && cfg.pet.corner) PET_CORNER = cfg.pet.corner === 'bottom-right' ? 'bottom-right' : 'bottom-left'
        const skip = cfg.splash && cfg.splash.everyLoad === false
        const wantSplash = parts.splash !== false && !skip && !bootedBefore()
        setStage(wantSplash ? 'splash' : 'ready')
      }, [cfg, stage, parts.splash])

      useEffect(() => {
        if (!cfg) return
        if (cfg.pet && cfg.pet.model) setModel(cfg.pet.model)
        setPetEnabled(parts.pet !== false)
    if (cfg.voice && cfg.voice.userName) USER_NAME = String(cfg.voice.userName)
        /* 档位：拿到就按它收紧语音量；没拿到按默认（A）走 */
        window.fetch('/sandrone/tier', { cache: 'no-store' })
          .then((res) => (res.ok ? res.json() : null))
          .then((tier) => {
            if (!tier) return
            VOICE_TIER = tier
            if (tier.stream === false) SPEAKER.streamOn = false
          })
          .catch(() => { /* 探测失败保持默认 */ })
        SPEAKER.enabled = parts.voice !== false
        const mode = cfg.voice && typeof cfg.voice.mode === 'string' ? cfg.voice.mode : 'auto'
        SPEAKER.engine = mode
        try { window.localStorage.setItem('sandrone-fairy:engine', mode) } catch (error) { /* ignore */ }
      }, [cfg, parts.voice])

      /* 运行时皮肤：aurora 才整层覆盖主题 token，workshop 保持主题黑金 */
      useEffect(() => {
        if (typeof applySkinTheme === 'function') applySkinTheme(skin)
      }, [applySkinTheme, skin])

      /* 工坊开关：不刷新页面直接控制桌宠显隐 */
      useEffect(() => {
        const onPet = (event) => {
          const enabled = !(event && event.detail && event.detail.enabled === false)
          setPetEnabled(enabled)
          if (!enabled) {
            setOpen(false)
            setWhisper(null)
          }
        }
        window.addEventListener('sandrone:pet', onPet)
        return () => window.removeEventListener('sandrone:pet', onPet)
      }, [])

      /* 面板一开就预热语音服务：人还在打字，模型已经在加载。
         收起后通知宿主 90s 再卸载（内存还给系统，但下一次打开不必再等冷启动）。 */
      useEffect(() => {
        if (!cfg || parts.voice === false) return undefined
        const url = '/sandrone/voice/session'
        try {
          window.fetch(url, {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ active: !!open }),
          }).catch(() => {})
        } catch (error) { /* ignore */ }
        return undefined
      }, [open, cfg, parts.voice])

      /* splash bookkeeping */
      useEffect(() => {
        if (stage !== 'splash') return undefined
        bootedThisLoad = true
        setLeaving(false)
        const skipMs = Math.max(4200, Math.min(20000, Number((PLUGIN_CFG && PLUGIN_CFG.splash && PLUGIN_CFG.splash.skipMs) || 7600)))
        const leaveAt = Math.max(2000, skipMs - 1200)
        const greetAt = Math.max(600, skipMs - 3700)
        const sayGreeting = !(PLUGIN_CFG && PLUGIN_CFG.splash && PLUGIN_CFG.splash.greeting === false)
        const leave = window.setTimeout(() => setLeaving(true), leaveAt)
        /* 开屏收尾：她的原声问候（休息时段不出声） */
        const hi = sayGreeting
          ? window.setTimeout(() => { SPEAKER.sayClip('welcome', '……哼，回来了。我又没在等你。……茶还热着，坐下吧。') }, greetAt)
          : null
        const done = window.setTimeout(() => {
          setStage('ready')
          setOpen(true)
          // 离开超过 30 分钟再回来：先接一句「回来了」（预制音频，零延迟）
          try {
            const stored = loadStored()
            const gap = stored && stored.seenAt ? Date.now() - stored.seenAt : 0
            if (gap > 150 * 60 * 1000 && gap < 24 * 3600 * 1000 && !SPEAKER.resting()) {
              const line = '回来了。……茶凉了，我重泡一杯。'
              setWhisper(line)
              SPEAKER.sayClip('welcome-back', line)
              window.setTimeout(() => setWhisper(null), 8000)
            }
          } catch (error) { /* ignore */ }
        }, skipMs)
        return () => { window.clearTimeout(leave); if (hi) window.clearTimeout(hi); window.clearTimeout(done) }
      }, [stage])

      useEffect(() => {
        if (stage !== 'splash') return undefined
        const skip = () => setLeaving(true)
        window.addEventListener('pointerdown', skip, { once: true })
        return () => window.removeEventListener('pointerdown', skip)
      }, [stage])

      /* default position: bottom-right, sized by the same formula the CSS uses */
      useEffect(() => {
        if (pos) return
        setPos(defaultPos())
      }, [pos])

      useEffect(() => {
        const onResize = () => {
          setPos((current) => {
            if (!current) return current
            const size = fairySize()
            return {
              x: Math.min(current.x, Math.max(0, window.innerWidth - size.w - 6)),
              y: Math.min(current.y, Math.max(0, window.innerHeight - size.h - 6)),
            }
          })
        }
        window.addEventListener('resize', onResize)
        return () => window.removeEventListener('resize', onResize)
      }, [])

      /* voice plumbing */
      useEffect(() => {
        const listener = (value) => setSpeaking(value)
        SPEAKER.listeners.add(listener)
        SPEAKER.enabled = voice
        const warm = () => { try { SPEAKER.pickVoice() } catch (error) { /* ignore */ } }
        warm()
        try { window.speechSynthesis && window.speechSynthesis.addEventListener('voiceschanged', warm) } catch (error) { /* ignore */ }
        return () => {
          SPEAKER.listeners.delete(listener)
          try { window.speechSynthesis && window.speechSynthesis.removeEventListener('voiceschanged', warm) } catch (error) { /* ignore */ }
          SPEAKER.stop()
        }
      }, [])

      useEffect(() => { SPEAKER.setEnabled(voice) }, [voice])

      /* persist */
      useEffect(() => {
        saveStored({ messages: messages.slice(-40), voice, pos: pos || undefined, seenAt: Date.now() })
      }, [messages, voice, pos])

      /* bridge health */
      const probe = useCallback(async () => {
        try {
          const response = await fetch(PING_PATH, { method: 'GET', cache: 'no-store' })
          setLink(response.ok ? 'ok' : 'bad')
        } catch (error) { setLink('bad') }
      }, [])

      useEffect(() => {
        probe()
        const id = window.setInterval(probe, 30000)
        return () => window.clearInterval(id)
      }, [probe])

      /* idle murmurs */
      useEffect(() => {
        if (stage !== 'ready') return undefined
        const id = window.setInterval(() => {
          if (open || busy || speaking) return
          if (Date.now() - lastTouch.current < 110000) return
          if (Math.random() > 0.3) return
          if (SPEAKER.resting() && new Date().getHours() >= 5) return
          const murmur = idleMurmur(Date.now() - lastTouch.current)
          if (!murmur) return
          setWhisper(murmur.text)
          SPEAKER.sayClip(murmur.clip, murmur.text)
          lastTouch.current = Date.now()
          window.setTimeout(() => setWhisper(null), 8000)
        }, 900000)
        return () => window.clearInterval(id)
      }, [stage, open, busy, speaking])

      const touch = () => { lastTouch.current = Date.now() }

      const send = useCallback(async (text) => {
        if (busy) return
        touch()
        setWhisper(null)
        const history = messagesRef.current
          .filter((m) => !m.error && m.text)
          .map((m) => ({ role: m.role, text: m.text }))
        const nextMessages = messagesRef.current.concat([{ role: 'user', text }, { role: 'assistant', text: '' }])
        setMessages(nextMessages)
        setBusy(true)
        SPEAKER.stop()

        // 先接一句场景反应（先进队列，所以会排在回复语音前面播）
        const hit = REACTIONS.find((rule) => rule.test.test(String(text || '')))
        if (hit) {
          SPEAKER.sayReaction(hit.clip, hit.text, () => {
          setWhisper(hit.text)
          window.setTimeout(() => setWhisper((cur) => (cur === hit.text ? null : cur)), 6000)
        })
        }

        let answer = ''
        let failed = false
        let spoken = { cut: 0, voiced: 0, pieces: 0 }
        const END_RE = /[。！？…!?；;\n]/
        /* 人设校验（确定性规则，不依赖模型自觉）：
           ① 越权承诺——她只是个寄居在终端里的机偶，不能替雪改文件/跑命令；
           ② 甜腻低幼——「人家/宝宝/亲亲/抱抱/喵/哒」这类词一旦出现就不是她了。
           命中就不让这句出声，文字照常显示（她说过的话不能被偷偷改掉）。 */
        const GUARD_OVERREACH = /(?:我|帮你|替你)[^。！？]{0,6}(?:改|删|跑|执行|安装|重启|写进|保存到)|(?:我来|已经)[^。！？]{0,4}(?:改|删|跑|执行|安装|重启)/
        const GUARD_SOFT = /(?:人家|宝宝|亲亲|抱抱|小可爱|喵呜|喵~|哒啦|嘻嘻)/

        const guardCheck = (text) => {
          const s1 = String(text || '')
          if (GUARD_OVERREACH.test(s1)) return 'overreach'
          if (GUARD_SOFT.test(s1)) return 'soft'
          return ''
        }

        const VOICE_CAP = VOICE_TIER && VOICE_TIER.maxChars ? VOICE_TIER.maxChars : 58
        const VOICE_PIECES = VOICE_TIER && VOICE_TIER.maxPieces ? VOICE_TIER.maxPieces : 2
        const canVoice = () => SPEAKER.enabled && !SPEAKER.resting()
          && spoken.pieces < VOICE_PIECES && spoken.voiced < VOICE_CAP

        /* 文字按「句」排队：有语音的句子等声音响起来才显示，没语音的立刻显示。
           这样看到哪句、就听到哪句，顺序也不会被异步合成打乱。 */
        const segs = []
        let revealHead = 0
        let segmentsDone = false
        const paint = () => {
          while (revealHead < segs.length && segs[revealHead].ready) revealHead += 1
          const shown = segs.slice(0, revealHead).map((seg) => seg.text).join('')
          const cursor = revealHead < segs.length || !segmentsDone ? '…' : ''
          setMessages((current) => {
            const copy = current.slice()
            const last = copy[copy.length - 1]
            if (last && last.role === 'assistant') {
              copy[copy.length - 1] = { role: 'assistant', text: shown + cursor }
            }
            return copy
          })
        }
        const pushSeg = (text, ready) => {
          segs.push({ text, ready })
          if (ready) paint()
        }
        try {
          /* 本轮重新开始：清掉上一轮的情绪锁定，模型不给标签就逐句现算 */
          SPEAKER.lockPool = ''
          const response = await fetch(CHAT_PATH, {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ messages: history.concat([{ role: 'user', text }]) }),
          })
          if (!response.ok || !response.body) throw new Error('HTTP ' + response.status)
          const reader = response.body.getReader()
          const decoder = new TextDecoder()
          let buffer = ''
          let finished = false
          while (!finished) {
            const { done, value } = await reader.read()
            if (done) break
            buffer += decoder.decode(value, { stream: true })
            let index = buffer.indexOf('\n')
            while (index >= 0) {
              const line = buffer.slice(0, index).trim()
              buffer = buffer.slice(index + 1)
              index = buffer.indexOf('\n')
              if (!line) continue
              let event = null
              try { event = JSON.parse(line) } catch (error) { continue }
              if (event.t === 'emo' && typeof event.value === 'string') {
                /* 导演层给的档位：这一整轮都用它，避免一段话里忽冷忽热 */
                if (['cool', 'warm', 'tease', 'tired'].includes(event.value)) {
                  SPEAKER.lockPool = event.value
                }
                continue
              }
              if (event.t === 'delta' && typeof event.text === 'string') {
                answer += event.text
                /* 文字先出来，凑够一句就立刻送去合成 —— 语音与文字同进 */
                let cut = -1
                for (let i = spoken.cut; i < answer.length; i += 1) {
                  if (END_RE.test(answer[i])) cut = i
                }
                /* 一直没遇到句号就先在逗号处断，再不行满 16 字也断：别让第一声等太久 */
                if (cut < 0 && !spoken.firstCut) {
                  for (let i = spoken.cut; i < answer.length; i += 1) {
                    if (/[，,、：:]/.test(answer[i])) { cut = i; break }
                  }
                  if (cut < 0 && answer.length - spoken.cut >= 16) cut = answer.length - 1
                }
                if (cut >= 0) {
                  const piece = answer.slice(spoken.cut, cut + 1).trim()
                  spoken.cut = cut + 1
                  if (!spoken.firstCut) spoken.firstCut = true
                  const bare = piece.replace(/\s/g, '')
                  const guardHit = guardCheck(piece)
                  if (guardHit) {
                    try {
                      console.warn('[sandrone-fairy] guard blocked voice:', guardHit, piece.slice(0, 40))
                    } catch (ignored) { /* noop */ }
                  }
                  if (bare.length >= 2 && canVoice() && !guardHit) {
                    spoken.voiced += bare.length
                    spoken.pieces += 1
                    const index = segs.length
                    segs.push({ text: piece, ready: false })
                    SPEAKER.enqueue(piece, () => {
                      if (segs[index]) segs[index].ready = true
                      paint()
                    })
                  } else if (piece) {
                    pushSeg(piece, true)
                  }
                }
              } else if (event.t === 'error') {
                failed = true
                answer = (answer ? answer + '\n' : '') + (event.text || '回路出岔子了。')
              }
            }
          }
        } catch (error) {
          failed = true
          answer = '……回路断了。检查一下主机那边。'
        }

        segmentsDone = true
        if (failed) {
          segs.length = 0
          revealHead = 0
          segs.push({ text: answer || '……', ready: true })
        } else if (answer.slice(spoken.cut).trim()) {
          pushSeg(answer.slice(spoken.cut).trim(), true)
        }
        setMessages((current) => {
          const copy = current.slice()
          const last = copy[copy.length - 1]
          if (last && last.role === 'assistant') {
            copy[copy.length - 1] = {
              role: 'assistant',
              text: segs.slice(0, revealHead).map((seg) => seg.text).join('') || '……',
              error: failed,
            }
          }
          return copy
        })
        setBusy(false)
        lastTouch.current = Date.now()
      }, [busy])

      /* drag */
      const onPointerDown = (event) => {
        if (event.button !== undefined && event.button !== 0) return
        const node = fairyRef.current
        if (!node) return
        const rect = node.getBoundingClientRect()
        dragRef.current = { active: true, moved: false, dx: event.clientX - rect.left, dy: event.clientY - rect.top }
        node.setPointerCapture && node.setPointerCapture(event.pointerId)
        node.classList.add('sdf-dragging')
      }
      const onPointerMove = (event) => {
        const drag = dragRef.current
        if (!drag.active) return
        const x = Math.min(Math.max(0, event.clientX - drag.dx), Math.max(0, window.innerWidth - 90))
        const y = Math.min(Math.max(0, event.clientY - drag.dy), Math.max(0, window.innerHeight - 90))
        if (Math.abs(x - (pos ? pos.x : 0)) > 2 || Math.abs(y - (pos ? pos.y : 0)) > 2) drag.moved = true
        setPos({ x, y })
      }
      const onPointerUp = (event) => {
        const drag = dragRef.current
        if (!drag.active) return
        drag.active = false
        const node = fairyRef.current
        if (node) {
          node.classList.remove('sdf-dragging')
          node.releasePointerCapture && (() => { try { node.releasePointerCapture(event.pointerId) } catch (error) { /* ignore */ } })()
        }
        touch()
        if (!drag.moved) {
          // 浏览器要求 AudioContext 在用户手势里创建：点她这一下顺手把播放上下文备好，
          // 之后流式播放就不会被「必须交互」挡住
          try { SPEAKER.ensureCtx() } catch (error) { /* ignore */ }
          setOpen((value) => !value)
          setWhisper(null)
        }
      }

      useEffect(() => {
        if (!open) return undefined
        try { SPEAKER.ensureCtx() } catch (error) { /* ignore */ }
        const onKey = (event) => {
          if (event.key === 'Escape') setOpen(false)
        }
        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
      }, [open])

      const fairyStyle = { left: (pos ? pos.x : 0) + 'px', top: (pos ? pos.y : 0) + 'px' }

      if (!cfg || stage === 'boot') return null

      return h('div', { className: 'sdf-root sdf-skin-' + skin },
        h('div', { className: 'sdf-ambient' }),
        stage === 'splash'
          ? h('div', {
            className: 'sdf-splash' + (leaving ? ' sdf-leaving' : ''),
            onClick: () => setLeaving(true),
          },
            h('div', { className: 'sdf-splash-inner' },
              h('div', { className: 'sdf-cinebox' },
                h('img', { className: 'sdf-art', src: '/sandrone/asset/cine.jpg', alt: '', draggable: 'false' })),
              h('div', { className: 'sdf-veil' }),
              h('div', { className: 'sdf-ringwrap' }, SplashStage()),
              h('div', { className: 'sdf-reveal' },
                h('div', { className: 'sdf-reveal-burst' }),
                h('div', { className: 'sdf-reveal-glow' }),
                h('img', { className: 'sdf-reveal-figure', src: '/sandrone/asset/figure.png', alt: '', draggable: 'false' })),
              h('div', { className: 'sdf-copy' },
                h('div', { className: 'sdf-title' }, '桑多涅'),
              h('div', { className: 'sdf-subtitle' }, 'SANDRONE · 第七席 · 木偶'),
              h('div', { className: 'sdf-rule' }),
              h('div', { className: 'sdf-bar' }, h('i')),
                h('div', { className: 'sdf-boot-line' }, leaving ? '桑多涅' : '机偶唤醒中…'))),
            h('div', { className: 'sdf-corner' }, 'DSH · 机偶终端'),
            h('div', { className: 'sdf-skip' }, '点击跳过'))
          : null,

        stage === 'ready' && petEnabled
          ? h('div', {
            ref: fairyRef,
            className: 'sdf-fairy sdf-enter' + (speaking ? ' sdf-speaking' : '') + (PET_CORNER === 'bottom-right' ? ' sdf-right' : ''),
            style: fairyStyle,
            role: 'button',
            tabIndex: 0,
            title: '桑多涅',
            onPointerDown,
            onPointerMove,
            onPointerUp,
            onPointerCancel: onPointerUp,
            onDoubleClick: () => { setOpen(false); setWhisper(null); setStage('splash') },
            onKeyDown: (event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                setOpen((value) => !value)
              }
            },
          },
            h('img', { className: 'sdf-card-img', src: petSrc(model), alt: '', draggable: 'false' }),
            h('div', { className: 'sdf-card-pulse' }),
            h('div', { className: 'sdf-fairy-burst' }),
            whisper
              ? h('div', {
                className: 'sdf-whisper',
                onClick: (event) => { event.stopPropagation(); setWhisper(null) },
                onPointerDown: (event) => event.stopPropagation(),
              }, whisper)
              : null)
          : null,

        open && stage === 'ready' && petEnabled
          ? h(Panel, {
            messages,
            busy,
            link,
            voice,
            onVoice: setVoice,
            onSend: send,
            onStop: () => SPEAKER.stop(),
            model,
            onModel: (next) => {
              setModel(next)
              try {
                fetch('/sandrone/config', {
                  method: 'POST',
                  headers: { 'content-type': 'application/json' },
                  body: JSON.stringify({ pet: { model: next } }),
                }).catch(() => {})
              } catch (error) { /* ignore */ }
            },
            onClose: () => { setOpen(false); SPEAKER.stop() },
          })
          : null)
    }

    /* ──────────────────────────── plugin ──────────────────────────── */

    /** A frame-wide occupant must never take the app down with it. */
    class Guard extends React.Component {
      constructor(props) {
        super(props)
        this.state = { failed: false }
      }
      static getDerivedStateFromError() { return { failed: true } }
      componentDidCatch(error) {
        try { console.error('[sandrone-fairy]', error) } catch (ignored) { /* no console */ }
      }
      render() {
        if (this.state.failed) return null
        return this.props.children
      }
    }

    /* ── 桑多涅主题：深蓝底 + 紫色点缀（整层覆盖 DSH 主题 token） ── */
    const SANDRONE_TOKENS = {
      '--dsw-alias-bg-base': { light: '#eef0fb', dark: '#05061a' },
      '--dsw-alias-bg-layer-1': { light: '#f8f8fe', dark: '#0a0d25' },
      '--dsw-alias-bg-layer-2': { light: '#ecebfa', dark: '#111539' },
      '--dsw-alias-bg-overlay': { light: '#ffffff', dark: '#141838' },
      '--dsw-alias-border-l1': { light: '#ded9f2', dark: '#241f4d' },
      '--dsw-alias-border-l2': { light: '#c8c0ea', dark: '#3a3070' },
      '--dsw-alias-brand-primary': { light: '#7440e0', dark: '#a878ff' },
      '--dsw-alias-label-primary': { light: '#171331', dark: '#e8e3ff' },
      '--dsw-alias-label-secondary': { light: '#5b5480', dark: '#a49bd4' },
      '--dsw-alias-state-error-primary': { light: '#c2325b', dark: '#ff6b8a' },
      '--dsw-alias-state-idle-primary': { light: '#8a84a6', dark: '#736c9e' },
      '--dsw-alias-state-success-primary': { light: '#128a72', dark: '#5fd8bf' },
      '--dsw-alias-state-warn-primary': { light: '#a87514', dark: '#e8bd6b' },
      '--dsw-specific-sidebar-fill': { light: '#e9e8f7', dark: '#070922' },
    }

    return {
      inject: ['slots'],
      apply(ctx) {
        ctx.effect(() => {
          const style = document.createElement('style')
          style.id = CSS_ID
          style.textContent = CSS
          document.head.appendChild(style)
          return () => { if (style.parentNode) style.parentNode.removeChild(style) }
        }, 'sandrone-fairy.styles')

        /* 运行时皮肤开关：cfg.ui.skin === 'aurora' 才整层覆盖主题 token；
           'workshop' 不覆盖，让主题的黑金透出。 */
        let themeService = null
        try { themeService = ctx.get('theme') } catch (error) { /* 没有主题服务就算了 */ }
        let themeOverrideApplied = false
        let themeOverrideDispose = null
        const applySkinTheme = (skin) => {
          const aurora = skin === 'aurora'
          if (!aurora) {
            if (themeOverrideApplied) {
              if (typeof themeOverrideDispose === 'function') {
                try { themeOverrideDispose() } catch (error) { /* ignore */ }
              }
              themeOverrideApplied = false
              themeOverrideDispose = null
            }
            return
          }
          if (!themeOverrideApplied && themeService && typeof themeService.overrideTokens === 'function') {
            try {
              themeOverrideDispose = themeService.overrideTokens('sandrone-fairy', SANDRONE_TOKENS)
              themeOverrideApplied = true
            } catch (error) {
              try { console.error('[sandrone-fairy] theme', error) } catch (ignored) { /* no console */ }
            }
          }
        }
        ctx.effect(() => () => {
          if (themeOverrideApplied && typeof themeOverrideDispose === 'function') {
            try { themeOverrideDispose() } catch (error) { /* ignore */ }
          }
        }, 'sandrone-fairy.theme-dispose')

        ctx.slots.inject('shell.overlay', () => ctx.slots.register({
          name: 'shell.overlay',
          id: 'sandrone-fairy',
          order: 60,
        }, () => h(Guard, null, h(Overlay, { applySkinTheme }))))
      },
    }
  },
})
