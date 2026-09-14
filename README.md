# Havesome Memory

**Havesome Memory** opens with a source-backed comparison of four basic memory patterns and all nine integrations documented on the Hermes memory-provider page (eight bundled plugins plus the separately installed Memori integration). Provider positions and benchmark results are attributed to their own sources, with test conditions, gaps and disagreements visible. No universal leaderboard.

The complete native-scroll Morrow Works story and its five-technology deep dive remain available at `story.html`. A separate presentation layer applies shared branding, stronger labels, Lucide icons, direct system links and concise reader-facing copy. The pinned story snapshot and source corpus remain unchanged. Presentation edits shorten repeated commentary and two lifecycle labels without changing interaction logic.

The story also has a fixed 36-step timeline, chapter jumps and an all-steps overview. The comparison uses a documented six-axis editorial rubric, separate from vendor benchmarks: every approach has an assessed scope, strengths, limits and a radar profile. Axis names appear directly on the charts; detail profiles show each score beside its axis instead of repeating a separate key. Unknowns are not scored as zero; there is no overall ranking.

The homepage table prioritizes descriptions: approach, saved information, retrieval, published evidence and storage. Its checkboxes pin the original rows beneath a table-scoped sticky heading and overlay the selected approaches in one shared radar. Selection is unlimited; pinned descriptions and the named series legend scroll independently. Filters retain selections with explicit counts. Stable colors, letter keys and focus/tap highlighting distinguish series; all six axes expose exact scores and rubric questions, including Unknown. On smaller screens the chart is a bounded expandable panel, visible only alongside the table. No-JavaScript reading retains descriptions, full dossier radars and native source disclosures; pin controls are disabled. Detailed claim cards and historical evidence are inside the default-closed source drawers.

Published site: <https://zacaria.github.io/havesome-memory/>

## What the guide covers

- why filenames, embeddings, and retrieval alone do not make a maintained knowledge system;
- source identity, provenance, scope, time, conflict, correction, permission, context assembly, expiry, and forgetting;
- the documented centers of gravity of Hindsight, Mem0 Platform and Dream, OpenViking, Supermemory, and Microsoft GraphRAG;
- tests an engineering team should run before choosing or building a memory layer.

The Morrow Works organization and all its records are fictional. The comparison evidence was reviewed on 14 September 2026; the preserved story deep dive retains its 13 September 2026 review. The project has not deployed or independently benchmarked those providers.

## Repository boundary

This public repository intentionally contains only the production source and verification scripts. Research-page snapshots, third-party reference screenshots, historical prototypes, generated screenshots, and packaged evidence archives are excluded. The generated site embeds a small, source-attributed collection of provider marks, a pinned Lucide icon subset and original note illustrations. It makes no external runtime requests and includes no analytics or credentials. Logo origins and complete license notices are recorded in `src/provider-logos.json`, `THIRD_PARTY_NOTICES.md`, and the page’s credits.

## Build

```sh
python3 scripts/build_site.py
python3 scripts/check_site.py --worktree
python3 scripts/test_comparison.py
python3 scripts/test_assessment.py
```

The deterministic build writes exactly four files to `_site/`: `index.html` (comparison), `story.html` (preserved guide), `404.html`, and `.nojekyll`. The original four-chapter source remains hash-pinned. Major old story fragment links redirect to `story.html`.

Comparison data and citations live in `src/comparison.json`; `scripts/build_comparison.py` renders the self-contained entry point. `scripts/approach_assessment.py` derives the shared chart's geometry from the same renderer used for the full assessment profiles. `src/comparison-interactions.js` and `.css` provide selection, sticky layout and top-layer score popups without dependencies or runtime requests. The `--worktree` audit includes the explicit new-file closure before staging; CI omits the flag and audits the Git index.

## Browser verification

```sh
python3 -m venv .venv
.venv/bin/python -m pip install playwright==1.62.0
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/test_site_browser.py
.venv/bin/python scripts/test_comparison_browser.py
```

The comparison and optional assessment browser tests use Playwright-managed Chromium when `BROWSER_EXECUTABLE` is absent or empty; set it explicitly to use another Chromium-family executable. The comparison suite exercises all 13 disclosures at five widths, filtering, search and empty state, keyboard operation, no-JavaScript reading, source drawers, direct provider anchors, an old story anchor, and the round trip to the preserved story. It also runs `scripts/test_comparison_interactions.py`: a nine-viewport selection matrix covering none/one/several/all 13, original-node identity and order, filter retention, bounded scrolling, resize and column geometry, table-end sticky behavior, shared series/legend synchronization, all 78 scores and unknown geometry, touch/keyboard popups and dismissal. Evidence is written under ignored `_verification/`. The unchanged story release suite exercises all 27 story beats forwards and backwards at five viewport sizes, the five technology sections, direct chapter navigation, source drawers, reduced motion, no-JavaScript fallback, overflow, page errors, and remote requests.

## Publishing

GitHub Pages deploys only `_site/` through `.github/workflows/pages.yml` after static and browser verification pass on `main`. Generated files are not committed.

## License

- Code: [MIT](LICENSE-CODE)
- Original prose, fictional scenario, and visual design: [all rights reserved](LICENSE-CONTENT)
- Third-party and research-source boundary: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
