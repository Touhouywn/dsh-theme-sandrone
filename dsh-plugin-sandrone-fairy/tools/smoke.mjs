#!/usr/bin/env node
// sandrone-fairy smoke test — checks the four routes the plugin exposes.
//
//   node tools/smoke.mjs            # auto-detect the local dsh web port
//   node tools/smoke.mjs 54306      # or pass it explicitly
//
// Exit code 0 = everything that should work, works.

const argPort = process.argv[2];
const CANDIDATE_PORTS = [argPort, process.env.DSH_WEB_PORT, 54306].filter(Boolean);

const green = (s) => `\x1b[32m${s}\x1b[0m`;
const red = (s) => `\x1b[31m${s}\x1b[0m`;
const dim = (s) => `\x1b[2m${s}\x1b[0m`;
const bold = (s) => `\x1b[1m${s}\x1b[0m`;

function report(ok, label, detail) {
  console.log(`${ok ? green('PASS') : red('FAIL')}  ${label}${detail ? dim(`  ${detail}`) : ''}`);
  return ok;
}

async function tryPort(port) {
  try {
    const res = await fetch(`http://127.0.0.1:${port}/sandrone/config`, {
      signal: AbortSignal.timeout(2500),
    });
    return res.ok ? port : null;
  } catch {
    return null;
  }
}

async function main() {
  const explicit = argPort || process.env.DSH_WEB_PORT;
  let port = null;

  if (explicit) {
    port = await tryPort(explicit);
  } else {
    // Walk the usual dsh web port range.
    for (let p = 54300; p <= 54400 && !port; p += 1) port = await tryPort(p);
    if (!port) for (let p = 62000; p <= 62500 && !port; p += 5) port = await tryPort(p);
  }

  if (!port) {
    console.log(red('FAIL') + '  cannot find a running dsh web /sandrone/config');
    console.log(dim('\nIs DeepSeek Harness running, and is the plugin enabled?  ' +
      'Try: node tools/smoke.mjs <port>'));
    process.exit(1);
  }

  console.log(bold(`sandrone-fairy smoke @ 127.0.0.1:${port}`) + '\n');
  const base = `http://127.0.0.1:${port}/sandrone`;
  let failures = 0;
  const fail = () => { failures += 1; };

  // 1. config
  let cfg = null;
  try {
    cfg = await (await fetch(`${base}/config`, { signal: AbortSignal.timeout(4000) })).json();
    if (!report(!!cfg.parts, 'GET /sandrone/config', `splash=${cfg.parts?.splash} pet=${cfg.parts?.pet} voice=${cfg.parts?.voice}`)) fail();
  } catch (e) {
    report(false, 'GET /sandrone/config', String(e)); fail();
  }

  // 2. model
  try {
    const ping = await (await fetch(`${base}/ping`, { signal: AbortSignal.timeout(8000) })).json();
    if (!report(ping.ok === true, 'GET /sandrone/ping', `${ping.provider || '?'} / ${ping.model || '?'}`)) fail();
  } catch (e) {
    report(false, 'GET /sandrone/ping', String(e)); fail();
  }

  // 3. voice engine (cold start is slow: 16–40s, so only warn when it is not up yet)
  try {
    const v = await (await fetch(`${base}/voice`, { signal: AbortSignal.timeout(10000) })).json();
    const line = `up=${v.ok} python=${v.python || '?'} child=${v.child ?? 'none'}`;
    if (v.ok) report(true, 'GET /sandrone/voice', line);
    else {
      console.log(`${'\x1b[33mWARN\x1b[0m'}  GET /sandrone/voice  ${dim(line + '  (will start on first utterance)')}`);
    }
  } catch (e) {
    report(false, 'GET /sandrone/voice', String(e)); fail();
  }

  // 4. static asset
  try {
    const res = await fetch(`${base}/asset/figure.png`, { signal: AbortSignal.timeout(6000) });
    if (!report(res.ok && (res.headers.get('content-type') || '').includes('image'), 'GET /sandrone/asset/figure.png',
      `${res.status} ${res.headers.get('content-type') || ''}`)) fail();
  } catch (e) {
    report(false, 'GET /sandrone/asset/figure.png', String(e)); fail();
  }

  // 5. config write round-trip (restores the values it found)
  if (cfg) {
    try {
      const res = await fetch(`${base}/config`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ parts: cfg.parts, pet: cfg.pet }),
        signal: AbortSignal.timeout(5000),
      });
      const after = await res.json();
      if (!report(res.ok && after.pet?.corner === cfg.pet?.corner, 'POST /sandrone/config',
        `corner=${after.pet?.corner}`)) fail();
    } catch (e) {
      report(false, 'POST /sandrone/config', String(e)); fail();
    }
  }

  console.log('');
  if (failures === 0) {
    console.log(green('all good.'));
    process.exit(0);
  }
  console.log(red(`${failures} check(s) failed.`));
  process.exit(1);
}

main();
