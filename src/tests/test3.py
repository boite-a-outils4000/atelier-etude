import asyncio, json, os
from playwright.async_api import async_playwright

APP = 'file:///home/claude/outil/Atelier-etude.html'
PDF = '/home/claude/Synthese_DAP_S1_Introduction.pdf'
OUT = '/home/claude/outil/shots3'
os.makedirs(OUT, exist_ok=True)

async def span_pos(page, n, pred):
    return await page.evaluate('''([n, pred]) => { const sps=[...document.querySelectorAll(`.page[data-n="${n}"] .textLayer span`)]; const sp = sps.find(s => new Function('s', 'return ' + pred)(s)); if(!sp) return null; sp.scrollIntoView({block:'center'}); const b=sp.getBoundingClientRect(); return {x:b.left+Math.min(30,b.width/2), y:b.top+b.height/2, t:sp.textContent, fs: sp.style.fontSize}; }''', [n, pred])

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=1)
        await ctx.add_init_script('window.__noUnloadWarn = true; (()=>{try{const p=JSON.parse(localStorage.getItem("etude.prefs")||"{}");p.tourDone=true;localStorage.setItem("etude.prefs",JSON.stringify(p));}catch(e){}})();')
        page = await ctx.new_page()
        errs = []
        page.on('console', lambda m: errs.append(f'{m.type}: {m.text}') if m.type == 'error' else None)
        page.on('pageerror', lambda e: errs.append('PAGEERROR ' + str(e)))
        await page.goto(APP); await page.wait_for_timeout(1200)
        await page.set_input_files('#fileInput', PDF)
        await page.wait_for_selector('.page canvas', timeout=20000); await page.wait_for_timeout(800)
        await page.fill('#pageInput', '9'); await page.press('#pageInput', 'Enter'); await page.wait_for_timeout(1500)
        print('img boxes p9', await page.evaluate('window.__atelier.S.pages[8].imgBoxes'))
        await page.click('#annotBtn'); await page.click('#linkBtn'); await page.wait_for_timeout(200)
        # 1. titre
        t = await span_pos(page, 9, "s.textContent.includes('4.4 Les leviers')")
        print('title span', t)
        await page.mouse.move(t['x'], t['y']); await page.wait_for_timeout(150)
        await page.screenshot(path=f'{OUT}/01-survol-titre.png')
        await page.mouse.click(t['x'], t['y']); await page.wait_for_timeout(500)
        last = await page.evaluate('window.__atelier.S.doc.notes.at(-1)')
        print('1 title note:', last['title'], '|', last['html'][:160])
        # 2. phrase
        t = await span_pos(page, 9, "s.textContent.includes('trois leviers')")
        await page.mouse.click(t['x'], t['y']); await page.wait_for_timeout(500)
        # 3. mot (shift)
        t = await span_pos(page, 9, "s.textContent.includes('collaboratif')")
        await page.evaluate('([x,y]) => {}', [t['x'], t['y']])
        pos = await page.evaluate('''() => { const sp=[...document.querySelectorAll('.page[data-n="9"] .textLayer span')].find(s=>s.textContent.includes('collaboratif')); const tn=sp.firstChild; const i=tn.data.indexOf('collaboratif'); const r=document.createRange(); r.setStart(tn,i+2); r.setEnd(tn,i+3); const b=r.getBoundingClientRect(); return {x:b.left+1,y:b.top+b.height/2}; }''')
        await page.keyboard.down('Shift'); await page.mouse.move(pos['x'], pos['y']); await page.mouse.click(pos['x'], pos['y']); await page.keyboard.up('Shift'); await page.wait_for_timeout(500)
        # 4. image
        bx = await page.evaluate('''() => { const p=window.__atelier.S.pages[8]; const b=(p.imgBoxes||[])[0]; if(!b) return null; p.div.scrollIntoView(); const r=p.div.getBoundingClientRect(); window.scrollTo(0,0); return b; }''')
        await page.wait_for_timeout(300)
        if bx:
            await page.evaluate('() => { const p=window.__atelier.S.pages[8]; const b=p.imgBoxes[0]; const v=document.getElementById("viewer"); v.scrollTop = p.div.offsetTop + b.y*p.div.offsetHeight - 100; }'); await page.wait_for_timeout(500)
            r = await page.evaluate('() => { const p=window.__atelier.S.pages[8]; const b=p.imgBoxes[0]; const r=p.div.getBoundingClientRect(); return {x:r.left+(b.x+b.w*0.5)*r.width, y:r.top+(b.y+b.h*0.5)*r.height}; }')
            await page.mouse.move(r['x'], r['y']); await page.wait_for_timeout(150)
            await page.screenshot(path=f'{OUT}/02-survol-image.png')
            await page.mouse.click(r['x'], r['y']); await page.wait_for_timeout(1500)
        # 5. zone (glisser)
        r = await page.evaluate('() => { const r=document.querySelector(\'.page[data-n="9"]\').getBoundingClientRect(); return {x:r.left, y:Math.max(r.top,60), w:r.width}; }')
        await page.mouse.move(r['x'] + 60, r['y'] + 80); await page.mouse.down(); await page.mouse.move(r['x'] + 300, r['y'] + 220, steps=6); await page.mouse.up(); await page.wait_for_timeout(1500)
        await page.keyboard.press('Escape')
        # 6. ⌥ + clic hors mode
        t = await span_pos(page, 9, "s.textContent.includes('Implications') || s.textContent.includes('implications')")
        if t:
            await page.keyboard.down('Alt'); await page.mouse.click(t['x'], t['y']); await page.keyboard.up('Alt'); await page.wait_for_timeout(500)
        st = await page.evaluate('({anchors: window.__atelier.S.doc.anchors.map(a=>a.kind+":"+a.text.slice(0,30)), notes: window.__atelier.S.doc.notes.map(n=>({t:n.title, links:(n.html.match(/data-a=/g)||[]).length, imgs:(n.html.match(/<img/g)||[]).length}))})')
        print('2-6 state', json.dumps(st, ensure_ascii=False))
        print('anc drawn p9', await page.evaluate('document.querySelectorAll(\'.page[data-n="9"] .anc\').length'), 'tags', await page.evaluate('document.querySelectorAll(\'.page[data-n="9"] .anc-tag\').length'))
        await page.screenshot(path=f'{OUT}/03-apres-association.png')
        # 7. sélection + Associer
        await page.evaluate('''() => { const sp=[...document.querySelectorAll('.page[data-n="9"] .textLayer span')].find(s=>s.textContent.trim().length>30); const r=document.createRange(); r.selectNodeContents(sp); const s=getSelection(); s.removeAllRanges(); s.addRange(r); document.getElementById('viewer').dispatchEvent(new MouseEvent('mouseup',{bubbles:true})); }''')
        await page.wait_for_timeout(200)
        await page.click('.bubble [data-b="link"]'); await page.wait_for_timeout(500)
        print('anchors after selection', await page.evaluate('window.__atelier.S.doc.anchors.length'))
        # 8. clic sur une étiquette dans la note → le PDF va à l'endroit
        await page.click('#tabAll'); await page.wait_for_timeout(200)
        await page.evaluate('document.getElementById("viewer").scrollTop = 0'); await page.wait_for_timeout(500)
        await page.click('.notes-list .lnk >> nth=1'); await page.wait_for_timeout(1200)
        print('current after chip click', await page.evaluate('window.__atelier.S.current'))
        await page.screenshot(path=f'{OUT}/04-clic-etiquette.png')
        # 9. clic sur ↗ dans le PDF
        await page.click('.page[data-n="9"] .anc-tag >> nth=1'); await page.wait_for_timeout(600)
        await page.screenshot(path=f'{OUT}/05-clic-ancre.png')
        import re
        h = await page.evaluate('window.__atelier.S.doc.notes.find(n=>n.title.startsWith("4.4")).html')
        print('ORDER', re.sub(r'src="data:[^"]+"','src=…',h))
        # 10. rechargement
        await page.wait_for_timeout(800)
        await page.reload(); await page.wait_for_timeout(1500)
        await page.set_input_files('#fileInput', PDF); await page.wait_for_selector('.page canvas', timeout=20000); await page.wait_for_timeout(1500)
        print('after reload anchors', await page.evaluate('window.__atelier.S.doc.anchors.length'), 'drawn', await page.evaluate('document.querySelectorAll(\'.page[data-n="9"] .anc\').length'))
        await page.screenshot(path=f'{OUT}/06-recharge.png')
        print('ERRORS', errs)
        await b.close()

asyncio.run(main())
