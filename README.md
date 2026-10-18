# Comic Shelf: private PDF comic reader (iPad-first PWA)

An offline comic reader for PDF comics. You import PDFs with the iPad file picker (Files app, Google Drive included). They are copied into the app's on-device IndexedDB storage and are **never uploaded anywhere**.

## Use on iPad
1. Open the site in Safari, then Share → **Add to Home Screen**.
2. Open **Comics** from the Home Screen and tap **Import**. Pick PDFs from the Files app, including Google Drive. You can pick several at once.
3. Import from the Home Screen app. On iPad, its storage is separate from Safari's.

## Features
- Shelf: grid of cover thumbnails (page 1 is rendered with pdf.js), editable titles, page counts, a progress bar, a "Continue reading" card, sorting by recent, title, or date added, search, optional grouping by series, and delete with a confirmation step.
- Reader: a real 3D page-turn fold that follows your finger, with shading. A small flick of about 20 px turns the page. A slow drag turns it once you pass 13% of the width, and releasing earlier snaps it back. Mostly vertical swipes never turn the page.
- Portrait shows one page. Landscape shows a two-page spread (the cover sits alone on the right, then pages come in pairs). A 1-up/2-up toggle is in the top bar.
- Pinch to zoom, double-tap to zoom, and pan while zoomed (pages don't turn while zoomed). Zoomed pages are re-rendered at higher resolution so they stay sharp.
- Tap the edges to turn pages. Tap the center to show or hide the slim, solid toolbars (title, back to shelf, a page scrubber with a thumbnail preview, a page grid, and "page x of y").
- Guided panel view: double-tap a panel to zoom to it, then swipe panel by panel in reading order, across page turns. Panels are found on the device with a recursive XY-cut over the gutters, and pages without gutters are split into thirds. Double-tap again or tap Full Page to leave. It can be turned off in Settings.
- Sharp zoom: when a zoom settles, the visible region is redrawn from the PDF at devicePixelRatio × zoom.
- Spinner rack for any Timeline month (realistic wire rack, always full, momentum spin, pull-out to read)
- Online release-date lookup (Fandom comics wikis, manual button)
- Timeline by release date (metadata / file name / built-in series table / manual)
- Multi-select with Move to Series… / Remove from Series (manual series survive re-import)
- Reading lists: named reading orders across series, each with a Home row and progress. The end-of-comic card follows the list when the comic was opened from it.
- Per-comic right-to-left (manga) mode. The app remembers your last page in each comic, including after a reload.
- Performance: pages render at device pixel ratio (capped at 2) and the 2 neighbouring views on each side are pre-rendered. Rendered pages are kept in an LRU bitmap cache with a pixel budget (about 30 MP on iOS), and evicted canvases are zeroed so iPad memory gets released. PDFs are stored in 4 MB chunks and pdf.js reads them by byte range, so a 200 MB, 220-page PDF never loads into memory all at once.
- Storage: IndexedDB, plus a `navigator.storage.persist()` request. Settings shows how much storage is used.
- Offline: a service worker caches the app shell, the vendored pdf.js and worker, and the font.

## Files
`index.html` is generated from `src/` by `./build.sh`, so edit the files in `src/` and then rebuild.
`vendor/` holds pdf.js 4.10.38 (legacy build, Apache-2.0), its cmaps and standard fonts, and the Bangers font (OFL).
The icons are original artwork (`icons/icon.svg`).

## Rebuild / test
```sh
./build.sh                                   # regenerate index.html
python3 test/gen_pdfs.py                     # original test comics -> testpdfs/ (git-ignored)
python3 -m http.server 8823 --bind 127.0.0.1 &
pip install playwright reportlab pillow && playwright install chromium webkit
python3 test/e2e.py chromium --big           # or: webkit; screenshots -> shots/
python3 test/e2e_v21.py webkit               # panel view, sharp zoom tiles, reading lists, multi-select (fixtures: test/gen_panels.py)
python3 test/e2e_v24.py webkit               # Timeline / release dates, 4 sizes standalone (fixtures: test/gen_dates.py)
python3 test/e2e_v26.py webkit               # spinner rack (v36 look: tops lean out, cream wire, sign), compact Timeline, online date lookup (mocked + one live check), 4 sizes
python3 test/e2e_v38.py webkit               # v38: Recent tab (4th segment, newest-first grid, scroll memory), removed Home rows, circular Home carousel (both sides filled on load), 4 sizes
python3 test/e2e_v39.py webkit               # v39: Keep screen awake while reading (mocked Screen Wake Lock: acquire/release/re-acquire, unsupported note), 4 sizes
python3 test/e2e_v40.py webkit               # v40: back-issue bin + night at the comic shop (auto-rotate) + rain sound, 4 sizes
python3 test/e2e_v41.py webkit               # v41: decade chips (touch taps, every chip, empty decade) + built-in release list, 4 sizes
python3 test/e2e_v42.py webkit               # v42: creator credits + creator page, Home carousel in release order, 4 sizes
python3 test/e2e_v43.py webkit               # v43: Continue Reading row on Home, 4 sizes
python3 test/e2e_v44.py webkit               # v44: Home without category rows (Settings toggle), spines for every series/list/Misc, 4 sizes
python3 test/e2e_v29.py webkit               # two-page spreads: landscape full screen, portrait fit + in-view Rotate, pinch, turns, panels; 4 sizes (fixtures: test/gen_spreads.py)
python3 test/e2e_v30.py webkit               # shelf of volumes on Home + v31 spine fonts/full names/contrast sweep + v35 book spines (rounded, cylindrical shading, accent bands, no count/vol line, glow titles ≥7:1, shrink-to-fit, 50–90px, 4–6px gaps, 220ms tip-out) (grouping, colours + contrast, IDB cache, tap/slide, reduced motion), 4 sizes
python3 test/e2e_v32.py webkit               # page sharpness: canvas backing >= CSS x DPR after turns/rotation, iOS caps (iPad UA), 4 sizes
```
See CHANGELOG.md for the history.
