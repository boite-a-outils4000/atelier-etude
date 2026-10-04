import asyncio, subprocess, time, os, re
from playwright.async_api import async_playwright
SITE = '/home/claude/whisper/site'; COURS = '/home/claude/outil/cours.pdf'; FAKE = '/home/claude/whisper/audio/fake48.wav'; OUT = '/home/claude/outil/shots21'; os.makedirs(OUT, exist_ok=True)
R = []
def ok(name, cond, extra=''):
    R.append((name, bool(cond))); print(('OK  ' if cond else 'ÉCHEC ') + name, extra, flush=True)
T19 = open('/home/claude/outil/test19.py').read(); MOCK = re.search(r"MOCK = '''(.*?)'''", T19, re.S).group(1)
T16 = open('/home/claude/outil/test16.py').read(); ASRC = re.search(r"INIT = '''(.*?)'''", T16, re.S).group(1)
async def wait_for(ev, expr, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if await ev(expr): return True
        await asyncio.sleep(0.5)
    return False
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8799', '--bind', '127.0.0.1'], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--use-file-for-fake-audio-capture=' + FAKE])
            ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); await ctx.add_init_script(MOCK + '\n' + ASRC)
            await ctx.grant_permissions(['microphone'], origin='http://127.0.0.1:8799')
            page = await ctx.new_page(); errs = []
            page.on('pageerror', lambda e: errs.append('PAGEERROR ' + str(e))); page.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'favicon' not in m.text else None)
            ev = page.evaluate
            await page.goto('http://127.0.0.1:8799/'); await page.wait_for_timeout(1200); await ev('window.S=__atelier.S; window.prefs=__atelier.prefs; prefs.recModel="rapide"; 1')
            await page.set_input_files('#fileInput', COURS); await page.wait_for_selector('.page canvas'); await page.wait_for_timeout(1000)
            ok('boutons Dicter visibles', await ev('!!document.getElementById("dictBtn2").offsetParent && !!document.getElementById("dictBtn").offsetParent'))
            # 1. dans une note
            await page.click('#addNote'); await page.keyboard.type('Dictée'); await page.keyboard.press('Enter'); await page.keyboard.type('Début :')
            await page.keyboard.press('Alt+KeyV'); await page.wait_for_timeout(800)
            ok('⌥V lance la dictée (pastille)', await ev('Dict.on && !!document.getElementById("dictPill")'))
            await page.screenshot(path=OUT + '/1-ecoute.png')
            done = await wait_for(ev, '!Dict.on && !Dict.busy && !document.getElementById("dictPill")', 200)
            body = await ev('S.doc.notes.at(-1).html')
            ok('arrêt automatique après un silence, texte inséré dans la note', done and 'Début :' in body[:20] and len(re.sub('<[^>]+>', '', body)) > 30, body[:200])
            # 2. annuler
            await page.keyboard.press('Escape'); await page.click('#viewer', position={'x': 40, 'y': 40})
            n0 = await ev('S.doc.notes.length')
            await page.click('#dictBtn2'); await page.wait_for_timeout(1200); await page.keyboard.press('Escape'); await page.wait_for_timeout(500)
            ok('Échap annule la dictée', await ev('!Dict.on && !Dict.busy') and await ev('S.doc.notes.length') == n0)
            # 3. sans note ouverte : nouvelle note
            await page.click('#viewer', position={'x': 40, 'y': 40}); await page.keyboard.press('Alt+KeyV'); await wait_for(ev, 'Dict.on', 20)
            await wait_for(ev, '!Dict.on && !Dict.busy', 200); await page.wait_for_timeout(600)
            ok('sans note ouverte : la dictée devient une nouvelle note', await ev('S.doc.notes.length') == n0 + 1, await ev('S.doc.notes.at(-1).title || S.doc.notes.at(-1).html'))
            # 4. vidéo, tout dans une note
            await page.click('#coursBtn'); await page.click('#vidItem'); await page.fill('#vidUrl', 'https://youtu.be/dQw4w9WgXcQ?t=90'); await page.click('#vidGo'); await page.wait_for_timeout(900)
            await page.check('#vidFlow'); await page.wait_for_timeout(200)
            ok('option « Tout dans une note »', await ev('prefs.vidFlow === true && document.querySelector(".vb-tc").textContent.includes("Écrire ici")'))
            await page.click('.vb-play'); await page.wait_for_timeout(1500)
            await page.click('#quick'); await page.keyboard.type('Premier passage'); await page.keyboard.press('Enter'); await page.wait_for_timeout(1600)
            await page.click('#quick'); await page.keyboard.type('Deuxième passage'); await page.keyboard.press('Enter'); await page.wait_for_timeout(500)
            h = await ev('({ n: S.doc.notes.length, html: S.doc.notes[0] && S.doc.notes[0].html })')
            ok('deux passages dans la même note, minutage entre parenthèses', h['n'] == 1 and h['html'].count('class="tc"') == 2 and re.search(r'Premier passage \(<span class="tc"[^>]*>1:3\d</span>\)', h['html']) is not None, h)
            await page.wait_for_timeout(500)
            await page.click('.note .body'); await page.keyboard.press('End'); await page.keyboard.type(' ajout'); await page.keyboard.press('Alt+KeyT'); await page.wait_for_timeout(400)
            ok('⌥T dans la note : minutage entre parenthèses', re.search(r'ajout \(<span class="tc"', await ev('document.querySelector(".note .body").innerHTML')) is not None, (await ev('document.querySelector(".note .body").innerHTML'))[-160:])
            await page.keyboard.press('Escape'); await page.wait_for_timeout(300)
            await page.click('#vidStage .vb-time'); await page.keyboard.press('Alt+KeyV'); await wait_for(ev, 'Dict.on', 20)
            await wait_for(ev, '!Dict.on && !Dict.busy', 200); await page.wait_for_timeout(800)
            h2 = await ev('({ n: S.doc.notes.length, tc: (S.doc.notes[0].html.match(/class="tc"/g) || []).length })')
            ok('dictée sur la vidéo : ajoutée à la suite avec le minutage', h2['n'] == 1 and h2['tc'] == 4, h2)
            await page.screenshot(path=OUT + '/2-video-flow.png')
            await page.uncheck('#vidFlow'); await page.click('#quick'); await page.keyboard.type('Nouvelle idée'); await page.keyboard.press('Enter'); await page.wait_for_timeout(400)
            ok('option désactivée : une note par passage', await ev('S.doc.notes.length') == 2)
            ok('aucune erreur JavaScript', not errs, errs[:5])
            await b.close()
    finally: srv.kill()
    print('\nRÉSUMÉ', sum(1 for _, c in R if c), '/', len(R))
asyncio.run(main())
