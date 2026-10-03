# Atelier d'étude

Ton cours en PDF à gauche, tes notes à droite. Annoter, prendre des notes, enregistrer et transcrire le cours, réviser (QCM à degrés de certitude, séance du jour, bilan), travailler à plusieurs.

**Utiliser l'application : https://boite-a-outils4000.github.io/atelier-etude/**

Tout fonctionne dans le navigateur, hors ligne et sans compte : les notes restent sur l'ordinateur de chaque personne. Ce dépôt ne contient que l'outil.

La transcription du cours utilise Whisper (OpenAI, licence MIT) via Transformers.js (Hugging Face, Apache 2.0), exécuté dans le navigateur : le son n'est envoyé nulle part. Le modèle est téléchargé une seule fois depuis Hugging Face.

## Contenu du dépôt

- `index.html`, `sw.js`, `manifest.webmanifest`, icônes : l'application publiée (GitHub Pages).
- `src/` : les sources.
  - `source.html` : le code de l'application ;
  - `build.py` : assemble le fichier autonome `Atelier-etude.html` et le dossier `web/` publiable ;
  - `fonts/` : Nunito, Source Sans 3, Atkinson Hyperlegible, OpenDyslexic (licence SIL OFL) ;
  - `vendor/` : pdf.js 3.11.174 (Mozilla, Apache 2.0) et pdf-lib 1.17.1 (MIT) ;
  - `tests/` : tests automatiques (Python + Playwright).

Barème des degrés de certitude : D. Leclercq (Université de Liège).
