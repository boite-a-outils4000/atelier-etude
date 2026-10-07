import asyncio, subprocess, time, json, os
from playwright.async_api import async_playwright
SITE = '/home/claude/whisper/site'; COURS = '/home/claude/outil/cours.pdf'; QCM = '/home/claude/outil/QCM - DAP séance 1.json'; TMP = '/home/claude/outil/shots27'; os.makedirs(TMP, exist_ok=True)
R = []
def ok(name, cond, extra=''):
    R.append((name, bool(cond))); print(('OK  ' if cond else 'ÉCHEC ') + name, extra, flush=True)
INIT = 'window.__noUnloadWarn=true; (()=>{try{const p=JSON.parse(localStorage.getItem("etude.prefs")||"{}");p.tourDone=true;localStorage.setItem("etude.prefs",JSON.stringify(p));}catch(e){}})();'
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8809', '--bind', '127.0.0.1'], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx = await b.new_context(accept_downloads=True); await ctx.add_init_script(INIT); A = await ctx.new_page()
            await A.goto('http://127.0.0.1:8809/'); await A.wait_for_timeout(1000)
            await A.set_input_files('#fileInput', COURS); await A.wait_for_selector('.page canvas'); await A.wait_for_timeout(500)
            await A.click('#quick'); await A.keyboard.type('Note à transférer'); await A.keyboard.press('Enter'); await A.wait_for_timeout(500)
            async with A.expect_download() as d:
                await A.click('#coursBtn'); await A.click('#ddCours [data-x="json"]')
            path = TMP + '/sauvegarde.json'; await (await d.value).save_as(path)
            ctx2 = await b.new_context(); await ctx2.add_init_script(INIT); B = await ctx2.new_page(); errs = []; B.on('pageerror', lambda e: errs.append(str(e)))
            await B.goto('http://127.0.0.1:8809/'); await B.wait_for_timeout(1000)
            ok('le sélecteur « Ouvrir » accepte les .json', '.json' in await B.evaluate('document.getElementById("fileInput").accept'))
            await B.set_input_files('#fileInput', path); await B.wait_for_timeout(1000)
            ok('sauvegarde .json ouverte depuis « Ouvrir »', 'importé' in await B.evaluate('document.getElementById("toastTxt").textContent') and await B.evaluate('document.querySelectorAll("#recentList .lib-item").length') == 1, await B.evaluate('document.getElementById("toastTxt").textContent'))
            await B.set_input_files('#fileInput', COURS); await B.wait_for_selector('.page canvas'); await B.wait_for_timeout(600)
            ok('le PDF retrouve la note importée', await B.evaluate('__atelier.S.doc.notes.some(n => n.title === "Note à transférer")'))
            await B.set_input_files('#fileInput', QCM); await B.wait_for_timeout(1000)
            await B.wait_for_timeout(800); ok('fichier de QCM ouvert depuis « Ouvrir »', await B.evaluate('(__atelier.S.doc.quiz || []).length') > 0 or bool(await B.evaluate('!!document.querySelector(".modal")')), await B.evaluate('document.getElementById("toastTxt").textContent'))
            ok('aucune erreur', not errs, errs[:3])
            await b.close()
    finally: srv.kill()
    print('\nRÉSUMÉ', sum(1 for _, c in R if c), '/', len(R))
asyncio.run(main())
