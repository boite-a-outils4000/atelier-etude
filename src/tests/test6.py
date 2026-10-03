import asyncio, json, os
from playwright.async_api import async_playwright
APP='file:///home/claude/outil/Atelier-etude.html'; SYN='/home/claude/Synthese_DAP_S1_Introduction.pdf'; V2='/home/claude/outil/v2pdf/Synthese_DAP_S1_Introduction.pdf'; OUT='/home/claude/outil/shots6'; os.makedirs(OUT, exist_ok=True)
DIRMOCK = '''
window.__noUnloadWarn = true; window.__files = {};
const mkFile = (path) => ({ kind:'file', name: path.split('/').pop(), getFile: async () => new File([window.__files[path]||''], path), createWritable: async () => { let b=''; return { write: async d => { b += d; }, close: async () => { window.__files[path] = b; } }; }, queryPermission: async()=>'granted', requestPermission: async()=>'granted' });
const mkDir = (path) => ({ kind:'directory', name: path.split('/').pop() || 'Sauvegardes', queryPermission: async()=>'granted', requestPermission: async()=>'granted',
  getFileHandle: async (n, o) => { const p = path + '/' + n; if (!(p in window.__files) && !(o && o.create)) { const e = new Error('nf'); e.name='NotFoundError'; throw e; } if (!(p in window.__files)) window.__files[p] = ''; return mkFile(p); },
  getDirectoryHandle: async (n) => mkDir(path + '/' + n),
  keys: async function* () { for (const k of Object.keys(window.__files)) if (k.startsWith(path + '/') && !k.slice(path.length+1).includes('/')) yield k.slice(path.length+1); },
  removeEntry: async (n) => { delete window.__files[path + '/' + n]; } });
window.showDirectoryPicker = async () => mkDir('Sauvegardes');
(()=>{try{const p=JSON.parse(localStorage.getItem('etude.prefs')||'{}');p.sbTab='pages';localStorage.setItem('etude.prefs',JSON.stringify(p));}catch(e){}})();
'''
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1440,'height':900}, accept_downloads=True); await ctx.add_init_script(DIRMOCK); page=await ctx.new_page()
        errs=[]; page.on('pageerror', lambda e: errs.append(str(e))); page.on('console', lambda m: errs.append(m.text) if m.type=='error' else None)
        await page.goto(APP); await page.wait_for_timeout(1000)
        await page.set_input_files('#fileInput', SYN); await page.wait_for_selector('.page canvas'); await page.wait_for_timeout(1300)
        # 1. visite guidée
        print('tour', await page.evaluate('!!document.querySelector(".tour-tip")'))
        await page.screenshot(path=f'{OUT}/01-visite.png')
        for i in range(2): await page.click('.tour-tip [data-t="next"]'); await page.wait_for_timeout(250)
        await page.screenshot(path=f'{OUT}/02-visite-3.png')
        for i in range(3): await page.click('.tour-tip [data-t="next"]'); await page.wait_for_timeout(150)
        print('tour done', await page.evaluate('!document.querySelector(".tour-tip")'))
        # 2. modèles
        await page.fill('#pageInput','5'); await page.press('#pageInput','Enter'); await page.wait_for_timeout(800)
        await page.click('[data-dd="ddTpl"]'); await page.click('#ddTpl [data-tpl="cornell"]'); await page.wait_for_timeout(300)
        await page.keyboard.type('Pourquoi 35 % ?'); await page.keyboard.press('Tab')
        await page.evaluate('() => { const n=document.querySelector(".body .c-n"); const r=document.createRange(); r.selectNodeContents(n); r.collapse(true); const s=getSelection(); n.closest(".body").focus(); s.removeAllRanges(); s.addRange(r); }')
        await page.keyboard.type('Redoublement très élevé en FWB.')
        await page.click('[data-dd="ddTpl"]'); await page.click('#ddTpl [data-tpl="concept"]'); await page.keyboard.type('équité'); await page.wait_for_timeout(200)
        await page.click('[data-dd="ddTpl"]'); await page.click('#ddTpl [data-tpl="question"]'); await page.keyboard.type('Quels sont les 6 enseignements ?'); await page.wait_for_timeout(300)
        notes = await page.evaluate('window.__atelier.S.doc.notes.map(n=>({t:n.title, cornell:n.html.includes("cornell"), srs:!!n.srs}))')
        print('templates', notes)
        await page.screenshot(path=f'{OUT}/03-modeles.png')
        await page.fill('#pageInput','9'); await page.press('#pageInput','Enter'); await page.wait_for_timeout(800)
        await page.click('#quick'); await page.keyboard.type('Leviers : AP + suivi + DAccE'); await page.keyboard.press('Enter'); await page.wait_for_timeout(200)
        # surlignage p.9
        await page.evaluate('() => { const sp=[...document.querySelectorAll(".page[data-n=\\"9\\"] .textLayer span")].find(s=>s.textContent.trim().length>25); const r=document.createRange(); r.selectNodeContents(sp); const s=getSelection(); s.removeAllRanges(); s.addRange(r); document.getElementById("viewer").dispatchEvent(new MouseEvent("mouseup",{bubbles:true})); }'); await page.wait_for_timeout(200)
        await page.click('.bubble [data-h="yellow"]')
        # 3. glisser-déposer vers une vignette + fusion
        await page.click('#thumbsBtn'); await page.wait_for_timeout(800)
        await page.fill('#pageInput','5'); await page.press('#pageInput','Enter'); await page.wait_for_timeout(800)
        await page.drag_and_drop('.notes-list .note >> nth=2 >> .grip', '.thumb[data-n="12"]'); await page.wait_for_timeout(400)
        print('after drag to thumb', await page.evaluate('window.__atelier.S.doc.notes.map(n=>[n.title.slice(0,20), n.page])'))
        await page.drag_and_drop('.notes-list .note >> nth=1 >> .grip', '.notes-list .note >> nth=0'); await page.wait_for_timeout(300)
        print('order p5', await page.evaluate('[...document.querySelectorAll(".notes-list .note .note-title")].map(x=>x.value)'))
        await page.click('.notes-list .note >> nth=0 >> .more'); await page.click('#ddNote [data-a="merge"]'); await page.wait_for_timeout(300)
        print('after merge p5', await page.evaluate('window.__atelier.S.doc.notes.filter(n=>n.page===5).length'))
        # 4. confort
        await page.click('#viewBtn'); await page.click('#segUi [data-v="1.1"]'); await page.click('#segFont [data-v="dys"]'); await page.check('#optHc'); await page.wait_for_timeout(300)
        await page.screenshot(path=f'{OUT}/04-confort.png'); await page.keyboard.press('Escape')
        await page.click('#viewBtn'); await page.click('#segUi [data-v="1"]'); await page.click('#segFont [data-v="sans"]'); await page.uncheck('#optHc'); await page.keyboard.press('Escape')
        # 5. lecture
        await page.keyboard.press('Alt+KeyL'); await page.wait_for_timeout(900)
        print('reading', await page.evaluate('document.body.classList.contains("reading")'), 'scale', await page.evaluate('window.__atelier.S.scale.toFixed(2)'))
        await page.keyboard.press('ArrowRight'); await page.wait_for_timeout(600)
        await page.mouse.move(700,500); await page.wait_for_timeout(200)
        await page.screenshot(path=f'{OUT}/05-lecture.png')
        await page.keyboard.press('Escape'); await page.wait_for_timeout(500)
        print('reading off', await page.evaluate('!document.body.classList.contains("reading")'))
        # 6. sauvegarde dossier + historique
        await page.click('#saveBtn'); await page.wait_for_timeout(500); await page.screenshot(path=f'{OUT}/06-sauvegarde.png')
        await page.click('[data-b="dir"]'); await page.wait_for_timeout(1500)
        print('files', await page.evaluate('Object.keys(window.__files)'), await page.inner_text('#saveTxt'))
        # 7. nouvelle version du PDF
        await page.wait_for_timeout(1500)
        await page.set_input_files('#fileInput', V2); await page.wait_for_timeout(3500)
        print('version modal', await page.evaluate('document.querySelector(".modal-h h3")?.textContent'))
        await page.screenshot(path=f'{OUT}/07-nouvelle-version.png')
        await page.click('[data-v="yes"]'); await page.wait_for_timeout(1200)
        await page.screenshot(path=f'{OUT}/08-transfert.png')
        print('transferred', await page.evaluate('window.__atelier.S.doc.notes.map(n=>[n.title.slice(0,18), n.page, !!n.moved])'), 'hl', await page.evaluate('window.__atelier.S.doc.highlights.map(h=>h.page)'))
        await page.keyboard.press('Escape')
        # 8. historique : restaurer
        await page.reload(); await page.wait_for_timeout(1500)
        await page.click('#saveBtn'); await page.wait_for_timeout(800)
        print('hist rows', await page.evaluate('document.querySelectorAll(".hist-row").length'))
        await page.screenshot(path=f'{OUT}/09-historique.png')
        print('ERRORS', errs); await b.close()
asyncio.run(main())
