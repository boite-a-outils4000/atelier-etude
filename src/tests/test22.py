import asyncio, subprocess, time, os, json, urllib.parse, re
from playwright.async_api import async_playwright
SITE = '/home/claude/whisper/site'; OUT = '/home/claude/outil/shots22'; os.makedirs(OUT, exist_ok=True)
R = []
def ok(name, cond, extra=''):
    R.append((name, bool(cond))); print(('OK  ' if cond else 'ÉCHEC ') + name, extra, flush=True)
INIT = 'window.__noUnloadWarn=true; (()=>{try{const p=JSON.parse(localStorage.getItem("etude.prefs")||"{}");p.tourDone=true;localStorage.setItem("etude.prefs",JSON.stringify(p));}catch(e){}})();'
SENT = []
async def lt(route):
    data = urllib.parse.parse_qs(route.request.post_data or ''); text = data.get('text', [''])[0]; SENT.append(text)
    m = []
    for bad, good, msg in [('élève', 'élèves', 'Accord du nom avec « Les ».'), ('arrivé', 'arrivés', 'Le participe passé s\'accorde avec le sujet.')]:
        mm = re.search(r'(?<!\w)' + bad + r'(?!\w)', text); i = mm.start() if mm else -1
        if i >= 0: m.append({'offset': i, 'length': len(bad), 'message': msg, 'replacements': [{'value': good}], 'context': {}, 'rule': {'category': {'name': 'Grammaire'}}})
    await route.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin': '*'}, body=json.dumps({'matches': m}))
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8802', '--bind', '127.0.0.1'], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); await ctx.add_init_script(INIT)
            await ctx.route('https://api.languagetool.org/**', lt)
            page = await ctx.new_page(); errs = []
            page.on('pageerror', lambda e: errs.append('PAGEERROR ' + str(e))); page.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'favicon' not in m.text else None)
            ev = page.evaluate
            await page.goto('http://127.0.0.1:8802/'); await page.wait_for_timeout(1200); await ev('window.S=__atelier.S; window.prefs=__atelier.prefs; 1')
            await page.click('#nbBtn2'); await page.wait_for_timeout(600)
            q = '#quick'
            await page.click(q); await page.keyboard.type('A --> B, x => y, a <-> b, c <=> d, e <-- f, g -> h, x <= 5')
            v = await ev('document.getElementById("quick").value')
            ok('flèches dans la note rapide', v == 'A → B, x ⇒ y, a ↔ b, c ⇔ d, e ← f, g → h, x <= 5', v)
            await ev('document.getElementById("quick").value = ""'); await page.keyboard.type('a ->'); await page.keyboard.press('Backspace')
            ok('⌫ remet les signes tapés', await ev('document.getElementById("quick").value') == 'a ->')
            await ev('document.getElementById("quick").value = ""; 1')
            await page.click('#addNote'); await page.keyboard.type('Cause --> effet'); await page.keyboard.press('Enter'); await page.keyboard.type('Révolution => crise <-> réformes')
            t = await ev('({ t: document.activeElement.closest(".note").querySelector(".note-title").value, b: document.activeElement.textContent })')
            ok('flèches dans le titre et le texte d\'une note', t['t'] == 'Cause → effet' and t['b'] == 'Révolution ⇒ crise ↔ réformes', t)
            await page.keyboard.press('Escape'); await page.wait_for_timeout(300)
            ok('enregistré', '⇒' in await ev('S.doc.notes.at(-1).html') and await ev('S.doc.notes.at(-1).title') == 'Cause → effet')
            await ev('prefs.arrowsOn = false; 1'); await page.click(q); await page.keyboard.type('sans -->')
            ok('désactivable', await ev('document.getElementById("quick").value') == 'sans -->')
            await ev('prefs.arrowsOn = true; document.getElementById("quick").value = ""; 1'); await page.keyboard.press('Escape')
            ok('correcteur de Chrome actif sur titres, notes rapides et texte', await ev('document.getElementById("quick").spellcheck && document.querySelector(".note-title").spellcheck && document.querySelector(".note .body").spellcheck'))
            # grammaire
            await page.click('#addNote'); await page.keyboard.type('Les élève'); await page.keyboard.press('Enter'); await page.keyboard.type('sont arrivé hier.'); await page.keyboard.press('Enter'); await page.keyboard.type('Deuxième ligne')
            await page.keyboard.press('Alt+KeyG'); await page.wait_for_timeout(500)
            ok('⌥G : demande d\'accord avant d\'envoyer', 'LanguageTool' in await ev('document.querySelector(".modal").textContent'))
            await page.click('#ltOk'); await page.wait_for_selector('.lt-item'); await page.wait_for_timeout(300)
            ok('texte envoyé : uniquement cette note, lignes séparées', len(SENT) == 1 and SENT[0] == 'Les élève\n\nsont arrivé hier.\nDeuxième ligne', repr(SENT[0] if SENT else ''))
            ok('deux corrections proposées', await ev('document.querySelectorAll(".lt-item").length') == 2)
            await page.screenshot(path=OUT + '/1-grammaire.png')
            await page.click('.lt-item[data-i="0"] [data-s="0"]'); await page.wait_for_timeout(200)
            await page.click('.lt-item[data-i="1"] [data-s="0"]'); await page.wait_for_timeout(500)
            n = await ev('({ title: S.doc.notes.at(-1).title, html: S.doc.notes.at(-1).html, modal: !!document.querySelector(".modal") })')
            ok('corrections appliquées et enregistrées', n['title'] == 'Les élèves' and 'sont arrivés hier.' in n['html'] and 'Deuxième ligne' in n['html'] and not n['modal'], n)
            await ev('document.querySelector(".note:last-of-type .more, .notes-list .note:last-child .more").click()'); await page.wait_for_timeout(200)
            ok('menu ⋯ : « Vérifier orthographe et grammaire »', await ev('!!document.querySelector("#ddNote [data-a=lt]")'))
            await page.click('#ddNote [data-a=lt]'); await page.wait_for_timeout(800)
            await page.wait_for_timeout(600)
            ok('plus rien à corriger', 'Aucune faute' in await ev('document.getElementById("toastTxt").textContent') and len(SENT) == 2, [await ev('document.getElementById("toastTxt").textContent'), len(SENT), SENT[-1][:40]])
            ok('aucune erreur JavaScript', not errs, errs[:5])
            await b.close()
    finally: srv.kill()
    print('\nRÉSUMÉ', sum(1 for _, c in R if c), '/', len(R))
asyncio.run(main())
