import asyncio, subprocess, time, json
from playwright.async_api import async_playwright
SITE = '/home/claude/whisper/site'; COURS = '/home/claude/outil/cours.pdf'
R = []
def ok(name, cond, extra=''):
    R.append((name, bool(cond))); print(('OK  ' if cond else 'ÉCHEC ') + name, extra, flush=True)
FS = {}
INIT = '''window.__noUnloadWarn=true; (()=>{try{const p=JSON.parse(localStorage.getItem("etude.prefs")||"{}");p.tourDone=true;localStorage.setItem("etude.prefs",JSON.stringify(p));}catch(e){}})();
const mkFile = (path) => ({ kind: 'file', name: path.split('/').pop(), getFile: async () => { const r = await window.fsGet(path); return new File([r.data], path.split('/').pop(), { lastModified: r.mtime }); },
  createWritable: async () => { let b = ''; return { write: async d => { b += d; }, close: async () => { await window.fsPut(path, b); } }; }, queryPermission: async () => 'granted', requestPermission: async () => 'granted' });
const mkDir = (path) => ({ kind: 'directory', name: path.split('/').pop(), queryPermission: async () => 'granted', requestPermission: async () => 'granted',
  getFileHandle: async (n, o) => { const p = path + '/' + n; const r = await window.fsGet(p); if (!r.exists && !(o && o.create)) { const e = new Error('nf'); e.name = 'NotFoundError'; throw e; } if (!r.exists) await window.fsPut(p, ''); return mkFile(p); },
  getDirectoryHandle: async (n) => mkDir(path + '/' + n), keys: async function* () {}, removeEntry: async () => {} });
window.showDirectoryPicker = async () => mkDir('Mon Drive/Atelier');'''
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8808', '--bind', '127.0.0.1'], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    async def fsGet(path):
        e = FS.get(path); return {'exists': e is not None, 'data': e[0] if e else '', 'mtime': e[1] if e else 0}
    async def fsPut(path, data):
        FS[path] = (data, int(time.time() * 1000))
    def notes_in_file():
        d = json.loads(FS.get('Mon Drive/Atelier/Atelier-etude-notes.json', FS.get(next((k for k in FS if k.endswith('.json') and 'Historique' not in k), ''), ('{}', 0)))[0] or '{}')
        return sorted(n['title'] for doc in d.get('docs', []) for n in doc.get('notes', []))
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            async def pc():
                ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); await ctx.add_init_script(INIT)
                await ctx.expose_function('fsGet', fsGet); await ctx.expose_function('fsPut', fsPut)
                pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
                await pg.goto('http://127.0.0.1:8808/'); await pg.wait_for_timeout(1200); await pg.evaluate('window.S=__atelier.S; window.B=__atelier.Backup; 1')
                return ctx, pg, errs
            ctxA, A, errA = await pc()
            await A.evaluate('B.useDir()'); await A.wait_for_timeout(500)
            ok('PC A : dossier de sauvegarde choisi', await A.evaluate('B.status') == 'connected')
            await A.set_input_files('#fileInput', COURS); await A.wait_for_selector('.page canvas'); await A.wait_for_timeout(600)
            await A.click('#quick'); await A.keyboard.type('Note du PC A'); await A.keyboard.press('Enter'); await A.wait_for_timeout(3500)
            ok('PC A : note écrite dans le dossier', 'Note du PC A' in notes_in_file(), notes_in_file())
            ctxB, B, errB = await pc()
            await B.evaluate('B.useDir()'); await B.wait_for_timeout(600)
            await B.set_input_files('#fileInput', COURS); await B.wait_for_selector('.page canvas'); await B.wait_for_timeout(600)
            ok('PC B : retrouve la note du PC A', await B.evaluate('S.doc.notes.some(n => n.title === "Note du PC A")'))
            await B.click('#quick'); await B.keyboard.type('Note du PC B'); await B.keyboard.press('Enter'); await B.wait_for_timeout(3500)
            ok('PC B : sa note s\'ajoute sans effacer celle de A', notes_in_file() == ['Note du PC A', 'Note du PC B'], notes_in_file())
            # retour sur A (fenêtre au premier plan)
            await A.evaluate('B.lastFocusPull = 0; window.dispatchEvent(new Event("focus"))'); await A.wait_for_timeout(1200)
            ok('PC A : récupère la note du PC B en revenant sur la fenêtre', await A.evaluate('S.doc.notes.some(n => n.title === "Note du PC B")'))
            await A.click('#quick'); await A.keyboard.type('Encore A'); await A.keyboard.press('Enter'); await A.wait_for_timeout(3500)
            ok('PC A : rien n\'est écrasé', notes_in_file() == ['Encore A', 'Note du PC A', 'Note du PC B'], notes_in_file())
            # B modifie pendant que A écrit sans revenir au premier plan
            await B.click('#quick'); await B.keyboard.type('B encore'); await B.keyboard.press('Enter'); await B.wait_for_timeout(3500)
            await A.click('#quick'); await A.keyboard.type('A sans recharger'); await A.keyboard.press('Enter'); await A.wait_for_timeout(3500)
            ok('écriture de A : fusionne d\'abord ce que B a ajouté', notes_in_file() == ['A sans recharger', 'B encore', 'Encore A', 'Note du PC A', 'Note du PC B'], notes_in_file())
            # redémarrage de B : relit le dossier
            await B.reload(); await B.wait_for_timeout(1500); await B.evaluate('window.S=__atelier.S; window.B=__atelier.Backup; 1')
            await B.evaluate('B.useDir()'); await B.wait_for_timeout(800)  # (le faux dossier du test ne se garde pas d'une session à l'autre, contrairement au vrai)
            ok('PC B rouvert : récupère tout', await B.evaluate('[...S.docs.values()].flatMap(d => d.notes).length') == 5)
            # enregistrement : plus de « Précise » choisi tout seul
            r = await A.evaluate('(async () => { const P = __atelier.prefs; delete P.recModel; Asr._gpu = { f16: true }; await RecUI.defaults(); const a = P.recModel; P.recModel = "precis"; P.recLive = true; delete P.recMig1; await RecUI.defaults(); return [a, P.recModel, P.recLive]; })()')
            ok('qualité par défaut Équilibrée ; Précise passe en « Après le cours »', r == ['equilibre', 'precis', False], r)
            ok('aucune erreur', not errA and not errB, (errA + errB)[:3])
            await b.close()
    finally: srv.kill()
    print('\nRÉSUMÉ', sum(1 for _, c in R if c), '/', len(R))
asyncio.run(main())
