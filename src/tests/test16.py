import asyncio, os, json, subprocess, time
from playwright.async_api import async_playwright
SITE = '/home/claude/whisper/site'; COURS = '/home/claude/outil/cours.pdf'; FAKE = '/home/claude/whisper/audio/fake48.wav'; WEBM = '/home/claude/whisper/audio/cours.webm'
OUT = '/home/claude/outil/shots16'; os.makedirs(OUT, exist_ok=True)
R = []
def ok(name, cond, extra=''):
    R.append((name, bool(cond))); print(('OK  ' if cond else 'ÉCHEC ') + name, extra, flush=True)
INIT = '''window.__noUnloadWarn=true;
(()=>{try{const p=JSON.parse(localStorage.getItem("etude.prefs")||"{}");p.tourDone=true;localStorage.setItem("etude.prefs",JSON.stringify(p));}catch(e){}})();
(()=>{const o=location.origin; const m={label:'Rapide',model:'Xenova/whisper-base',cpu:'q8',size:{cpu:'80 Mo'},d:'test'};
window.ATELIER_ASR={lib:o+'/lib/transformers.min.js',remoteHost:o+'/models/',remotePathTemplate:'{model}/',wasmPaths:o+'/lib/',models:{rapide:m,equilibre:m,precis:m}};})();'''
async def wait_for(ev, expr, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if await ev(expr): return True
        await asyncio.sleep(1)
    return False
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8790', '--bind', '127.0.0.1'], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--use-file-for-fake-audio-capture=' + FAKE, '--autoplay-policy=no-user-gesture-required'])
            ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, accept_downloads=True); await ctx.add_init_script(INIT)
            await ctx.grant_permissions(['microphone', 'clipboard-read', 'clipboard-write'], origin='http://127.0.0.1:8790')
            page = await ctx.new_page(); errs = []
            page.on('pageerror', lambda e: errs.append('PAGEERROR ' + str(e)))
            page.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'favicon' not in m.text else None)
            ev = page.evaluate
            await page.goto('http://127.0.0.1:8790/'); await page.wait_for_timeout(1200); await ev('window.S=__atelier.S; window.renderNotes=__atelier.renderNotes; window.prefs=__atelier.prefs; window.savePrefs=__atelier.savePrefs; 1')
            await page.set_input_files('#fileInput', COURS); await page.wait_for_selector('.page canvas'); await page.wait_for_timeout(1200)
            ok('bouton Enregistrer visible, onglet Transcription caché', await ev('!!document.getElementById("recBtn").offsetParent && document.getElementById("tabTrans").classList.contains("hidden")'))
            # première fois : fenêtre de réglages
            await page.click('#recBtn'); await page.wait_for_selector('.modal'); await page.wait_for_timeout(400)
            mt = await ev('document.querySelector(".modal-h h3").textContent')
            nq = await ev('document.querySelectorAll(".qopt").length')
            ok('première fois : fenêtre « Enregistrer et transcrire »', 'Enregistrer et transcrire' in mt and nq == 3, mt)
            await page.screenshot(path=OUT + '/1-reglages.png')
            await ev('window.Rec.partSec = 12')
            await page.click('#rqGo'); await page.wait_for_timeout(1500)
            ok('enregistrement démarré', await ev('Rec.on && document.getElementById("recBtn").classList.contains("rec") && document.body.classList.contains("recording")'))
            ok('onglet Transcription apparu', await ev('!document.getElementById("tabTrans").classList.contains("hidden")'))
            await page.wait_for_timeout(5000)
            await page.click('#quick'); await page.keyboard.type('Cockerill à Seraing'); await page.keyboard.press('Enter'); await page.wait_for_timeout(400)
            await page.keyboard.press('Escape'); await page.click('#viewer'); await page.keyboard.press('ArrowRight'); await page.wait_for_timeout(1500)
            ok('note reliée à l\'enregistrement (bouton ▶)', await wait_for(ev, '!!document.querySelector(".note .recb") || (S.view="all", renderNotes(), !!document.querySelector(".note .recb"))', 10))
            rb = await ev('(document.querySelector(".note .recb")||{}).textContent')
            print('   badge :', rb)
            await page.screenshot(path=OUT + '/2-pendant.png')
            ok('niveau du micro affiché', await ev('Rec.level > -60'), await ev('Rec.level'))
            # transcription en direct
            got = await wait_for(ev, 'Rec.r && Rec.r.segs.length > 0', 150)
            ok('transcription en direct pendant l\'enregistrement', got, await ev('Rec.r && Rec.r.segs.slice(0,2)'))
            await wait_for(ev, 'Rec.samples/16000 > 30', 60)
            ok('parties de 12 s créées (rotation)', await ev('Rec.r.parts.length >= 2'), await ev('Rec.r.parts.length'))
            ok('page suivie dans l\'enregistrement', await ev('Rec.r.pages.length >= 2'), await ev('JSON.stringify(Rec.r.pages)'))
            # pause / reprise
            await ev('Rec.pause()'); s0 = await ev('Rec.samples'); await page.wait_for_timeout(2000); s1 = await ev('Rec.samples')
            ok('pause : le son n\'avance plus', s0 == s1 and await ev('document.getElementById("recBtn").classList.contains("paused")'))
            await ev('Rec.resume()'); await page.wait_for_timeout(2500)
            ok('reprise', await ev('Rec.samples') > s1 and await ev('Rec.r.spans.length === 2'))
            await page.keyboard.press('Alt+KeyM'); await page.wait_for_timeout(2500)
            ok('⌥M arrête l\'enregistrement', await ev('!Rec.on && !document.body.classList.contains("recording")'))
            done = await wait_for(ev, 'TQ.list.length === 0 && !TQ.running', 240)
            ok('transcription terminée après l\'arrêt', done, await ev('TQ.list.length'))
            info = await ev('(() => { const r = S.doc.recs[0]; return { n: r.segs.length, dur: r.dur, parts: r.parts.map(p=>[p.at.toFixed(1), p.dur.toFixed(1)]), text: r.segs.map(s=>s.t).join(" ") }; })()')
            print('   transcription :', json.dumps(info, ensure_ascii=False)[:900])
            ok('texte reconnu (mots du cours)', any(w in info['text'].lower() for w in ['révolution', 'belgique', 'industri', 'siècle', 'ouvrier']), '')
            # panneau
            await page.click('#tabTrans'); await page.wait_for_timeout(600)
            ok('panneau Transcription : segments et note intercalée', await ev('document.querySelectorAll(".tseg").length > 2 && document.querySelectorAll(".tnote").length >= 1'), await ev('[document.querySelectorAll(".tseg").length, document.querySelectorAll(".tnote").length, document.querySelectorAll(".tr-page").length]'))
            await page.screenshot(path=OUT + '/3-transcription.png')
            # lecture à partir d'un passage (dans la 2e partie)
            idx = await ev('(() => { const r=S.doc.recs[0]; const p=r.parts[1]; const segs=[...document.querySelectorAll(".tseg")]; const i=segs.findIndex(x=>+x.dataset.a > p.at+1); return i; })()')
            if idx < 0: idx = 0
            await ev(f'document.querySelectorAll(".tseg")[{idx}].querySelector(".tt").click()'); await page.wait_for_timeout(2500)
            pl = await ev('({ playing: !Player.el.paused, t: Player.time(), a: +document.querySelectorAll(".tseg")[%d].dataset.a, part: Player.p.i, bar: !document.getElementById("pbar").classList.contains("hidden"), mark: !!document.querySelector(".tseg.playing") })' % idx)
            ok('lecture à partir d\'un passage (seek dans une partie)', pl['playing'] and pl['bar'] and abs(pl['t'] - pl['a'] - 2.5) < 2.5, pl)
            ok('passage en cours de lecture surligné', pl['mark'])
            await page.screenshot(path=OUT + '/4-lecture.png')
            await page.click('.pb-rate'); ok('vitesse 1,25×', await ev('Player.el.playbackRate === 1.25'))
            await page.click('.pb-back'); await page.wait_for_timeout(800)
            # passage de partie en partie
            await ev('Player.play(Player.d, Player.r, Player.r.parts[0].dur - 1)'); await page.wait_for_timeout(3500)
            ok('enchaînement automatique sur la partie suivante', await ev('Player.p.i >= 1 && !Player.el.paused'), await ev('[Player.p.i, Player.time()]'))
            await page.click('.pb-x')
            # + : passage vers une note
            n0 = await ev('S.doc.notes.length')
            await ev('document.querySelector(".tseg .tadd").click()'); await page.wait_for_timeout(700)
            ok('« + » : passage copié dans une nouvelle note', await ev('S.doc.notes.length') == n0 + 1 and await ev('S.view === "page" && !!document.querySelector(".note blockquote")'))
            # bouton ▶ de la note
            await page.click('#tabAll'); await page.wait_for_timeout(400)
            await ev('document.querySelector(".note .recb").click()'); await page.wait_for_timeout(2000)
            ok('▶ d\'une note : réécoute quelques secondes avant', await ev('!Player.el.paused && Player.time() < 12'), await ev('Player.time()'))
            await ev('Player.close()')
            # recherche dans la transcription
            await page.click('#tabTrans'); await page.fill('#noteSearch', 'Belgique'); await page.wait_for_timeout(600)
            ok('recherche dans la transcription', await ev('document.querySelectorAll(".tseg mark").length >= 1 || document.querySelector(".tr-list .empty")'))
            await page.fill('#noteSearch', ''); await page.wait_for_timeout(400)
            # Envoyer à Claude
            md = await ev('ToClaude.build(S.doc, {hl:true, images:false, peers:false, trans:true, since:0}).then(r=>r.md)')
            ok('« Envoyer à Claude » inclut la transcription', 'Transcription du cours oral' in md and '#### Page' in md)
            # sauvegarde JSON : transcription incluse, son exclu
            ok('sauvegarde : transcription dans le document', await ev('JSON.stringify(S.doc).includes("segs") && !JSON.stringify(S.doc).includes("blob")'))
            # import d'un fichier audio
            await page.set_input_files('#audioInput', WEBM); await page.wait_for_timeout(500)
            done2 = await wait_for(ev, 'S.doc.recs.length === 2 && S.doc.recs[1].segs.length > 0 && TQ.list.length === 0 && !TQ.running', 240)
            ok('fichier audio importé et transcrit', done2, await ev('S.doc.recs[1] && [S.doc.recs[1].dur, S.doc.recs[1].segs.length]'))
            ok('sélecteur des enregistrements', await ev('!!document.querySelector(".tr-sel") && document.querySelector(".tr-sel").options.length === 2'))
            await page.screenshot(path=OUT + '/5-fichier.png')
            # mode « après le cours » + fermeture brutale → reprise
            await ev('prefs.recLive = false; savePrefs()')
            await ev('Rec.start()'); await page.wait_for_timeout(30000)
            ok('après le cours : rien n\'est transcrit pendant l\'enregistrement', await ev('Rec.r.segs.length === 0 && TQ.list.length > 0'), await ev('TQ.list.length'))
            await page.wait_for_timeout(1500)
            await page.reload(); await page.wait_for_timeout(2500); await ev('window.S=__atelier.S; window.renderNotes=__atelier.renderNotes; window.prefs=__atelier.prefs; window.savePrefs=__atelier.savePrefs; 1')
            st = await ev('(() => { const d=[...S.docs.values()].find(d=>d.recs&&d.recs.length); return { toast: document.getElementById("toastTxt").textContent, jobs: TQ.list.length, status: d.recs[2] && d.recs[2].status, hold: TQ.hold, doc: !!S.doc }; })()')
            ok('après fermeture : transcription en attente proposée', st['jobs'] > 0 and st['status'] == 'cut' and st['hold'], st)
            await ev('TQ.hold = false; TQ.kick()')
            done3 = await wait_for(ev, 'TQ.list.length === 0 && !TQ.running', 240)
            ok('reprise de la transcription après fermeture', done3 and await ev('[...S.docs.values()].find(d=>d.recs&&d.recs.length).recs[2].segs.length > 0'))
            if not await ev('!!S.doc'):
                await page.click('#recentList .lib-item'); await page.wait_for_timeout(2500)
                if not await ev('!!S.doc'):
                    await page.set_input_files('#fileInput', COURS); await page.wait_for_timeout(2000)
            ok('cours rouvert', await ev('!!S.doc && S.doc.recs.length === 3'))
            # suppression
            await page.click('#tabTrans'); await page.wait_for_timeout(300)
            await ev('Trans.sel = S.doc.recs[2].id; Trans.render()')
            await page.click('.tr-more'); await page.click('#ddTr [data-t="del"]'); await page.click('#trDel'); await page.wait_for_timeout(800)
            left = await ev('AStore.keys("chunks").then(k => k.filter(x => x.startsWith(S.doc.recs.length === 2 ? "" : "zz")).length)')
            ok('suppression d\'un enregistrement', await ev('S.doc.recs.length === 2'))
            # largeur 1280 pendant l'enregistrement
            await page.set_viewport_size({'width': 1280, 'height': 800}); await ev('Rec.start()'); await page.wait_for_timeout(1500)
            w = await ev('({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})')
            ok('1280 px pendant l\'enregistrement : pas de débordement', w['sw'] <= w['cw'], w)
            await page.screenshot(path=OUT + '/6-1280.png')
            await ev('Rec.stop()'); await page.wait_for_timeout(1500)
            bad = [e for e in errs if 'net::ERR' not in e]
            ok('aucune erreur JavaScript', not bad, bad[:5])
            await b.close()
    finally:
        srv.kill()
    print('\nRÉSUMÉ', sum(1 for _, c in R if c), '/', len(R))
asyncio.run(main())
