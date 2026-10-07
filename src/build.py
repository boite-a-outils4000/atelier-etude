# Assemble Atelier-etude.html à partir de source.html (polices et bibliothèques intégrées).
import base64, os, sys
H = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(H, 'fonts')
fonts = [("Nunito",700,"normal","nunito-latin-700-normal.woff"),("Nunito",800,"normal","nunito-latin-800-normal.woff"),("Source Sans 3",400,"normal","source-sans-3-latin-400-normal.woff"),("Source Sans 3",400,"italic","source-sans-3-latin-400-italic.woff"),("Source Sans 3",600,"normal","source-sans-3-latin-600-normal.woff"),("Source Sans 3",700,"normal","source-sans-3-latin-700-normal.woff"),("Atkinson Hyperlegible",400,"normal","atkinson-hyperlegible-latin-400-normal.woff"),("Atkinson Hyperlegible",700,"normal","atkinson-hyperlegible-latin-700-normal.woff"),("OpenDyslexic",400,"normal","opendyslexic-latin-400-normal.woff"),("OpenDyslexic",700,"normal","opendyslexic-latin-700-normal.woff")]
css = ''.join(f'@font-face{{font-family:"{n}";font-weight:{w};font-style:{s};font-display:swap;src:url(data:font/woff;base64,{base64.b64encode(open(os.path.join(F,p),"rb").read()).decode()}) format("woff");}}\n' for n,w,s,p in fonts)
s = open(os.path.join(H,'source.html'), encoding='utf-8').read()
parts = {'/*FONTS*/': css, '/*WORKER*/': open(os.path.join(H,'vendor/pdfjs/pdf.worker.min.js'),encoding='utf-8').read(), '/*PDFJS*/': open(os.path.join(H,'vendor/pdfjs/pdf.min.js'),encoding='utf-8').read(), '/*PDFLIB*/': open(os.path.join(H,'vendor/pdflib/pdf-lib.min.js'),encoding='utf-8').read(), '/*MAMMOTH*/': open(os.path.join(H,'vendor/mammoth/mammoth.browser.min.js'),encoding='utf-8').read()}
for k, v in parts.items():
    assert s.count(k) == 1, k
    i = s.index(k); s = s[:i] + v + s[i+len(k):]
# ---------- Fichier autonome + version en ligne installable (dossier web/) ----------
import hashlib, json as _json
V = hashlib.sha1(s.encode('utf-8')).hexdigest()[:10]
OUTF = os.path.join(H, 'Atelier-etude.html'); open(OUTF, 'w', encoding='utf-8').write(s.replace('<!--PWA-->', '')); print(os.path.getsize(OUTF)//1024, 'Ko')
if True:
    import shutil; os.chdir(H)
    os.makedirs('web', exist_ok=True)
    for f in os.listdir('icons'): shutil.copy(os.path.join('icons', f), 'web')
    head = ('<link rel="manifest" href="manifest.webmanifest">\n<meta name="theme-color" content="#f6f6f5" media="(prefers-color-scheme: light)">\n'
            '<meta name="theme-color" content="#232426" media="(prefers-color-scheme: dark)">\n<link rel="icon" type="image/png" href="favicon.png">\n'
            '<link rel="apple-touch-icon" href="apple-touch-icon.png">\n<meta name="apple-mobile-web-app-title" content="Atelier">\n<meta name="mobile-web-app-capable" content="yes">\n'
            '<meta name="description" content="Lire un cours en PDF, prendre des notes à côté et réviser. Fonctionne hors ligne, sans compte : tes notes restent chez toi.">')
    open('web/index.html', 'w', encoding='utf-8').write(s.replace('<!--PWA-->', head))
    man = {"name": "Atelier d'étude", "short_name": "Atelier", "id": "./", "start_url": "./", "scope": "./", "display": "standalone", "display_override": ["window-controls-overlay", "standalone"],
           "background_color": "#f4f4f3", "theme_color": "#23807a", "lang": "fr", "dir": "ltr", "description": "Ton cours en PDF à gauche, tes notes à droite. Hors ligne et sans compte.",
           "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}, {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
           "file_handlers": [{"action": "./", "accept": {"application/pdf": [".pdf"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"]}}],
           "categories": ["education", "productivity"]}
    open('web/manifest.webmanifest', 'w', encoding='utf-8').write(_json.dumps(man, ensure_ascii=False, indent=1))
    sw = """// Atelier d'étude — fonctionnement hors ligne. Version : %s
const CACHE = 'atelier-%s';
const FILES = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'apple-touch-icon.png', 'favicon.png'];
self.addEventListener('install', (e) => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES))); });
self.addEventListener('activate', (e) => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith('atelier-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('message', (e) => { if (e.data === 'skip') self.skipWaiting(); });
self.addEventListener('fetch', (e) => {
  const req = e.request; if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  e.respondWith(caches.match(req, { ignoreSearch: true }).then(hit => hit || fetch(req).catch(() => req.mode === 'navigate' ? caches.match('index.html') : Response.error())));
});
""" % (V, V)
    open('web/sw.js', 'w', encoding='utf-8').write(sw)
    print('web/ prêt, version', V)
