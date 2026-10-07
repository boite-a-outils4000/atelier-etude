import asyncio, subprocess, time, os
from playwright.async_api import async_playwright
SITE = '/home/claude/whisper/site'; COURS = '/home/claude/outil/cours.pdf'; OUT = '/home/claude/outil/shots28'; os.makedirs(OUT, exist_ok=True)
R = []
def ok(name, cond, extra=''):
    R.append((name, bool(cond))); print(('OK  ' if cond else 'ÉCHEC ') + name, extra, flush=True)
INIT = 'window.__noUnloadWarn=true; delete window.showOpenFilePicker; (()=>{try{const p=JSON.parse(localStorage.getItem("etude.prefs")||"{}");p.tourDone=true;localStorage.setItem("etude.prefs",JSON.stringify(p));}catch(e){}})();'
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8812', '--bind', '127.0.0.1'], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); await ctx.add_init_script(INIT)
            pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); ev = pg.evaluate
            await pg.goto('http://127.0.0.1:8812/'); await pg.wait_for_timeout(1000)
            await pg.click('#nbBtn2'); await pg.wait_for_timeout(500)
            await pg.click('#quick'); await pg.keyboard.type('Avant le PDF'); await pg.keyboard.press('Enter')
            ok('bouton « Afficher un PDF à côté »', await ev('!!document.querySelector("#nbStage [data-nb=ref]")'))
            async with pg.expect_file_chooser() as fc:
                await pg.click('#nbStage [data-nb=ref]')
            await (await fc.value).set_files(COURS); await pg.wait_for_timeout(2500)
            st = await ev('({ ref: !document.getElementById("refpane").classList.contains("hidden"), viewer: getComputedStyle(document.getElementById("viewer")).display, cls: document.body.classList.contains("nb-ref"), left: Math.round(document.querySelector(".pdfcol").getBoundingClientRect().width), canv: document.querySelectorAll("#refPages canvas").length, kind: __atelier.S.doc.kind, refName: __atelier.S.doc.refName })')
            ok('le PDF s\'affiche à gauche, en grand, le carnet reste ouvert', st['ref'] and st['viewer'] == 'none' and st['cls'] and st['left'] > 700 and st['canv'] > 0 and st['kind'] == 'blank', st)
            await pg.click('#quick'); await pg.keyboard.type('Pendant le PDF'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(300)
            ok('on écrit toujours dans le carnet', await ev('__atelier.S.doc.notes.length') == 2 and await ev('__atelier.S.doc.kind') == 'blank')
            await pg.screenshot(path=OUT + '/1-pdf-a-cote.png')
            await pg.click('#refClose'); await pg.wait_for_timeout(600)
            st = await ev('({ ref: !document.getElementById("refpane").classList.contains("hidden"), cls: document.body.classList.contains("nb-ref"), stage: !!document.getElementById("nbStage").offsetParent, reopen: !!document.querySelector("#nbStage [data-nb=reopen]"), notes: __atelier.S.doc.notes.length })')
            ok('✕ retire le PDF ; les notes restent dans le carnet', not st['ref'] and not st['cls'] and st['stage'] and not st['reopen'] and st['notes'] == 2, st)
            async with pg.expect_file_chooser() as fc:
                await pg.click('#nbStage [data-nb=ref]')
            await (await fc.value).set_files(COURS); await pg.wait_for_timeout(2000)
            await pg.click('#coursBtn'); await pg.click('#nbItem'); await pg.wait_for_timeout(800)
            ok('autre carnet : le PDF reste à côté', await ev('document.body.classList.contains("nb-ref")'))
            await ev('[...document.querySelectorAll(".dtab")].find(x => x.textContent.includes("Cours du")).click()'); await pg.wait_for_timeout(600)
            await pg.click('#refClose'); await pg.wait_for_timeout(400)
            ok('aucune erreur', not errs, errs[:3])
            await b.close()
    finally: srv.kill()
    print('\nRÉSUMÉ', sum(1 for _, c in R if c), '/', len(R))
asyncio.run(main())
