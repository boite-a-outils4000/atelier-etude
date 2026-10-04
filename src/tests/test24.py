import asyncio, subprocess, time, os, re
from playwright.async_api import async_playwright
SITE = '/home/claude/whisper/site'; COURS = '/home/claude/outil/cours.pdf'; OUT = '/home/claude/outil/shots24'; os.makedirs(OUT, exist_ok=True)
R = []
def ok(name, cond, extra=''):
    R.append((name, bool(cond))); print(('OK  ' if cond else 'ÉCHEC ') + name, extra, flush=True)
T19 = open('/home/claude/outil/test19.py').read(); MOCK = re.search(r"MOCK = '''(.*?)'''", T19, re.S).group(1)
INIT = MOCK + '\nwindow.print = () => { window.__printed = (window.__printed || 0) + 1; };'
async def pdftext(page, name):
    await page.emulate_media(media='print'); path = f'{OUT}/{name}.pdf'
    await page.pdf(path=path, format='A4', print_background=True); await page.emulate_media(media='screen')
    return subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True).stdout
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8804', '--bind', '127.0.0.1'], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); await ctx.add_init_script(INIT)
            page = await ctx.new_page(); errs = []; page.on('pageerror', lambda e: errs.append(str(e))); ev = page.evaluate
            await page.goto('http://127.0.0.1:8804/'); await page.wait_for_timeout(1000); await ev('window.S=__atelier.S; 1')
            await page.set_input_files('#fileInput', COURS); await page.wait_for_selector('.page canvas'); await page.wait_for_timeout(800)
            await page.click('#quick'); await page.keyboard.type('Note de la page un'); await page.keyboard.press('Enter')
            await page.click('#addNote'); await page.keyboard.type('Secret perso'); await page.keyboard.press('Escape')
            await ev('S.doc.notes.at(-1).private = true; S.doc.notes.at(-1).tags = ["retenir"]; 1')
            await page.click('#viewer', position={'x': 40, 'y': 40}); await page.keyboard.press('ArrowRight'); await page.wait_for_timeout(800)
            await page.click('#quick'); await page.keyboard.type('Note de la page deux'); await page.keyboard.press('Enter'); await page.wait_for_timeout(300)
            await page.click('#expBtn'); await page.click('#ddExport [data-x="notes"]'); await page.wait_for_selector('#npGo')
            ok('fenêtre de choix', await ev('document.querySelectorAll("#npScope button").length') == 2)
            await page.click('#npGo'); await page.wait_for_timeout(600)
            t = await pdftext(page, 'tout')
            ok('toutes les notes, classées par page', all(x in t for x in ['Note de la page un', 'Note de la page deux', 'Secret perso', 'Page 1', 'Page 2', 'À retenir']) and t.index('page un') < t.index('page deux'), t[:300])
            await page.click('#expBtn'); await page.click('#ddExport [data-x="notes"]'); await page.wait_for_selector('#npGo')
            await page.click('#npScope [data-v="page"]'); await page.uncheck('#npPriv'); await page.click('#npGo'); await page.wait_for_timeout(600)
            t = await pdftext(page, 'page')
            ok('seulement la page affichée', 'page deux' in t and 'page un' not in t, t[:200])
            await ev('document.querySelector(".notes-list .note .more").click()'); await page.click('#ddNote [data-a="pdf"]'); await page.wait_for_timeout(600)
            t = await pdftext(page, 'une')
            ok('une seule note depuis ⋯', 'page deux' in t and 'page un' not in t and 'Note ·' in t)
            # sans les notes privées
            await page.click('#tabAll'); await page.click('#expBtn'); await page.click('#ddExport [data-x="notes"]'); await page.wait_for_selector('#npGo')
            await page.uncheck('#npPriv'); await page.click('#npGo'); await page.wait_for_timeout(600)
            t = await pdftext(page, 'sans-prive'); ok('sans les notes privées', 'Secret perso' not in t and 'page un' in t)
            # vidéo
            await page.click('#coursBtn'); await page.click('#vidItem'); await page.fill('#vidUrl', 'https://youtu.be/dQw4w9WgXcQ?t=90'); await page.click('#vidGo'); await page.wait_for_timeout(800)
            await page.click('#quick'); await page.keyboard.type('Idée vidéo'); await page.keyboard.press('Enter'); await page.wait_for_timeout(300)
            ok('export PDF disponible pour une vidéo', await ev('(document.getElementById("expBtn").click(), !!document.querySelector("#ddExport [data-x=notes]").offsetParent)'))
            await page.click('#ddExport [data-x="notes"]'); await page.click('#npGo'); await page.wait_for_timeout(600)
            t = await pdftext(page, 'video'); ok('vidéo : minutage et lien', 'Idée vidéo' in t and '1:30' in t and 'youtu.be/dQw4w9WgXcQ' in t, t[:300])
            # carnet
            await page.click('#coursBtn'); await page.click('#nbItem'); await page.wait_for_timeout(500)
            await page.click('#quick'); await page.keyboard.type('Première'); await page.keyboard.press('Enter'); await page.keyboard.type('Seconde'); await page.keyboard.press('Enter'); await page.wait_for_timeout(300)
            await page.click('#expBtn'); await page.click('#ddExport [data-x="notes"]'); await page.click('#npGo'); await page.wait_for_timeout(600)
            t = await pdftext(page, 'carnet'); ok('carnet : dans l\'ordre, sans « Page »', 'Première' in t and t.index('Première') < t.index('Seconde') and 'Page 1' not in t)
            ok('impression lancée à chaque fois', await ev('window.__printed') == 6, await ev('window.__printed'))
            ok('aucune erreur', not errs, errs[:3])
            await b.close()
    finally: srv.kill()
    print('\nRÉSUMÉ', sum(1 for _, c in R if c), '/', len(R))
asyncio.run(main())
