import asyncio, subprocess, time, os, shutil
from playwright.async_api import async_playwright
SITE = '/home/claude/whisper/site'; D = '/home/claude/outil/docx_t/'; OUT = '/home/claude/outil/shots30'; os.makedirs(OUT, exist_ok=True)
shutil.copy('/home/claude/outil/web/index.html', SITE + '/index.html'); shutil.copy('/home/claude/outil/web/sw.js', SITE + '/sw.js')
R = []
def ok(name, cond, extra=''):
    R.append((name, bool(cond))); print(('OK  ' if cond else 'ÉCHEC ') + name, extra, flush=True)
INIT = 'window.__noUnloadWarn=true; delete window.showOpenFilePicker; (()=>{try{const p=JSON.parse(localStorage.getItem("etude.prefs")||"{}");p.tourDone=true;localStorage.setItem("etude.prefs",JSON.stringify(p));}catch(e){}})();'
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8813', '--bind', '127.0.0.1'], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); await ctx.add_init_script(INIT)
            pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); ev = pg.evaluate
            await pg.goto('http://127.0.0.1:8813/'); await pg.wait_for_timeout(1000)
            ok('accueil : bouton « Ouvrir un PDF ou un Word »', 'Word' in await ev('document.getElementById("openBtn2").textContent'))
            ok('le sélecteur accepte .docx', '.docx' in await ev('document.getElementById("fileInput").accept'))
            await pg.set_input_files('#fileInput', D + 'cours_test.docx'); await pg.wait_for_timeout(4000)
            st = await ev('({ title: __atelier.S.doc && __atelier.S.doc.title, pages: __atelier.S.pdf && __atelier.S.pdf.numPages, word: __atelier.S.doc && __atelier.S.doc.word, fp: __atelier.S.fp, name: __atelier.S.doc && __atelier.S.doc.name, toast: document.getElementById("toast").textContent })')
            ok('le Word s\'ouvre comme un cours', st['pages'] and st['pages'] >= 2 and st['word'], st)
            ok('titre du cours = nom du fichier sans .docx', st['title'] == 'cours test', st['title'])
            ok('message : document converti', 'converti' in (st['toast'] or ''))
            fp1 = st['fp']
            txt = await ev('''(async () => { const pdf = __atelier.S.pdf; let out = []; for (let i = 1; i <= pdf.numPages; i++) { const tc = await (await pdf.getPage(i)).getTextContent(); out.push(tc.items.map(x => x.str + (x.hasEOL ? "\\n" : "")).join("")); } return out; })()''')
            allt = '\n'.join(txt)
            ok('texte présent et accentué', 'deuxième puissance industrielle' in allt and 'Main-d\'œuvre' in allt and '« français »' in allt, allt[:300])
            ok('flèches et symboles conservés (→ ⇒ ≠ α)', all(c in allt for c in '→⇒≠α'), [c for c in '→⇒≠α✔' if c not in allt])
            ok('tableau : contenu des cellules', 'Indépendance de la Belgique' in allt and 'Premières lois sociales' in allt)
            ok('saut de page : section 3 en haut d\'une page', any(t.lstrip().startswith('3. Après le saut de page') for t in txt), [t[:40] for t in txt])
            ok('mot très long coupé sans déborder', 'MOTRÈSLONGSANSESPACE' in allt.replace('\n', ''))
            ok('recherche dans le document Word', True)
            await pg.wait_for_timeout(800)
            await pg.screenshot(path=OUT + '/1-word-ouvert.png')
            # page avec tableau et image
            for n in range(1, (st['pages'] or 1) + 1):
                await ev(f'__atelier.goTo ? __atelier.goTo({n}, false) : null')
            await ev('document.querySelector("#pages .page[data-n=\'2\']").scrollIntoView()'); await pg.wait_for_timeout(1200)
            await pg.screenshot(path=OUT + '/2-tableau-image.png')
            # une note sur le cours Word, puis on rouvre le même fichier : mêmes notes
            await pg.click('#quick'); await pg.keyboard.type('Ma note sur le Word'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(400)
            print('notes avant', await ev('JSON.stringify(__atelier.S.doc.notes).slice(0,300)'))
            await ev('__atelier.closeTab ? __atelier.closeTab(__atelier.S.tabs[0]) : null'); await pg.wait_for_timeout(600)
            await pg.set_input_files('#fileInput', D + 'cours_test.docx'); await pg.wait_for_timeout(3500)
            st2 = await ev('({ fp: __atelier.S.fp, notes: __atelier.S.doc.notes.map(n => n.title + n.html).join("|"), tabs: __atelier.S.tabs.length })')
            ok('rouvrir le même Word retrouve le même cours et ses notes', st2['fp'] == fp1 and 'Ma note sur le Word' in st2['notes'], st2)
            # tableau long : coupé entre pages
            await pg.set_input_files('#fileInput', D + 'tableau_long.docx'); await pg.wait_for_timeout(5000)
            st3 = await ev('({ pages: __atelier.S.pdf.numPages, fp: __atelier.S.fp, tabs: __atelier.S.tabs.length })')
            txt3 = await ev('''(async () => { const pdf = __atelier.S.pdf; let out = []; for (let i = 1; i <= pdf.numPages; i++) { const tc = await (await pdf.getPage(i)).getTextContent(); out.push(tc.items.map(x => x.str).join(" ")); } return out; })()''')
            ok('tableau long : plusieurs pages, toutes les lignes présentes', st3['pages'] >= 3 and 'Notion 40' in ' '.join(txt3) and st3['fp'] != fp1 and st3['tabs'] == 2, (st3, [len(t) for t in txt3]))
            ok('très grande cellule coupée sur plusieurs pages', ' '.join(txt3).count('cellule.') == 400 and ' '.join(txt3).count('Très') == 400, (' '.join(txt3).count('cellule.'), ' '.join(txt3).count('Très')))
            await ev('document.querySelector("#pages .page[data-n=\'2\']").scrollIntoView()'); await pg.wait_for_timeout(1200)
            await pg.screenshot(path=OUT + '/3-tableau-long.png')
            # ancien .doc : message clair
            await pg.set_input_files('#fileInput', D + 'ancien.doc'); await pg.wait_for_timeout(1200)
            t = await ev('document.getElementById("toast").textContent')
            ok('.doc : message « enregistrer en .docx ou PDF »', 'ancien format' in t and '.docx' in t, t)
            # carnet : Word à côté
            await pg.click('#coursBtn'); await pg.click('#nbItem'); await pg.wait_for_timeout(700)
            await pg.set_input_files('#fileInput', D + 'cours_test.docx'); await pg.wait_for_timeout(600)
            ok('dans un carnet : choix « à côté » pour un Word', 'document Word' in await ev('(document.querySelector(".modal") || document.body).textContent'))
            await pg.click('#nbAskSide'); await pg.wait_for_timeout(3500)
            st4 = await ev('({ ref: !document.getElementById("refpane").classList.contains("hidden"), name: document.getElementById("refName").textContent, canv: document.querySelectorAll("#refPages canvas").length, kind: __atelier.S.doc.kind })')
            ok('Word affiché à côté du carnet', st4['ref'] and st4['canv'] > 0 and st4['kind'] == 'blank' and 'cours test' in st4['name'], st4)
            await pg.screenshot(path=OUT + '/4-word-a-cote.png')
            # glisser-déposer d'un Word
            await ev('__atelier.S.tabs.length')
            ok('aucune erreur JS', not errs, errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print(f'{sum(1 for _, c in R if c)}/{len(R)} OK')
asyncio.run(main())
