import asyncio, subprocess, time, os, shutil, glob
from playwright.async_api import async_playwright
SITE = '/home/claude/whisper/site'; D = '/home/claude/outil/docx_t/'; OUT = '/home/claude/outil/shots31'; os.makedirs(OUT, exist_ok=True)
shutil.copy('/home/claude/outil/web/index.html', SITE + '/index.html'); shutil.copy('/home/claude/outil/web/sw.js', SITE + '/sw.js')
R = []
def ok(name, cond, extra=''):
    R.append((name, bool(cond))); print(('OK  ' if cond else 'ÉCHEC ') + name, extra, flush=True)
INIT = 'window.__noUnloadWarn=true; delete window.showOpenFilePicker; (()=>{try{const p=JSON.parse(localStorage.getItem("etude.prefs")||"{}");p.tourDone=true;localStorage.setItem("etude.prefs",JSON.stringify(p));}catch(e){}})();'
TXT = '''(async () => { const pdf = __atelier.S.pdf; let out = []; for (let i = 1; i <= pdf.numPages; i++) { const tc = await (await pdf.getPage(i)).getTextContent(); out.push(tc.items.map(x => x.str + (x.hasEOL ? "\\n" : " ")).join("")); } return out.join("\\n=====\\n"); })()'''
EXPECT = {'riche.docx': ['Chapitre 2', 'sous-sous-point', 'Wallonie', 'Ceci est une note de bas de page', 'RTBF', 'union fait la force'],
          'riche_lo.docx': ['Chapitre 2', 'sous-point A', 'Charleroi', 'note de bas de page'],
          'footnotes.docx': ['Ouch'], 'tables.docx': ['Top left'], 'text-box.docx': [], 'empty.docx': [], 'footnote-hyperlink.docx': [], 'simple-list.docx': ['Apple']}
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8814', '--bind', '127.0.0.1'], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); await ctx.add_init_script(INIT)
            pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: print('CONSOLE', m.text[:400]) if m.type == 'error' else None); ev = pg.evaluate
            await pg.goto('http://127.0.0.1:8814/'); await pg.wait_for_timeout(1000)
            for f, exp in EXPECT.items():
                n0 = await ev('__atelier.S.tabs.length')
                await pg.set_input_files('#fileInput', D + f); await pg.wait_for_timeout(2500)
                st = await ev('({ tabs: __atelier.S.tabs.length, title: __atelier.S.doc && __atelier.S.doc.title, pages: __atelier.S.pdf && __atelier.S.pdf.numPages })')
                t = await ev(TXT) if st["pages"] else ""
                if not st["pages"]: print("toast:", await ev("document.getElementById(\"toast\").textContent"))
                miss = [e for e in exp if e not in t]
                ok(f'{f} : ouvert, texte attendu présent', st['tabs'] == n0 + 1 and not miss, (st, miss, t[:200].replace('\n', ' ')))
                await pg.wait_for_timeout(700); await pg.screenshot(path=OUT + '/' + f.replace('.docx', '.png'))
                if st['tabs'] >= 6: await ev('Promise.all(__atelier.S.tabs.slice(0, 3).map(() => 0))')
            ok('aucune erreur JS', not errs, errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print(f'{sum(1 for _, c in R if c)}/{len(R)} OK')
asyncio.run(main())
