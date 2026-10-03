import asyncio, json, os
from playwright.async_api import async_playwright
APP='file:///home/claude/outil/Atelier-etude.html'; SYN='/home/claude/Synthese_DAP_S1_Introduction.pdf'; COURS='/home/claude/outil/cours.pdf'; OUT='/home/claude/outil/shots5'; os.makedirs(OUT, exist_ok=True)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1440,'height':900}, accept_downloads=True); await ctx.add_init_script('window.__noUnloadWarn=true; (()=>{try{const p=JSON.parse(localStorage.getItem("etude.prefs")||"{}");p.tourDone=true;p.sbTab="pages";localStorage.setItem("etude.prefs",JSON.stringify(p));}catch(e){}})(); window.print=()=>{window.__printed=(window.__printed||0)+1};'); page=await ctx.new_page()
        errs=[]; page.on('pageerror', lambda e: errs.append(str(e))); page.on('console', lambda m: errs.append(m.text) if m.type=='error' else None)
        await page.goto(APP); await page.wait_for_timeout(1000)
        # 1. onglets : ouvrir le cours puis la synthèse
        await page.set_input_files('#fileInput', COURS); await page.wait_for_selector('.page canvas', timeout=60000); await page.wait_for_timeout(800)
        await page.set_input_files('#fileInput', SYN); await page.wait_for_timeout(2500)
        print('tabs', await page.evaluate('[...document.querySelectorAll(".dtab span")].map(x=>x.textContent)'), 'active', await page.evaluate('window.__atelier.S.doc.title'))
        # 2. note rapide
        await page.fill('#pageInput','5'); await page.press('#pageInput','Enter'); await page.wait_for_timeout(800)
        await page.click('#quick'); await page.keyboard.type('Redoublement 35 % en FWB'); await page.keyboard.press('Enter'); await page.wait_for_timeout(300)
        await page.keyboard.type('Équité en progrès'); await page.keyboard.down('Shift'); await page.keyboard.press('Enter'); await page.keyboard.up('Shift'); await page.keyboard.type('mais écarts liés au parcours'); await page.keyboard.press('Enter'); await page.wait_for_timeout(300)
        print('quick notes', await page.evaluate('window.__atelier.S.doc.notes.map(n=>[n.page,n.title,n.html])'), 'focus still quick', await page.evaluate('document.activeElement.id'))
        # 3. éditer une note puis faire défiler le PDF : la note reste
        await page.click('.notes-list .note .body >> nth=0'); await page.keyboard.type(' — à retenir')
        await page.evaluate('document.getElementById("viewer").scrollTop += 2500'); await page.wait_for_timeout(800)
        print('notice', await page.evaluate('!!document.getElementById("pageNotice")'), 'still editing', await page.evaluate('document.activeElement.classList.contains("body")'))
        await page.screenshot(path=f'{OUT}/01-notice.png')
        # mini-barre sur sélection
        await page.evaluate('() => { const b=document.activeElement; const r=document.createRange(); r.selectNodeContents(b); const s=getSelection(); s.removeAllRanges(); s.addRange(r); }'); await page.wait_for_timeout(200)
        print('selbar', await page.evaluate('!!document.querySelector(".selbar")'))
        await page.screenshot(path=f'{OUT}/02-selbar.png')
        await page.click('.selbar [data-h="#a6e3a1"]'); await page.wait_for_timeout(200)
        await page.keyboard.press('Escape'); await page.wait_for_timeout(500)
        print('notice gone', await page.evaluate('!document.getElementById("pageNotice")'), 'focus', await page.evaluate('document.activeElement.id'))
        # 4. vignettes
        await page.click('#thumbsBtn'); await page.wait_for_timeout(1500)
        print('thumbs', await page.evaluate('document.querySelectorAll(".thumb").length'), 'rendered', await page.evaluate('document.querySelectorAll(".thumb canvas").length'), 'badge', await page.evaluate('document.querySelectorAll(".thumb .nb").length'))
        await page.click('.thumb[data-n="9"]'); await page.wait_for_timeout(900)
        print('cur after thumb', await page.evaluate('window.__atelier.S.current'))
        await page.screenshot(path=f'{OUT}/03-vignettes.png')
        # 5. dessin
        await page.click('#annotBtn'); await page.click('#drawBtn'); await page.wait_for_timeout(200)
        box = await page.locator('.page[data-n="9"]').bounding_box()
        y0 = max(box['y']+80, 140)
        await page.mouse.move(box['x']+100, y0); await page.mouse.down()
        for i in range(25): await page.mouse.move(box['x']+100+i*12, y0+ (i%5)*6)
        await page.mouse.up(); await page.wait_for_timeout(200)
        await page.click('.drawbar [data-mk="#ffd84d"]')
        await page.mouse.move(box['x']+120, y0+60); await page.mouse.down(); await page.mouse.move(box['x']+420, y0+60, steps=10); await page.mouse.up(); await page.wait_for_timeout(200)
        print('ink', await page.evaluate('window.__atelier.S.doc.ink.length'), 'paths', await page.evaluate('document.querySelectorAll(".page[data-n=\\"9\\"] .inkLayer path").length'))
        await page.screenshot(path=f'{OUT}/04-dessin.png')
        await page.keyboard.press('Control+KeyZ'); await page.wait_for_timeout(200)
        print('after undo', await page.evaluate('window.__atelier.S.doc.ink.length'))
        await page.click('.drawbar [data-a="erase"]'); await page.mouse.move(box['x']+160, y0+10); await page.mouse.down(); await page.mouse.move(box['x']+260, y0+15, steps=8); await page.mouse.up(); await page.wait_for_timeout(200)
        print('after erase', await page.evaluate('window.__atelier.S.doc.ink.length'))
        await page.keyboard.press('Control+KeyZ'); await page.click('.drawbar [data-a="done"]')
        # 6. côte à côte : ouvrir le cours comme référence
        await page.set_input_files('#refInput', COURS); await page.wait_for_timeout(3000)
        print('ref pages', await page.evaluate('document.querySelectorAll("#refPages .page").length'), 'ref canvases', await page.evaluate('document.querySelectorAll("#refPages canvas").length'))
        await page.screenshot(path=f'{OUT}/05-cote-a-cote.png')
        await page.evaluate('() => { const sp=[...document.querySelectorAll("#refPages .textLayer span")].find(s=>s.textContent.trim().length>15); const r=document.createRange(); r.selectNodeContents(sp); const s=getSelection(); s.removeAllRanges(); s.addRange(r); document.getElementById("refViewer").dispatchEvent(new MouseEvent("mouseup",{bubbles:true})); }'); await page.wait_for_timeout(200)
        await page.click('.bubble [data-b="note"]'); await page.wait_for_timeout(300)
        print('ref quote', await page.evaluate('window.__atelier.S.doc.notes.at(-1).html.slice(0,200)'))
        await page.click('#refLayout'); await page.wait_for_timeout(800); await page.screenshot(path=f'{OUT}/06-dessous.png'); await page.click('#refLayout')
        await page.click('#refClose'); await page.wait_for_timeout(300)
        # 7. changer d'onglet et revenir
        await page.keyboard.press('Alt+Digit1'); await page.wait_for_timeout(1500); print('active after alt1', await page.evaluate('window.__atelier.S.doc.title'))
        await page.keyboard.press('Alt+Digit2'); await page.wait_for_timeout(1500); print('active after alt2', await page.evaluate('window.__atelier.S.doc.title'), 'page', await page.evaluate('window.__atelier.S.current'))
        # 8. export côte à côte avec dessin
        await page.click('#expBtn'); await page.click('#ddExport [data-x="sbs"]'); await page.click('#sbsGo'); await page.wait_for_function('window.__printed>=1', timeout=30000)
        await page.emulate_media(media='print'); await page.pdf(path=f'{OUT}/sbs.pdf', prefer_css_page_size=True, print_background=True); await page.emulate_media(media='screen')
        async with page.expect_download() as d: await page.click('#expBtn'); await page.click('#ddExport [data-x="annot"]')
        dl=await d.value; await dl.save_as(f'{OUT}/annote.pdf')
        # filtres
        await page.click('#filtBtn'); await page.wait_for_timeout(150); await page.screenshot(path=f'{OUT}/07-filtres.png'); await page.keyboard.press('Escape')
        # 9. fermer les onglets
        await page.click('#coursBtn'); await page.click('#ddCours [data-c="close"]'); await page.wait_for_timeout(1200); print('tabs after close', await page.evaluate('window.__atelier.S.tabs.length'), await page.evaluate('window.__atelier.S.doc && window.__atelier.S.doc.title'))
        await page.click('#coursBtn'); await page.click('#ddCours [data-c="close"]'); await page.wait_for_timeout(500); print('welcome visible', await page.evaluate('!document.getElementById("welcome").classList.contains("hidden")'))
        await page.screenshot(path=f'{OUT}/08-accueil.png')
        # persistance
        await page.wait_for_timeout(600); await page.reload(); await page.wait_for_timeout(1500)
        await page.set_input_files('#fileInput', SYN); await page.wait_for_selector('.page canvas'); await page.wait_for_timeout(1200)
        print('reload ink', await page.evaluate('window.__atelier.S.doc.ink.length'), 'notes', await page.evaluate('window.__atelier.S.doc.notes.length'), 'thumbs pref', await page.evaluate('document.querySelectorAll(".thumb").length'))
        print('ERRORS', errs); await b.close()
asyncio.run(main())
