import asyncio, subprocess, time, os
from playwright.async_api import async_playwright
SITE = '/home/claude/whisper/site'; OUT = '/home/claude/outil/shots23'; os.makedirs(OUT, exist_ok=True)
R = []
def ok(name, cond, extra=''):
    R.append((name, bool(cond))); print(('OK  ' if cond else 'ÉCHEC ') + name, extra, flush=True)
INIT = 'window.__noUnloadWarn=true; (()=>{try{const p=JSON.parse(localStorage.getItem("etude.prefs")||"{}");p.tourDone=true;localStorage.setItem("etude.prefs",JSON.stringify(p));}catch(e){}})();'
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8803', '--bind', '127.0.0.1'], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); await ctx.add_init_script(INIT)
            page = await ctx.new_page(); errs = []; page.on('pageerror', lambda e: errs.append(str(e))); ev = page.evaluate
            await page.goto('http://127.0.0.1:8803/'); await page.wait_for_timeout(1000)
            await page.click('#nbBtn2'); await page.wait_for_timeout(500)
            await page.click('#addNote'); await page.keyboard.type('Texte long'); await page.keyboard.press('Enter')
            await page.keyboard.type("La révolution industrielle transforme profondément la société belge au dix-neuvième siècle : les campagnes se vident, les villes grandissent et une nouvelle classe ouvrière apparaît dans les bassins houillers de Wallonie.")
            await page.keyboard.press('Escape')
            ok('par défaut : aligné à gauche', await ev('getComputedStyle(document.querySelector(".note .body")).textAlign') in ('start', 'left'))
            await page.click('#viewBtn'); await page.click('#segAlign [data-v="justify"]'); await page.wait_for_timeout(300)
            st = await ev('({ a: getComputedStyle(document.querySelector(".note .body")).textAlign, h: getComputedStyle(document.querySelector(".note .body")).hyphens })')
            ok('Justifié : texte justifié avec césure', st['a'] == 'justify' and st['h'] == 'auto', st)
            await page.screenshot(path=OUT + '/1-justifie.png')
            await page.reload(); await page.wait_for_timeout(1200)
            ok('réglage gardé après rechargement', await ev('document.body.classList.contains("justify") && document.querySelector("#segAlign [data-v=justify]").classList.contains("on")'))
            ok('aucune erreur', not errs, errs[:3])
            await b.close()
    finally: srv.kill()
    print('\nRÉSUMÉ', sum(1 for _, c in R if c), '/', len(R))
asyncio.run(main())
