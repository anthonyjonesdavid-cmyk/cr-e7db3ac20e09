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
python3 test/e2e_v21.py webkit               # panel view, sharp zoom tiles, reading lists (fixtures: test/gen_panels.py)
```
See CHANGELOG.md for the history.
