import asyncio, subprocess, time
from playwright.async_api import async_playwright
SYN='/home/claude/Synthese_DAP_S1_Introduction.pdf'; O='/home/claude/outil/shots15'
import os; os.makedirs(O, exist_ok=True)
async def run(b, url, tag):
    ctx=await b.new_context(viewport={'width':1366,'height':820}); await ctx.add_init_script('window.__noUnloadWarn=true')
    pg=await ctx.new_page(); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: errs.append(m.text) if m.type=='error' else None)
    await pg.goto(url); await pg.wait_for_timeout(1500)
    await pg.set_input_files('#fileInput', SYN); await pg.wait_for_selector('.page canvas'); await pg.wait_for_timeout(2000)
    n = await pg.evaluate('document.querySelectorAll(".tour-tip .dots i").length'); titles=[]
    for i in range(n):
        titles.append(await pg.evaluate('document.querySelector(".tour-tip h4").textContent'))
        act = await pg.evaluate('(document.querySelector(".tour-tip [data-t=act]")||{}).textContent||""')
        if i in (0, n-2, n-1): await pg.screenshot(path=f'{O}/{tag}-etape{i+1}.png')
        if i == 0 and act:
            await pg.click('.tour-tip [data-t=act]'); await pg.wait_for_timeout(300)
            vis = await pg.evaluate('(() => { const m=document.querySelector(".modal-back"); return m ? +getComputedStyle(m).zIndex : 0; })()')
            print(tag, 'installer → fenêtre au-dessus de la visite :', vis > 121); await pg.screenshot(path=f'{O}/{tag}-installer.png'); await pg.keyboard.press('Escape'); await pg.keyboard.press('Escape') if False else None
            if await pg.evaluate('!!document.querySelector(".modal-back")'): await pg.click('.modal [data-close]')
        if i < n-1: await pg.click('.tour-tip [data-t=next]'); await pg.wait_for_timeout(250)
    act = await pg.evaluate('(document.querySelector(".tour-tip [data-t=act]")||{}).textContent||""')
    await pg.click('.tour-tip [data-t=act]'); await pg.wait_for_timeout(400)
    print(tag, n, 'étapes :', titles)
    print(tag, 'dernière étape → bouton', act, '→', await pg.evaluate('(document.querySelector(".modal-h h3")||{}).textContent'), '; visite terminée :', await pg.evaluate('!document.querySelector(".tour-tip")'))
    print(tag, 'erreurs', errs); await ctx.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8765','--bind','127.0.0.1'], cwd='/home/claude/outil/web', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch()
            await run(b, 'file:///home/claude/outil/Atelier-etude.html', 'fichier')
            await run(b, 'http://127.0.0.1:8765/', 'enligne')
            await b.close()
    finally: srv.terminate()
asyncio.run(main())
