import asyncio, subprocess, time, json, os
from playwright.async_api import async_playwright
SITE = '/home/claude/whisper/site'; COURS = '/home/claude/outil/cours.pdf'; OUT = '/home/claude/outil/shots19'; os.makedirs(OUT, exist_ok=True)
R = []
def ok(name, cond, extra=''):
    R.append((name, bool(cond))); print(('OK  ' if cond else 'ÉCHEC ') + name, extra, flush=True)
MOCK = '''window.__noUnloadWarn=true;
(()=>{try{const p=JSON.parse(localStorage.getItem("etude.prefs")||"{}");p.tourDone=true;localStorage.setItem("etude.prefs",JSON.stringify(p));}catch(e){}})();
window.YT = { Player: class { constructor(el, o) { const host = typeof el === 'string' ? document.getElementById(el) : el; const f = document.createElement('div'); f.id = 'fakeYT'; f.style.cssText = 'position:absolute;inset:0;background:#123;color:#fff;display:flex;align-items:center;justify-content:center;font:20px sans-serif'; f.textContent = 'Vidéo ' + o.videoId; host.replaceWith(f);
  this.o = o; this.vid = o.videoId; this.t = (o.playerVars && o.playerVars.start) || 0; this.state = 5; this.t0 = 0; this.rate = 1; window.__yt = this; setTimeout(() => o.events.onReady({ target: this }), 50); }
  _now() { return this.state === 1 ? this.t + (Date.now() - this.t0) / 1000 * this.rate : this.t; }
  getCurrentTime() { return this._now(); } getDuration() { return 600; } getPlayerState() { return this.state; }
  playVideo() { if (this.state !== 1) { this.t = this._now(); this.t0 = Date.now(); this.state = 1; this.o.events.onStateChange({ data: 1 }); } }
  pauseVideo() { if (this.state === 1) { this.t = this._now(); this.state = 2; this.o.events.onStateChange({ data: 2 }); } }
  seekTo(s) { this.t = s; this.t0 = Date.now(); }
  setPlaybackRate(r) { this.t = this._now(); this.t0 = Date.now(); this.rate = r; }
  cueVideoById(x) { this.vid = x.videoId; this.t = x.startSeconds || 0; this.state = 5; document.getElementById('fakeYT').textContent = 'Vidéo ' + x.videoId; }
  getVideoData() { return { video_id: this.vid, title: 'Titre de ' + this.vid, author: 'Chaîne test' }; } } };'''
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8796', '--bind', '127.0.0.1'], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); await ctx.add_init_script(MOCK)
            await ctx.grant_permissions(['clipboard-read', 'clipboard-write'], origin='http://127.0.0.1:8796')
            page = await ctx.new_page(); errs = []
            page.on('pageerror', lambda e: errs.append('PAGEERROR ' + str(e))); page.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'favicon' not in m.text else None)
            ev = page.evaluate
            await page.goto('http://127.0.0.1:8796/'); await page.wait_for_timeout(1200); await ev('window.S=__atelier.S; 1')
            ok('bouton vidéo sur l\'accueil', await ev('!!document.getElementById("vidBtn2").offsetParent'))
            await page.click('#vidBtn2'); await page.fill('#vidUrl', 'pas une vidéo'); await page.click('#vidGo')
            ok('adresse invalide refusée', 'pas une adresse' in await ev('document.getElementById("vidErr").textContent'))
            await page.fill('#vidUrl', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1m30s'); await page.click('#vidGo'); await page.wait_for_timeout(900)
            ok('vidéo ouverte (mode vidéo, lecteur)', await ev('document.body.classList.contains("vid") && !!document.getElementById("fakeYT") && S.doc.fp === "yt:dQw4w9WgXcQ"'))
            ok('reprise à 1:30 (t= de l\'adresse)', await ev('Math.round(Vid.time()) === 90'), await ev('Vid.time()'))
            ok('titre récupéré', await ev('S.doc.title === "Titre de dQw4w9WgXcQ" && document.getElementById("docTitle").value === S.doc.title'))
            ok('outils PDF masqués', await ev('["thumbsBtn","searchBox","recBtn","annotBtn","quoteBtn","addPinNote","tabPage"].every(id => !document.getElementById(id).offsetParent)'))
            ok('bouton ⏱ visible dans la barre des notes', await ev('!!document.getElementById("tcBtn").offsetParent'))
            await page.screenshot(path=OUT + '/1-video.png')
            await page.click('.vb-play'); await page.wait_for_timeout(2000)
            ok('lecture', await ev('Vid.playing()'))
            await page.click('#quick'); await page.keyboard.type('Idée principale'); await page.wait_for_timeout(200)
            ok('pause automatique quand j\'écris', await ev('!Vid.playing() && Vid.autoPaused'))
            tq = await ev('Math.floor(Vid.time())')
            await page.keyboard.press('Enter'); await page.wait_for_timeout(500)
            n1 = await ev('S.doc.notes.at(-1)')
            ok('note rapide avec le minutage', n1['t'] == tq and n1['title'] == 'Idée principale', n1['t'])
            ok('la vidéo repart après la note', await ev('Vid.playing()'))
            ok('toast avec le minutage', ':' in await ev('document.getElementById("toastTxt").textContent'), await ev('document.getElementById("toastTxt").textContent'))
            await page.wait_for_timeout(1500)
            await page.click('#viewer', position={'x': 30, 'y': 30}); await page.keyboard.press('Alt+KeyT'); await page.wait_for_timeout(400)
            n2 = await ev('({ html: S.doc.notes.at(-1).html, t: S.doc.notes.at(-1).t, playing: Vid.playing(), focused: document.activeElement.classList.contains("body") })')
            ok('⌥T : nouvelle note avec minutage, vidéo en pause', 'class="tc"' in n2['html'] and n2['t'] is not None and not n2['playing'] and n2['focused'], n2)
            await page.keyboard.type('Exemple donné par la prof'); await page.wait_for_timeout(300)
            await page.keyboard.press('Alt+KeyT'); await page.keyboard.type('suite'); await page.wait_for_timeout(500)
            ok('⌥T dans une note : minutage inséré au curseur', await ev('document.querySelector(".note:focus-within .body").querySelectorAll(".tc").length === 2'))
            await page.keyboard.press('Escape'); await page.wait_for_timeout(300)
            ok('Échap : la vidéo repart', await ev('Vid.playing()'))
            await ev('__atelier.renderNotes()'); await page.wait_for_timeout(200)
            ok('minutage conservé après réaffichage (data-t)', await ev('[...document.querySelectorAll(".note .body .tc")].every(x => /^\\d+$/.test(x.dataset.t)) && document.querySelectorAll(".note .body .tc").length === 2 && !document.querySelector(".note .body > .tc")'))
            await ev('Vid.seek(400)'); await ev('document.querySelector(".note .body .tc").click()'); await page.wait_for_timeout(300)
            t0 = await ev('+document.querySelector(".note .body .tc").dataset.t')
            ok('clic sur un minutage : retour à ce moment', abs(await ev('Vid.time()') - t0) < 1.5, [t0, await ev('Vid.time()')])
            await ev('Vid.seek(500)'); await ev('document.querySelector(".note .recb.vt").click()'); await page.wait_for_timeout(300)
            ok('bouton ▶ d\'une note : 3 s avant', abs(await ev('Vid.time()') - (n1['t'] - 3)) < 1.5)
            await page.wait_for_timeout(600)
            ok('points des notes sur la barre de la vidéo', await ev('document.querySelectorAll(".vb-marks i").length === 2'))
            order = await ev('[...document.querySelectorAll(".notes-list .note")].map(x => S.doc.notes.find(n => n.id === x.dataset.id).t)')
            ok('notes dans l\'ordre de la vidéo', order == sorted(order), order)
            ok('pas de titre « Page 1 »', await ev('!document.querySelector(".notes-list .page-group h4")'))
            await page.screenshot(path=OUT + '/2-notes.png')
            md = await ev('ToClaude.build(S.doc, {hl:true, images:true, peers:false, trans:true, since:0}).then(r => r.md)')
            ok('Envoyer à Claude : notes minutées avec liens', 'youtu.be/dQw4w9WgXcQ?t=' in md and "Notes dans l'ordre de la vidéo" in md and '[MA NOTE]' in md)
            print(md[:700])
            # PDF puis retour à la vidéo
            await page.set_input_files('#fileInput', COURS); await page.wait_for_selector('.page canvas'); await page.wait_for_timeout(1200)
            ok('ouvrir un PDF : retour au mode PDF', await ev('!document.body.classList.contains("vid") && S.pages.length > 0 && document.getElementById("vidStage").classList.contains("hidden") && !!document.getElementById("searchBox").offsetParent'))
            ok('vidéo en pause en quittant', await ev('window.__yt.state !== 1'))
            await ev('[...document.querySelectorAll(".dtab")].find(x => x.textContent.includes("Titre de")).click()'); await page.wait_for_timeout(900)
            ok('onglet vidéo : retour à la vidéo et aux notes', await ev('document.body.classList.contains("vid") && S.doc.kind === "video" && document.querySelectorAll(".notes-list .note").length === 2 && !document.getElementById("vidStage").classList.contains("hidden")'))
            # fermer, retrouver dans les cours récents
            await ev('[...document.querySelectorAll(".dtab")].forEach(x => x.querySelector(".x").click())'); await page.wait_for_timeout(500)
            await ev('[...document.querySelectorAll(".dtab")].forEach(x => x.querySelector(".x").click())'); await page.wait_for_timeout(800)
            ok('fermé : accueil', await ev('!S.doc && !document.body.classList.contains("vid")'))
            await ev('[...document.querySelectorAll("#recentList .lib-item")].find(x => x.textContent.includes("Titre de")).click()'); await page.wait_for_timeout(900)
            ok('rouverte depuis « Reprendre un cours »', await ev('S.doc && S.doc.kind === "video" && S.doc.notes.length === 2'))
            # coller une adresse sur l'accueil
            await ev('[...document.querySelectorAll(".dtab")].forEach(x => x.querySelector(".x").click())'); await page.wait_for_timeout(600)
            await ev('''(() => { const dt = new DataTransfer(); dt.setData("text", "https://youtu.be/abcdefghijk?t=42"); document.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true })); })()'''); await page.wait_for_timeout(900)
            ok('coller une adresse YouTube ouvre la vidéo', await ev('S.doc && S.doc.fp === "yt:abcdefghijk" && Math.round(Vid.time()) === 42'))
            # sauvegarde : le minutage est conservé
            res = await ev('''(async () => { const d = JSON.parse(JSON.stringify(S.docs.get("yt:dQw4w9WgXcQ"))); d.fp = "yt:zzzzzzzzzzz"; d.notes.forEach(n => n.id = n.id + "x"); await __atelier.mergeBackup({ docs: [d] }); const m = S.docs.get("yt:zzzzzzzzzzz"); return { kind: m.kind, vid: m.vid, ts: m.notes.map(n => n.t), tc: m.notes.some(n => /data-t=/.test(n.html)) }; })()''')
            ok('sauvegarde importée : vidéo, minutages et liens gardés', res['kind'] == 'video' and res['vid'] == 'zzzzzzzzzzz' and all(t is not None for t in res['ts']) and res['tc'], res)
            await page.set_viewport_size({'width': 1280, 'height': 800}); await page.wait_for_timeout(600)
            w = await ev('({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})')
            ok('1280 px : pas de débordement', w['sw'] <= w['cw'], w)
            await page.screenshot(path=OUT + '/3-1280.png')
            ok('aucune erreur JavaScript', not errs, errs[:5])
            await b.close()
    finally: srv.kill()
    print('\nRÉSUMÉ', sum(1 for _, c in R if c), '/', len(R))
asyncio.run(main())
