import asyncio, subprocess, time, os, json, base64
from playwright.async_api import async_playwright
SITE = '/home/claude/whisper/site'; IMG = ['/home/claude/outil/shots27/photo1.jpg', '/home/claude/outil/shots27/photo2.jpg']; OUT = '/home/claude/outil/shots29'; os.makedirs(OUT, exist_ok=True)
R = []
def ok(name, cond, extra=''):
    R.append((name, bool(cond))); print(('OK  ' if cond else 'ÉCHEC ') + name, extra, flush=True)
INIT = 'window.__noUnloadWarn=true; delete window.showOpenFilePicker; (()=>{try{const p=JSON.parse(localStorage.getItem("etude.prefs")||"{}");p.tourDone=true;localStorage.setItem("etude.prefs",JSON.stringify(p));}catch(e){}})();'
REQ = []; MODE = {'status': 200}
ANSWER = "# Le protectionnisme de Trump\n\n- Droits de douane **par pays**\n  - contraire au libre-échange → [[sidération]] des marchés\n- Retour au XIXe s.\n\n## Conséquences\n1. Inflation\n2. Guerre commerciale avec la Chine"
async def api(route):
    req = route.request; body = json.loads(req.post_data); REQ.append({'h': req.headers, 'b': body})
    if MODE['status'] != 200:
        return await route.fulfill(status=MODE['status'], content_type='application/json', headers={'Access-Control-Allow-Origin': '*'}, body=json.dumps({'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}}))
    await route.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin': '*'}, body=json.dumps({'content': [{'type': 'text', 'text': ANSWER}]}))
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8814', '--bind', '127.0.0.1'], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); await ctx.add_init_script(INIT)
            await ctx.route('https://api.anthropic.com/**', api)
            pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); ev = pg.evaluate
            await pg.goto('http://127.0.0.1:8814/'); await pg.wait_for_timeout(1000)
            await pg.click('#nbBtn2'); await pg.wait_for_timeout(500)
            await pg.click('#nbStage [data-nb=ocr]'); await pg.wait_for_selector('#ocrKey')
            ok('première fois : demande la clé API', True)
            await pg.fill('#ocrKey', 'pas une clé'); await pg.click('#ocrOk'); await pg.wait_for_timeout(200)
            ok('clé invalide refusée', await ev('!!document.getElementById("ocrKey")'))
            await pg.fill('#ocrKey', 'sk-ant-test-123')
            async with pg.expect_file_chooser() as fc:
                await pg.click('#ocrOk')
            await (await fc.value).set_files(IMG); await pg.wait_for_timeout(3000)
            notes = await ev('__atelier.S.doc.notes.map(n => ({ t: n.title, h: n.html }))')
            ok('deux photos → deux notes', len(notes) == 2, [n['t'] for n in notes])
            h = notes[0]['h'] if notes else ''
            ok('titre, listes, gras, sous-titre et liste numérotée', notes and notes[0]['t'] == 'Le protectionnisme de Trump' and '<ul>' in h and '<b>par pays</b>' in h and '<h3>Conséquences</h3>' in h and '<ol>' in h, h[:400])
            ok('mot incertain surligné avec « ? »', 'sidération ?' in h and 'background-color' in h)
            ok('photo d\'origine gardée dans la note', '<img src="data:image/jpeg' in h)
            r0 = REQ[0] if REQ else {'h': {}, 'b': {}}
            img = r0['b']['messages'][0]['content'][0]['source']
            raw = base64.b64decode(img['data']); 
            from PIL import Image; import io; w, hh = Image.open(io.BytesIO(raw)).size
            ok('requête : clé, accès navigateur, modèle, image JPEG réduite', r0['h'].get('x-api-key') == 'sk-ant-test-123' and r0['h'].get('anthropic-dangerous-direct-browser-access') == 'true' and r0['b']['model'] == 'claude-sonnet-5-5' and img['media_type'] == 'image/jpeg' and max(w, hh) <= 1568, [w, hh])
            await pg.screenshot(path=OUT + '/1-photo.png')
            ok('la clé n\'est pas dans les sauvegardes ni les préférences', 'sk-ant' not in await ev('JSON.stringify([...__atelier.S.docs.values()]) + localStorage.getItem("etude.prefs")'))
            MODE['status'] = 401
            await pg.click('#coursBtn'); await pg.click('#ocrItem'); await pg.wait_for_selector('#ocrKey')
            ok('la clé est préremplie la fois suivante', await ev('document.getElementById("ocrKey").value') == 'sk-ant-test-123')
            async with pg.expect_file_chooser() as fc:
                await pg.click('#ocrOk')
            await (await fc.value).set_files(IMG[:1]); await pg.wait_for_timeout(1500)
            t = await ev('document.getElementById("toastTxt").textContent')
            ok('clé refusée : message clair avec « Réglages »', 'clé refusée' in t and await ev('document.getElementById("toastAct").textContent') == 'Réglages', t)
            MODE['status'] = 200
            await pg.click('#addNote'); await pg.keyboard.type('x'); await pg.keyboard.press('Escape')
            await pg.click('#fmt [data-dd="ddBlock"]'); ok('« Insérer » : entrée photo', await ev('!!document.querySelector("#ddBlock [data-ins=ocr]").offsetParent'))
            await pg.keyboard.press('Escape')
            ok('aucune erreur', not errs, errs[:3])
            await b.close()
    finally: srv.kill()
    print('\nRÉSUMÉ', sum(1 for _, c in R if c), '/', len(R))
asyncio.run(main())
