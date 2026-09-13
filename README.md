# Havesome Memory

**Memory Engineering** is a source-backed, native-scroll guide for engineers and AI-initiated readers. A fictional company story makes memory failures concrete; a final chapter maps those problems to five current technology approaches without declaring a universal winner.

Published site: <https://zacaria.github.io/havesome-memory/>

## What the guide covers

- why filenames, embeddings, and retrieval alone do not make a maintained knowledge system;
- source identity, provenance, scope, time, conflict, correction, permission, context assembly, expiry, and forgetting;
- the documented centers of gravity of Hindsight, Mem0 Platform and Dream, OpenViking, Supermemory, and Microsoft GraphRAG;
- tests an engineering team should run before choosing or building a memory layer.

The Morrow Works organization and all its records are fictional. Provider material is primary-source desk research reviewed on 13 September 2026. The project has not deployed or independently benchmarked those providers.

## Repository boundary

This public repository intentionally contains only the production source and verification scripts. Research-page snapshots, third-party reference screenshots, historical prototypes, generated screenshots, and packaged evidence archives are excluded. The generated site embeds no third-party runtime assets, analytics, network calls, or credentials.

## Build

```sh
python3 scripts/build_site.py
python3 scripts/check_site.py
```

The deterministic build writes exactly three files to `_site/`: `index.html`, `404.html`, and `.nojekyll`.

## Browser verification

```sh
python3 -m venv .venv
.venv/bin/python -m pip install playwright==1.62.0
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/test_site_browser.py
```

On Linux with a system Chromium, the script uses `/usr/bin/chromium`; set `BROWSER_EXECUTABLE` to another Chromium-family executable when needed. The release suite exercises all 27 story beats forwards and backwards at five viewport sizes, the five technology sections, direct chapter navigation, source drawers, reduced motion, no-JavaScript fallback, overflow, page errors, and remote requests.

## Publishing

GitHub Pages deploys only `_site/` through `.github/workflows/pages.yml` after static and browser verification pass on `main`. Generated files are not committed.

## License

- Code: [MIT](LICENSE-CODE)
- Original prose, fictional scenario, and visual design: [all rights reserved](LICENSE-CONTENT)
- Third-party and research-source boundary: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
