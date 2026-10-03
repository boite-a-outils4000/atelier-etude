import asyncio, subprocess, time
from playwright.async_api import async_playwright
exec(open('/home/claude/outil/test16.py').read().split('async def wait_for')[0])
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8794', '--bind', '127.0.0.1'], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--use-file-for-fake-audio-capture=' + FAKE])
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); await ctx.add_init_script(INIT); await ctx.grant_permissions(['microphone'], origin='http://127.0.0.1:8794')
        pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://127.0.0.1:8794/'); await pg.wait_for_timeout(1000)
        await pg.set_input_files('#fileInput', COURS); await pg.wait_for_timeout(1500)
        await pg.evaluate('window.__atelier.prefs.recSeen = true; Asr.ensure = async()=>{}; TQ.kick = async()=>{}')
        bad = 0
        for w in [1100, 1280, 1440, 1680]:
            for ui in [1, 1.1, 1.25]:
                for rec in [False, True]:
                    await pg.set_viewport_size({'width': w, 'height': 860})
                    await pg.evaluate(f'(() => {{ const P = window.__atelier.prefs; P.ui = {ui}; window.__atelier.savePrefs(); document.querySelector("#segUi [data-v=\\"{ui if ui != 1 else 1}\\"]").click(); }})()')
                    if rec: await pg.evaluate('Rec.start()')
                    await pg.wait_for_timeout(700)
                    r = await pg.evaluate('({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, help: Math.round(document.getElementById("helpBtn").getBoundingClientRect().right), cls: [...document.body.classList].filter(c=>c.startsWith("tb-")).join(","), lbl: getComputedStyle(document.querySelector("#recBtn .rt")).display })')
                    okk = r['sw'] <= r['cw'] and r['help'] <= r['cw']
                    bad += not okk
                    print('OK ' if okk else 'ÉCHEC', w, ui, 'rec' if rec else 'idle', r)
                    if rec: await pg.evaluate('Rec.stop()'); await pg.wait_for_timeout(600)
        await pg.screenshot(path='/home/claude/outil/shots16/7-1680.png')
        print('erreurs', errs, 'échecs', bad)
        await b.close()
    srv.kill()
asyncio.run(main())
