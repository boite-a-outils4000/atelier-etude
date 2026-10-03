import asyncio, os, json
from playwright.async_api import async_playwright
APP = 'file:///home/claude/outil/Atelier-etude.html'; SYN = '/home/claude/Synthese_DAP_S1_Introduction.pdf'
QF = '/home/claude/outil/QCM - DAP séance 1.json'; OUT = '/home/claude/outil/shots13'; os.makedirs(OUT, exist_ok=True)
R = []
def ok(name, cond, extra=''):
    R.append((name, bool(cond))); print(('OK  ' if cond else 'ÉCHEC ') + name, extra)
async def type_note(page, title, html, pg):
    await page.evaluate('''([t, h, p]) => { const A = window.__atelier; }''', [title, html, pg])
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, accept_downloads=True)
        await ctx.add_init_script('window.__noUnloadWarn=true; (()=>{try{const p=JSON.parse(localStorage.getItem("etude.prefs")||"{}");p.tourDone=true;p.sbTab="pages";p.sessSize=10;localStorage.setItem("etude.prefs",JSON.stringify(p));}catch(e){}})();')
        page = await ctx.new_page(); errs = []
        page.on('pageerror', lambda e: errs.append('PAGEERROR ' + str(e))); page.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
        ev = page.evaluate
        await page.goto(APP); await page.wait_for_timeout(900)
        await page.set_input_files('#fileInput', SYN); await page.wait_for_selector('.page canvas'); await page.wait_for_timeout(1300)
        # --- notes de départ : 4 concepts, 3 auteurs, mots en gras, une question
        for (concept, d, pg) in [('équité', 'Donner à chacun ce dont il a besoin pour que tous atteignent les mêmes attendus.', 15), ('désétayage', 'Retirer progressivement les aides pour que l\'élève construise ses propres outils.', 18), ('table d\'appui', 'Regroupement ponctuel près de l\'enseignant d\'élèves aux besoins proches.', 18), ('plan de travail', 'Consolidation autogérée : l\'élève choisit l\'ordre et le rythme des tâches.', 18)]:
            await page.fill('#pageInput', str(pg)); await page.press('#pageInput', 'Enter'); await page.wait_for_timeout(500)
            await page.click('[data-dd="ddTpl"]'); await page.click('#ddTpl [data-tpl="concept"]'); await page.keyboard.type(concept); await page.wait_for_timeout(100)
            await page.evaluate('() => { const el=[...document.querySelectorAll(".note")].at(-1) ; const n=window.__atelier.S.doc.notes.at(-1); const c=document.querySelector(`.note[data-id="${n.id}"] .callout.def div`); const r=document.createRange(); r.selectNodeContents(c); r.collapse(true); c.closest(".body").focus(); const s=getSelection(); s.removeAllRanges(); s.addRange(r); }')
            await page.keyboard.type(d); await page.wait_for_timeout(150)
        for (who, idea) in [('Forget (2018)', 'Modèle intégrateur : temporalités, objectifs, dispositifs, conditions d\'efficacité'), ('Galand (2017)', 'Pratiques efficaces : défi pour tous, objectifs clairs, feedbacks, flexibilité'), ('Coertjens (2022)', 'Exemple de Louise et proportions 80/15/5 de la RàI')]:
            await page.click('[data-dd="ddTpl"]'); await page.click('#ddTpl [data-tpl="auteur"]'); await page.keyboard.type(who)
            await page.evaluate('''(idea) => { const n = window.__atelier.S.doc.notes.at(-1); n.html = n.html.replace("<b>Modèle ou idée clé :</b>&nbsp;", "<b>Modèle ou idée clé :</b> " + idea); }''', idea)
        await page.fill('#pageInput', '5'); await page.press('#pageInput', 'Enter'); await page.wait_for_timeout(500)
        await page.click('#addNote'); await page.keyboard.type('Six enseignements de PISA'); await page.keyboard.press('Enter')
        await page.keyboard.type('Le taux de redoublement reste de ')
        await page.keyboard.press('ControlOrMeta+b'); await page.keyboard.type('35 %'); await page.keyboard.press('ControlOrMeta+b'); await page.keyboard.type(' des élèves de 15 ans en FWB.')
        await page.keyboard.press('Enter'); await page.keyboard.type('Les écarts liés au ')
        await page.click('#fmt [data-cmd="bold"]'); await page.keyboard.type('parcours scolaire'); await page.click('#fmt [data-cmd="bold"]'); await page.keyboard.type(' restent très élevés en 2025.')
        await page.keyboard.press('Enter'); await page.keyboard.type('La moyenne de la FWB rejoint celle de l\'')
        await page.keyboard.press('ControlOrMeta+b'); await page.keyboard.type('OCDE'); await page.keyboard.press('ControlOrMeta+b'); await page.keyboard.type(' en sciences.')
        await page.keyboard.press('Enter'); await page.keyboard.type('Les progrès ne viennent pas encore du ')
        await page.keyboard.press('ControlOrMeta+b'); await page.keyboard.type('Pacte d\'excellence'); await page.keyboard.press('ControlOrMeta+b'); await page.keyboard.type(' selon le cours.')
        await page.wait_for_timeout(800)
        # QCM perso via modèle
        await page.click('[data-dd="ddTpl"]'); await page.click('#ddTpl [data-tpl="qcm"]'); await page.keyboard.type('Combien de volets compte le DAccE ?')
        qn = await ev('window.__atelier.S.doc.notes.at(-1).id')
        st1 = await ev(f'document.querySelector(\'.note[data-id="{qn}"] .qcm-st\').textContent')
        await page.evaluate(f'''() => {{ const b=document.querySelector('.note[data-id="{qn}"] .body'); const lis=b.querySelectorAll('ul.check li'); ['2','3','4','5'].forEach((t,i)=>lis[i].textContent=t); lis[2].classList.add('done'); b.dispatchEvent(new Event('input',{{bubbles:true}})); }}''')
        await page.wait_for_timeout(500)
        st2 = await ev(f'document.querySelector(\'.note[data-id="{qn}"] .qcm-st\').textContent')
        await page.screenshot(path=f'{OUT}/01-qcm-perso.png')
        ok('modèle QCM : statut guidé puis « prêt »', st1.startswith('QCM :') and st2 == 'QCM prêt', f'{st1} → {st2}')
        # --- passer en Réviser
        await page.click('#modeSeg [data-mode="revise"]'); await page.wait_for_timeout(600)
        items = await ev('Rev.items(window.__atelier.S.doc).reduce((a,i)=>{const k=i.src+(i.sub?":"+i.sub:""); a[k]=(a[k]||0)+1; return a;},{})')
        ok('QCM automatiques (définitions, notions, auteurs, trous) + perso + questions ouvertes', items.get('auto:Définition', 0) >= 4 and items.get('auto:Auteur', 0) >= 3 and items.get('auto:Texte à trous', 0) >= 4 and items.get('perso', 0) == 1 and items.get('note', 0) >= 5, json.dumps(items, ensure_ascii=False))
        cnt = await ev('document.getElementById("sessCount").textContent')
        ok('compteur « Séance du jour »', cnt.strip() not in ('', '0'), cnt)
        # --- importer les QCM de Claude
        await page.click('#revMenuBtn'); await page.wait_for_timeout(200); await page.screenshot(path=f'{OUT}/02-menu-exercices.png')
        await page.keyboard.press('Escape')
        await page.set_input_files('#qcmInput', QF); await page.wait_for_timeout(600)
        await page.screenshot(path=f'{OUT}/03-import.png')
        await page.click('.modal [data-go]'); await page.wait_for_timeout(600)
        ok('import du fichier de QCM', await ev('window.__atelier.S.doc.quiz.length') == 37)
        await page.set_input_files('#qcmInput', QF); await page.wait_for_timeout(500); await page.click('.modal [data-go]'); await page.wait_for_timeout(400)
        ok('réimport : pas de doublons', await ev('window.__atelier.S.doc.quiz.length') == 37)
        # --- séance du jour
        await page.click('#sessBtn'); await page.wait_for_timeout(500)
        total = await ev('Sess.q.length')
        await page.screenshot(path=f'{OUT}/04-seance-question.png')
        did_danger = False; did_open = False; n_ans = 0; guard = 0
        while await ev('Sess.active && !!document.querySelector(".ss")') and guard < 60:
            guard += 1
            it = await ev('(() => { const e = Sess.cur(); return { type: e.it.type, retry: e.retry, pos: Sess.order ? Sess.order.indexOf(e.it.answer) : -1, n: e.it.choices ? e.it.choices.length : 0 }; })()')
            if it['type'] == 'qcm':
                if not did_danger and it['retry'] == 0:
                    wrong = (it['pos'] + 1) % it['n']; await page.keyboard.press('abcdefgh'[wrong]); await page.keyboard.press('6'); did_danger = True
                else:
                    await page.keyboard.press('abcdefgh'[it['pos']]); await page.keyboard.press(str(3 + (n_ans % 3)))
                if n_ans == 1: await page.screenshot(path=f'{OUT}/05-choix-certitude.png')
                await page.keyboard.press('Enter'); await page.wait_for_timeout(150)
                if did_danger and n_ans == 0: await page.screenshot(path=f'{OUT}/06-erreur-a-risque.png')
            else:
                await page.fill('#ssFree', 'Je pense que c\'est la réponse attendue.'); await page.keyboard.press('Tab'); await page.keyboard.press('4'); await page.keyboard.press('Enter'); await page.wait_for_timeout(150)
                if not did_open: await page.screenshot(path=f'{OUT}/07-question-ouverte.png')
                await page.keyboard.press('o'); did_open = True; await page.wait_for_timeout(100)
            n_ans += 1
            if n_ans == 3 and await ev('!!document.getElementById("ssPeek")'):
                await page.click('#ssPeek'); await page.wait_for_timeout(500)
                ok('« Voir dans le cours » : séance en pause + bouton Reprendre', await ev('!!document.getElementById("sessPill") && !document.querySelector(".ss")'))
                await page.screenshot(path=f'{OUT}/08-pause.png')
                await page.click('#sessPill'); await page.wait_for_timeout(300)
            await page.keyboard.press('Enter'); await page.wait_for_timeout(120)
        await page.wait_for_timeout(400)
        ok('séance complète jusqu\'au bilan de séance', await ev('(document.querySelector(".modal-h h3")||{}).textContent') == 'Séance terminée', f'{total} questions, {n_ans} réponses (avec nouveaux essais)')
        await page.screenshot(path=f'{OUT}/09-fin-seance.png')
        ok('erreur à risque enregistrée', await ev('Object.values(window.__atelier.S.doc.rev).some(s=>s.danger)'))
        ok('question ouverte jouée', did_open)
        await page.click('.modal [data-x="bilan"]'); await page.wait_for_timeout(500)
        await page.screenshot(path=f'{OUT}/10-bilan.png', full_page=False)
        ok('bilan : réalisme et maîtrise affichés', await ev('!!document.querySelector(".calib .cl-row") && !!document.querySelector(".pmap .m-r, .pmap .m-g, .pmap .m-o")'))
        await page.keyboard.press('Escape')
        # --- exercices : erreurs à risque, tous les QCM, gestion
        await page.click('#revMenuBtn'); await page.click('#ddRev [data-r="danger"]'); await page.wait_for_timeout(400)
        ok('« Erreurs à risque » lance une séance ciblée', await ev('Sess.active && Sess.q.length >= 1'))
        await page.keyboard.press('Escape'); await page.wait_for_timeout(200)
        await page.click('#revMenuBtn'); await page.click('#ddRev [data-r="list"]'); await page.wait_for_timeout(400)
        await page.screenshot(path=f'{OUT}/11-gestion.png')
        ok('gestion des QCM', await ev('document.querySelectorAll(".qrow").length') >= 45)
        await page.keyboard.press('Escape')
        await page.click('#thumbsBtn'); await page.wait_for_timeout(800)
        ok('vignettes : pastilles de maîtrise en mode Réviser', await ev('document.querySelectorAll(".thumb[data-m]").length') >= 1)
        await page.screenshot(path=f'{OUT}/12-vignettes-maitrise.png')
        # --- sauvegarde complète puis rechargement
        async with page.expect_download() as d:
            await page.click('#coursBtn'); await page.click('#ddCours [data-x="json"]')
        dl = await d.value; bk = json.load(open(await dl.path(), encoding='utf-8'))
        bdoc = [x for x in bk['docs'] if x.get('quiz')][0]
        ok('sauvegarde .json : QCM, résultats et historique de séances inclus', len(bdoc['quiz']) == 37 and len(bdoc['rev']) >= 8 and len(bdoc['revLog']) >= 1)
        await page.wait_for_timeout(800); await page.reload(); await page.wait_for_timeout(1300)
        await page.set_input_files('#fileInput', SYN); await page.wait_for_selector('.page canvas'); await page.wait_for_timeout(1300)
        ok('rechargement : QCM et résultats conservés', await ev('window.__atelier.S.doc.quiz.length') == 37 and await ev('Object.keys(window.__atelier.S.doc.rev).length') >= 8)
        await page.fill('#pageInput', '5'); await page.press('#pageInput', 'Enter'); await page.wait_for_timeout(700)
        bt = await ev('[...document.querySelectorAll(".note .body b")].map(x=>x.textContent).join("|")'); ok('le gras reste en gras après rechargement', '35 %' in bt and 'parcours scolaire' in bt, bt)
        # --- import de la sauvegarde dans un navigateur vierge
        ctx2 = await b.new_context(viewport={'width': 1280, 'height': 800}); await ctx2.add_init_script('window.__noUnloadWarn=true; localStorage.setItem("etude.prefs", JSON.stringify({tourDone:true}))')
        p2 = await ctx2.new_page(); await p2.goto(APP); await p2.wait_for_timeout(800)
        await p2.set_input_files('#jsonInput', await dl.path()); await p2.wait_for_timeout(1200)
        await p2.set_input_files('#fileInput', SYN); await p2.wait_for_selector('.page canvas'); await p2.wait_for_timeout(1200)
        ok('import de la sauvegarde ailleurs : QCM et résultats retrouvés', await p2.evaluate('window.__atelier.S.doc.quiz.length') == 37 and await p2.evaluate('Object.keys(window.__atelier.S.doc.rev).length') >= 8)
        await p2.click('#modeSeg [data-mode="revise"]'); await p2.wait_for_timeout(500); await p2.click('#sessBtn'); await p2.wait_for_timeout(500)
        await p2.screenshot(path=f'{OUT}/13-seance-1280.png')
        await p2.evaluate('document.documentElement.setAttribute("data-theme","dark")'); await p2.wait_for_timeout(300)
        await p2.keyboard.press('a'); await p2.keyboard.press('5'); await p2.keyboard.press('Enter'); await p2.wait_for_timeout(300)
        await p2.screenshot(path=f'{OUT}/14-seance-sombre.png')
        ok('aucune erreur JavaScript', not errs, str(errs[:4]))
        print('\nRÉSUMÉ', sum(1 for r in R if r[1]), '/', len(R))
        await b.close()
asyncio.run(main())
