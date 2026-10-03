import asyncio, json, os, sys
from playwright.async_api import async_playwright

APP = 'file:///home/claude/outil/Atelier-etude.html'
PDF = '/home/claude/Synthese_DAP_S1_Introduction.pdf'
OUT = '/home/claude/outil/shots2'
os.makedirs(OUT, exist_ok=True)
v1 = json.load(open('/home/claude/outil/shots/backup.json'))['docs'][0]

MOCK = '''
window.__noUnloadWarn = true; (()=>{try{const p=JSON.parse(localStorage.getItem('etude.prefs')||'{}');p.tourDone=true;localStorage.setItem('etude.prefs',JSON.stringify(p));}catch(e){}})();
window.showSaveFilePicker = async () => ({ name: 'sauvegarde-test.json', kind: 'file', queryPermission: async () => 'granted', requestPermission: async () => 'granted', createWritable: async () => { let buf = ''; return { write: async (d) => { buf += d; }, close: async () => { window.__fileContent = buf; window.__writes = (window.__writes || 0) + 1; } }; } });
window.print = () => { window.__printed = (window.__printed || 0) + 1; };
'''

async def sel_text(page, pageNo, minlen=25):
    return await page.evaluate('''([n, minlen]) => { const sp=[...document.querySelectorAll(`.page[data-n="${n}"] .textLayer span`)].find(s=>s.textContent.trim().length>minlen); if(!sp) return null; const r=document.createRange(); r.selectNodeContents(sp); const s=getSelection(); s.removeAllRanges(); s.addRange(r); const b=sp.getBoundingClientRect(); return {x:b.left+b.width/2, y:b.top+b.height/2, t: sp.textContent}; }''', [pageNo, minlen])

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=1, accept_downloads=True)
        await ctx.add_init_script(MOCK)
        page = await ctx.new_page()
        errs = []
        page.on('console', lambda m: errs.append(f'{m.type}: {m.text}') if m.type == 'error' else None)
        page.on('pageerror', lambda e: errs.append('PAGEERROR ' + str(e)))
        page.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        # Données v1 dans localStorage
        await page.goto(APP)
        await page.evaluate('([k, v]) => localStorage.setItem(k, v)', ['etude.doc.' + v1['fp'], json.dumps(v1)])
        await page.reload(); await page.wait_for_timeout(1800)
        print('docs after migration', await page.evaluate('window.__atelier.S.docs.size'))
        await page.screenshot(path=f'{OUT}/01-accueil.png')

        # Ouvrir le PDF (via input)
        await page.set_input_files('#fileInput', PDF)
        await page.wait_for_selector('.page canvas', timeout=20000); await page.wait_for_timeout(1500)
        print('notes from v1', await page.evaluate('window.__atelier.S.doc.notes.length'), 'page', await page.evaluate('window.__atelier.S.current'))

        # Sauvegarde : panneau + création fichier
        await page.click('#saveBtn'); await page.wait_for_timeout(300)
        await page.screenshot(path=f'{OUT}/02-panneau-sauvegarde.png')
        await page.click('[data-b="create"]'); await page.wait_for_timeout(1200)
        print('backup status', await page.evaluate('window.__atelier.Backup.status'), '|', await page.inner_text('#saveTxt'))

        # Aller page 9, nouvelle note avec / menu et markdown
        await page.fill('#pageInput', '9'); await page.press('#pageInput', 'Enter'); await page.wait_for_timeout(900)
        await page.keyboard.press('Alt+KeyN'); await page.wait_for_timeout(300)
        await page.keyboard.type('Approche évolutive : définition')
        await page.keyboard.press('Enter')
        await page.keyboard.type('/def'); await page.wait_for_timeout(250)
        await page.screenshot(path=f'{OUT}/03-menu-slash.png')
        await page.keyboard.press('Enter')
        await page.keyboard.type('Démarche proactive : déceler tôt, puis adapter dans la classe.')
        await page.keyboard.press('ArrowDown'); await page.keyboard.press('End')
        await page.keyboard.type('- identifier'); await page.keyboard.press('Enter'); await page.keyboard.type('adapter'); await page.keyboard.press('Enter'); await page.keyboard.press('Enter')
        await page.keyboard.type('[] relire le guide DAccE'); await page.wait_for_timeout(200)
        await page.keyboard.press('Enter'); await page.keyboard.press('Enter')
        await page.keyboard.type('Mot important ici')
        # surligner les 3 derniers mots via sélection
        await page.keyboard.down('Shift');
        for _ in range(9): await page.keyboard.press('ArrowLeft')
        await page.keyboard.up('Shift')
        await page.keyboard.press('Meta+Shift+KeyH') if sys.platform=='darwin' else await page.keyboard.press('Control+Shift+KeyH')
        await page.wait_for_timeout(300)
        # tableau via menu Insérer
        await page.keyboard.press('End'); await page.keyboard.press('Enter')
        await page.click('[data-dd="ddBlock"]'); await page.click('#ddBlock [data-ins="table"]')
        await page.keyboard.type('Traditionnel'); await page.keyboard.press('Tab'); await page.keyboard.type('Évolutif'); await page.keyboard.press('Tab'); await page.keyboard.type('réactif'); await page.keyboard.press('Tab'); await page.keyboard.type('proactif')
        await page.wait_for_timeout(500)
        # case à cocher : clic
        await page.evaluate('''() => { const li=document.querySelector('.note .body ul.check li'); if(!li) return; const r=li.getBoundingClientRect(); li.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,clientX:r.left-10,clientY:r.top+8})); }''')
        await page.wait_for_timeout(500)
        html = await page.evaluate('window.__atelier.S.doc.notes.at(-1).html')
        print('HTML note:', html[:900])
        await page.click('.note .chip >> text=À retenir')
        await page.screenshot(path=f'{OUT}/04-note-riche.png')

        # Surlignage dans le PDF
        pt = await sel_text(page, 9)
        await page.mouse.move(pt['x'], pt['y']);
        await page.evaluate('() => document.getElementById("viewer").dispatchEvent(new MouseEvent("mouseup",{bubbles:true}))')
        await page.wait_for_timeout(200)
        await page.screenshot(path=f'{OUT}/05-bulle-selection.png')
        await page.click('.bubble [data-h="green"]'); await page.wait_for_timeout(300)
        print('highlights', await page.evaluate('window.__atelier.S.doc.highlights.length'), await page.evaluate('document.querySelectorAll(".page[data-n=\\"9\\"] .hlLayer div").length'))
        # Surligner + note
        pt = await sel_text(page, 9, 40)
        await page.evaluate('() => document.getElementById("viewer").dispatchEvent(new MouseEvent("mouseup",{bubbles:true}))'); await page.wait_for_timeout(200)
        await page.click('.bubble [data-b="hlnote"]'); await page.wait_for_timeout(300)

        # Note épinglée
        await page.click('#annotBtn'); await page.click('#pinBtn'); await page.wait_for_timeout(200)
        box = await page.locator('.page[data-n="9"]').bounding_box()
        await page.mouse.click(box['x'] + box['width'] * 0.7, box['y'] + 160); await page.wait_for_timeout(400)
        await page.keyboard.type('Ici : le schéma clé')
        print('pins on p9', await page.evaluate('document.querySelectorAll(".page[data-n=\\"9\\"] .pin").length'))

        # Capture d'une zone
        await page.click('#annotBtn'); await page.click('#capBtn'); await page.wait_for_timeout(200)
        await page.mouse.move(box['x'] + 60, box['y'] + 120); await page.mouse.down(); await page.mouse.move(box['x'] + box['width'] - 60, box['y'] + 420, steps=6); await page.mouse.up()
        await page.wait_for_timeout(1500)
        imgs = await page.evaluate('window.__atelier.S.doc.notes.filter(n=>n.html.includes("<img")).length')
        print('notes with capture', imgs)
        await page.screenshot(path=f'{OUT}/06-epingle-capture.png')

        # Toutes les notes + recherche dans les notes
        await page.click('#tabAll'); await page.wait_for_timeout(300)
        await page.screenshot(path=f'{OUT}/07-toutes.png')
        await page.fill('#noteSearch', 'proactive'); await page.wait_for_timeout(500)
        print('search results', await page.evaluate('document.querySelectorAll("#notesList .note").length'))
        await page.click('#noteSearchClr')

        # Fiches
        await page.click('#modeSeg [data-mode="revise"]'); await page.click('#revMenuBtn'); await page.click('#cardsBtn'); await page.wait_for_timeout(300)
        await page.screenshot(path=f'{OUT}/08-fiches-accueil.png')
        await page.click('#fcSrc [data-v="all"]'); await page.click('#fcGo'); await page.wait_for_timeout(300)
        await page.keyboard.press('Space'); await page.wait_for_timeout(300)
        await page.screenshot(path=f'{OUT}/09-fiche.png')
        await page.keyboard.press('3'); await page.wait_for_timeout(200); await page.keyboard.press('Space'); await page.keyboard.press('1'); await page.wait_for_timeout(200)
        await page.keyboard.press('Escape')
        print('srs set', await page.evaluate('window.__atelier.S.doc.notes.filter(n=>n.srs).length'))

        # Progression
        await page.click('#modeSeg [data-mode="revise"]'); await page.click('#progBtn'); await page.wait_for_timeout(300)
        await page.screenshot(path=f'{OUT}/10-progression.png'); await page.keyboard.press('Escape')

        # Bibliothèque + recherche transversale
        await page.click('#coursBtn'); await page.click('#libBtn'); await page.wait_for_timeout(300)
        await page.fill('#libQ', 'redoublement'); await page.wait_for_timeout(300)
        await page.screenshot(path=f'{OUT}/11-bibliotheque.png'); await page.keyboard.press('Escape')

        # Exports
        async with page.expect_download() as d:
            await page.click('#expBtn'); await page.click('#ddExport [data-x="md"]')
        dl = await d.value; await dl.save_as(f'{OUT}/notes.md')
        async with page.expect_download() as d:
            await page.click('#expBtn'); await page.click('#ddExport [data-x="annot"]')
        dl = await d.value; await dl.save_as(f'{OUT}/annote.pdf')
        await page.click('#expBtn'); await page.click('#ddExport [data-x="sbs"]'); await page.wait_for_timeout(200)
        await page.click('#sbsGo'); await page.wait_for_function('window.__printed >= 1', timeout=30000)
        await page.emulate_media(media='print'); await page.pdf(path=f'{OUT}/cote-a-cote.pdf', prefer_css_page_size=True, print_background=True); await page.emulate_media(media='screen')
        await page.click('#expBtn'); await page.click('#ddExport [data-x="notes"]'); await page.wait_for_timeout(500)
        await page.emulate_media(media='print'); await page.pdf(path=f'{OUT}/notes-seules.pdf', prefer_css_page_size=True, print_background=True); await page.emulate_media(media='screen')

        # Fichier de sauvegarde sur « disque » (OPFS simulé)
        await page.wait_for_timeout(2500)
        content = await page.evaluate('window.__fileContent'); print('writes', await page.evaluate('window.__writes'))
        j = json.loads(content); print('backup file docs', len(j['docs']), 'notes', len(j['docs'][0]['notes']), 'hl', len(j['docs'][0]['highlights']), '|', await page.inner_text('#saveTxt'))

        # Réglages d'affichage : cahier, grande taille, sombre, PDF à droite
        await page.click('#viewBtn'); await page.wait_for_timeout(150)
        await page.screenshot(path=f'{OUT}/12-menu-affichage.png')
        await page.click('#segStyle [data-v="notebook"]'); await page.click('#segSize [data-v="16.5"]'); await page.click('#segSide [data-v="right"]')
        await page.keyboard.press('Escape'); await page.evaluate('document.getElementById("themeBtn").click()'); await page.wait_for_timeout(600)
        await page.click('#tabPage'); await page.wait_for_timeout(300)
        await page.screenshot(path=f'{OUT}/13-sombre-cahier.png')

        # Persistance après rechargement
        await page.reload(); await page.wait_for_timeout(2000)
        print('after reload docs', await page.evaluate('window.__atelier.S.docs.size'), 'status', await page.evaluate('window.__atelier.Backup.status'))
        await page.screenshot(path=f'{OUT}/14-accueil-reprendre.png')
        await page.set_input_files('#fileInput', PDF); await page.wait_for_selector('.page canvas', timeout=20000); await page.wait_for_timeout(1200)
        print('reopened notes', await page.evaluate('window.__atelier.S.doc.notes.length'), 'hl', await page.evaluate('window.__atelier.S.doc.highlights.length'), 'page', await page.evaluate('window.__atelier.S.current'))
        print('ERRORS', errs)
        await b.close()

asyncio.run(main())
