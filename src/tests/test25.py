import asyncio, subprocess, time, re
from playwright.async_api import async_playwright
T19 = open('/home/claude/outil/test19.py').read(); MOCK = re.search(r"MOCK = '''(.*?)'''", T19, re.S).group(1)
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8806', '--bind', '127.0.0.1'], cwd='/home/claude/whisper/site', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for ui in [1, 1.1, 1.25]:
            ctx = await b.new_context(viewport={'width': 1366, 'height': 650}); await ctx.add_init_script(MOCK + f';(()=>{{const p=JSON.parse(localStorage.getItem("etude.prefs")||"{{}}");p.ui={ui};localStorage.setItem("etude.prefs",JSON.stringify(p));}})();')
            pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto('http://127.0.0.1:8806/'); await pg.wait_for_timeout(900)
            for mode in ['pdf', 'vid', 'nofocus']:
                if mode == 'pdf':
                    await pg.set_input_files('#fileInput', '/home/claude/outil/cours.pdf'); await pg.wait_for_selector('.page canvas'); await pg.wait_for_timeout(600)
                if mode == 'vid':
                    await pg.click('#coursBtn'); await pg.click('#vidItem'); await pg.fill('#vidUrl', 'https://youtu.be/dQw4w9WgXcQ'); await pg.click('#vidGo'); await pg.wait_for_timeout(700)
                if mode != 'nofocus':
                    await pg.click('#addNote'); await pg.keyboard.type('T'); await pg.keyboard.press('Enter'); await pg.keyboard.type('texte ')
                else:
                    await pg.keyboard.press('Escape'); await pg.mouse.click(300, 300)
                await pg.click('#fmt [data-dd="ddBlock"]'); await pg.wait_for_timeout(300)
                r = await pg.evaluate('(() => { const m = document.getElementById("ddBlock"); const r = m.getBoundingClientRect(); const it = m.querySelector("[data-ins=def]").getBoundingClientRect(); return {open: m.classList.contains("open"), top: Math.round(r.top), bottom: Math.round(r.bottom), right: Math.round(r.right), item: [Math.round(it.x), Math.round(it.y)], vw: innerWidth, vh: innerHeight}; })()')
                n0 = await pg.evaluate('document.querySelectorAll(".notes-list .callout").length')
                try:
                    await pg.click('#ddBlock [data-ins="def"]', timeout=3000)
                except Exception as e: print('   click fail', str(e)[:80])
                await pg.wait_for_timeout(300)
                n1 = await pg.evaluate('document.querySelectorAll(".notes-list .callout").length')
                print(ui, mode, r, 'inserted' if n1 > n0 else 'NOT inserted', errs[:2])
            await ctx.close()
        await b.close()
    srv.kill()
asyncio.run(main())
