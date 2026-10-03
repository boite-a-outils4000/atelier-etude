import asyncio, json, os
from playwright.async_api import async_playwright
APP='file:///home/claude/outil/Atelier-etude.html'; PDF='/home/claude/Synthese_DAP_S1_Introduction.pdf'; OUT='/home/claude/outil/shots4'; os.makedirs(OUT, exist_ok=True)
MOCK="window.__noUnloadWarn=true; (()=>{try{const p=JSON.parse(localStorage.getItem('etude.prefs')||'{}');p.tourDone=true;localStorage.setItem('etude.prefs',JSON.stringify(p));}catch(e){}})(); window.print=()=>{window.__printed=(window.__printed||0)+1};"
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1440,'height':900}, accept_downloads=True); await ctx.add_init_script(MOCK); page=await ctx.new_page()
        errs=[]; page.on('pageerror', lambda e: errs.append(str(e))); page.on('console', lambda m: errs.append(m.text) if m.type=='error' else None)
        await page.goto(APP); await page.wait_for_timeout(1000)
        await page.set_input_files('#fileInput', PDF); await page.wait_for_selector('.page canvas'); await page.wait_for_timeout(800)
        # mes notes : p.5 et p.9 (une privée)
        for pg, title, body, priv in [(5,'PISA : 6 enseignements','Équité en progrès, redoublement à 35 %.',False),(9,'Approche évolutive','Observer, adapter, soutenir.',False),(9,'Idée perso','à ne pas partager',True)]:
            await page.fill('#pageInput', str(pg)); await page.press('#pageInput','Enter'); await page.wait_for_timeout(700)
            await page.keyboard.press('Alt+KeyN'); await page.keyboard.type(title); await page.keyboard.press('Enter'); await page.keyboard.type(body); await page.wait_for_timeout(300)
            if priv: await page.evaluate('() => { const n=window.__atelier.S.doc.notes.at(-1); n.private=true; }')
        # Partager mes notes
        await page.click('#expBtn'); await page.click('#ddExport [data-x="share"]'); await page.wait_for_timeout(200)
        await page.fill('#shName','Hugo'); await page.screenshot(path=f'{OUT}/01-partager.png')
        async with page.expect_download() as d: await page.click('#shGo')
        dl=await d.value; path=f'{OUT}/partage-hugo.json'; await dl.save_as(path)
        sh=json.load(open(path)); print('share kind', sh['kind'], 'author', sh['author']['name'], 'notes', len(sh['notes']), [n['title'] for n in sh['notes']])
        # Fabriquer les fichiers de deux collègues à partir du mien
        fp=sh['fp']
        julie=dict(sh, author={'id':'uJULIE','name':'Julie'}, notes=[
            {'id':'j1','page':9,'title':'Leviers : AP + suivi + DAccE','html':'<div>Les trois leviers se combinent.</div>','tags':['retenir'],'created':1,'updated':1,'pin':{'x':0.5,'y':0.3}},
            {'id':'j2','page':12,'title':'MTSS niveau 1 ?','html':'<div>Le niveau 1 n\'est pas défini dans le cours.</div>','tags':['question'],'created':2,'updated':2},
            {'id':'j3','page':14,'title':'Forget : tensions','html':'<ul><li>étayer/désétayer</li><li>adapter/institutionnaliser</li></ul>','tags':[],'created':3,'updated':3}],
            highlights=[{'id':'jh1','page':9,'color':'green','rects':[{'x':0.1,'y':0.2,'w':0.4,'h':0.02}],'text':'Enjeu 1'}], anchors=[])
        marc=dict(sh, author={'id':'uMARC','name':'Marc'}, fp='autre-fichier-123', docTitle='DAP S1 (version Marc)', notes=[
            {'id':'m1','page':5,'title':'PISA','html':'<div>FWB au niveau OCDE mais OCDE en baisse.</div>','tags':['verifier'],'created':1,'updated':1},
            {'id':'m2','page':14,'title':'Plan de travail','html':'<div>Consolidation autogérée.</div>','tags':['exemple'],'created':2,'updated':2}], highlights=[], anchors=[])
        json.dump(julie, open(f'{OUT}/julie.json','w')); json.dump(marc, open(f'{OUT}/marc.json','w'))
        await page.set_input_files('#jsonInput', f'{OUT}/julie.json'); await page.wait_for_timeout(800)
        await page.set_input_files('#jsonInput', f'{OUT}/marc.json'); await page.wait_for_timeout(600)
        await page.screenshot(path=f'{OUT}/02-rattacher.png')
        await page.click('[data-c="attach"]'); await page.wait_for_timeout(600)
        print('peers', await page.evaluate('Object.values(window.__atelier.S.doc.peers).map(p=>p.name+":"+p.notes.length+":"+p.color+":"+p.matched)'))
        # Affichage page 9
        await page.fill('#pageInput','9'); await page.press('#pageInput','Enter'); await page.wait_for_timeout(900)
        print('peer cards p9', await page.evaluate('document.querySelectorAll(".note.peer").length'), 'ppins', await page.evaluate('document.querySelectorAll(".page[data-n=\\"9\\"] .ppin").length'), 'phl', await page.evaluate('document.querySelectorAll(".page[data-n=\\"9\\"] .phl").length'), 'peerbadges', await page.evaluate('document.querySelectorAll(".badge.peerb").length'))
        await page.screenshot(path=f'{OUT}/03-page9.png')
        # copier la note de Julie
        await page.click('.note.peer .cp'); await page.wait_for_timeout(400)
        print('my notes p9', await page.evaluate('window.__atelier.S.doc.notes.filter(n=>n.page===9).map(n=>n.title)'))
        # Toutes les notes
        await page.click('#tabAll'); await page.wait_for_timeout(300); await page.screenshot(path=f'{OUT}/04-toutes.png')
        # Comparer
        await page.click('#groupBtn'); await page.wait_for_timeout(300); await page.screenshot(path=f'{OUT}/05-comparer.png', full_page=False)
        print('gaps', await page.evaluate('[...document.querySelectorAll(".gap-chip")].map(x=>x.textContent)'))
        # Synthèse md
        async with page.expect_download() as d: await page.click('[data-g="gmd"]')
        dl=await d.value; await dl.save_as(f'{OUT}/synthese-commune.md')
        await page.click('[data-g="gpdf"]'); await page.wait_for_function('window.__printed>=1')
        await page.emulate_media(media='print'); await page.pdf(path=f'{OUT}/synthese-commune.pdf', prefer_css_page_size=True, print_background=True); await page.emulate_media(media='screen')
        await page.click('#groupBtn'); await page.click('[data-g="gsbs"]'); await page.wait_for_function('window.__printed>=2', timeout=30000)
        await page.emulate_media(media='print'); await page.pdf(path=f'{OUT}/synthese-cote.pdf', prefer_css_page_size=True, print_background=True); await page.emulate_media(media='screen')
        # masquer les collègues
        await page.click('#tabPage'); await page.click('#filtBtn'); await page.uncheck('#showPeers'); await page.keyboard.press('Escape'); await page.wait_for_timeout(300)
        print('peer cards hidden', await page.evaluate('document.querySelectorAll(".note.peer").length'))
        await page.click('#filtBtn'); await page.check('#showPeers'); await page.keyboard.press('Escape')
        # persistance
        await page.wait_for_timeout(900); await page.reload(); await page.wait_for_timeout(1500)
        await page.screenshot(path=f'{OUT}/06-accueil.png')
        await page.set_input_files('#fileInput', PDF); await page.wait_for_selector('.page canvas'); await page.wait_for_timeout(1000)
        print('after reload peers', await page.evaluate('Object.keys(window.__atelier.S.doc.peers).length'))
        # Bibliothèque : recherche chez les collègues
        await page.click('#coursBtn'); await page.click('#libBtn'); await page.fill('#libQ','consolidation'); await page.wait_for_timeout(300); await page.screenshot(path=f'{OUT}/07-biblio.png')
        print('ERRORS', errs); await b.close()
asyncio.run(main())
