# Comic Shelf: change log

## cr-v30 — 2026-10-14
- **Shelf of volumes on Home**, directly under the carousel (above "This week in…"): one book spine per series/volume exactly as grouped in Library (Move to Series choices included), standing on a minimal dark wooden shelf.
- Spine colour = dominant colour of the volume's first cover; text ink (white or near-black) picked for ≥4.5:1 contrast. Vertical title plus a second line with volume number and year range from Timeline dates (e.g. "Vol 2 · 1991–92").
- Thickness grows modestly with issue count (40px minimum tap target, 76px cap); slight height variation for a real-shelf look.
- Native horizontal scroll with momentum when the shelf overflows.
- Tap a spine: it slides out (200ms; instant with Reduce Motion) and opens that series' issues.
- Compact: ~176px on iPad, ~142px on iPhone. Colours are sampled once per volume and cached in IndexedDB (on the comic record); no other background work.

## cr-v29 — 2026-10-13
- **Two-page spreads**: wide pages (width/height > 1.2) are detected when a comic opens (page shapes read once, remembered).
- **Landscape**: a spread is its own page, shown full screen; it never pairs with a neighbour (2-up pairing resumes after it). Page turns between a pair and a spread turn as one sheet.
- **Portrait (iPad/iPhone)**: a spread is fitted to the full width, centred vertically on black — not shrunk into a page slot or split. Pinch zoom with sharp re-render.
- **Rotate** button (40px, bottom-right, only on spreads in portrait): rotates the spread 90° inside the view to fill the portrait screen (web apps can't force device orientation); tap again to undo. Pinch zoom works rotated; turning the page or entering panel view returns it upright.
- Panel view works on spreads.

## cr-v28 — 2026-10-13
- **"This week in…" row on Home** (first row under the carousel, same row style): your issues released this week in past years, newest year first; each tile shows its year (and day when known). Tap to read.
- Uses Timeline release dates in this order: set by you > looked up online > embedded metadata > file name. "≈" estimates are never used.
- Most dates are month-level: when no exact-day match falls within ±3 days of today, the row falls back to this calendar month and is titled "On sale this month in past years". Hidden when nothing matches.
- Computed when Home is drawn (at open / after changes); no background task.
- Exact days are now kept from ComicInfo `<Day>` and full ISO XMP dates (a "-01"/Day 1 placeholder stays month-level).

## cr-v27 — 2026-10-13
- **Timeline is a tab**: top control is now Home | Library | Timeline. The Timeline tab shows the compact grid inside the normal app chrome, with decade chips, issue count and the spinner-rack button in a solid sub-bar; year labels still open that year's rack. The app still opens on Home.
- Removed the Timeline bar under the Home carousel; Home rows sit directly under the carousel again.
- Segmented control buttons are 40px tall. On iPhone (≤440px) the segments narrow and the Library "Select" button becomes a 40px icon so everything fits at 390pt with no overlap.

## cr-v26 — 2026-10-12
- **Spinner rack rebuilt to look like a real one**: tall, narrow white wire rack on a chrome pole with a round white base and a plain "COMICS" sign; 6 wings × 8 tiers of angled wire pockets fanned around the pole, covers leaning back and overlapping down each wing, several wings visible at once; fills ~90% of the screen height. Spins around the pole (60° steps, momentum, reduced motion respected). Every pocket's transform is computed per frame, so it renders the same even where nested 3D is flattened.
- **Always full**: all 48 pockets filled, nearest dates first (outward from the chosen month, then undated issues); issues repeat only when the whole library is smaller than the rack (shown as "repeats to fill").
- **Timeline compacted**: one continuous grid, oldest → newest, no per-year sections or sticky headers; a small year label on the first issue of each year (tap it for that year's rack), decade chips, and a rack button in the bar.
- **Online release-date lookup** (manual only): Settings → *Look Up Release Dates…* (issues with unknown or ≈ dates) and *Look Up Online* in the Release Date sheet. Source: Fandom comics wikis (Marvel / DC / Image / Dark Horse Databases) via the public MediaWiki API — keyless and CORS-enabled, verified from the app in WebKit. Results are saved with source "online"; dates you set by hand are never changed. When several volumes match and nothing says which, it lists them for you to pick instead of guessing.
- **Fix: volume-aware estimates.** The built-in table only knows each title's first volume, so it no longer estimates when the series/file says Vol 2+ / v2, a relaunch ("Heroes Reborn", "Rebirth", "New 52"…), or a start year like "(1996)" that doesn't match. Those stay Unknown for the online lookup, which also matches by volume/start year (e.g. Heroes Reborn *Fantastic Four* #3 → Vol 2, Jan 1997). Estimates are computed live, so existing ≈ dates are re-evaluated immediately on upgrade; embedded dates are re-read once (DATE_V 2).

## cr-v25 — 2026-10-12
- **Spinner rack**: each year section of the Timeline has a 40px rack button. It opens a full-screen CSS‑3D wire spinner rack ("On the racks · Mar 1984") holding your issues dated within ±2 months of that month (the year's median issue month), widened step by step up to ±6 months when fewer than 6 issues fall inside; the window is shown under the title.
- 4–8 sided rack (by issue count), 4 tiers × 2 wire pockets per side, top sign, pole and base; original drawn wirework only, covers are your own.
- Drag/swipe spins with momentum and settles on a face; ‹ › spin buttons and arrow keys turn one face; tapping a side pocket turns it to the front. Prev/next month arrows move the window; empty months say so.
- Tap a front cover: it pulls out of the pocket (animated) and opens in the reader; closing the reader returns to the rack. A second tap during the pull-out is ignored.
- Reduced motion: no momentum, no pull-out animation, instant face changes.
- Faces turned away are hidden and depth-ordered in JS (robust on WebKit); spin runs on one transform per frame.

## cr-v24 — 2026-10-12
- **Timeline**: every issue arranged by original cover/release date, oldest first, with sticky year headers, decade jump chips (highlight follows scrolling) and an "Unknown date" section last. Tap an issue to open it; closing the reader returns to the Timeline. Compact **Timeline** entry on Home under the carousel, showing the year range.
- **How dates are found** (first match wins): date you set by hand → embedded metadata (ComicInfo.xml attached to the PDF, XMP `prism:coverDate` / `prism:publicationDate`, Info Year/Month) → year in the file name/title (`(1983)`, `(Mar 1984)`, `(1983-04)`) → built-in offline table of well-known series (estimated from #1's cover date + monthly cadence, shown with ≈) → Unknown. PDF CreationDate/ModDate are ignored (they're scan/export dates).
- **Release Date…** in the long-press sheet: set month (optional) + year, or go back to Automatic. Stored in IndexedDB (DB v3, new `overrides` store, keyed by file) so it survives delete + re-import and Drive re-sync.
- Comics imported before v24 get their embedded dates read once in the background.

## cr-v23 — 2026-10-10
- **Multi-select** on the Library and series pages: **Select** in the top bar, tap covers to check, Select All / Select None, live count; solid black selection bar with 40px+ targets (compact labels on iPhone).
- **Move to Series…**: pick an existing series or create a new one with a name and optional volume (e.g. “Uncanny X-Men” + 2 → “Uncanny X-Men Vol. 2”). Moved issues keep progress, reading lists, blank-page and panel caches; Home rows, series carousel and issue order update; an emptied series disappears (its open series page follows the comics).
- **Manual series overrides** are remembered per file (Drive id, or file name + size), so a re-import or Drive re-sync keeps them instead of re-grouping by folder/file name. Rename/Merge and the Edit sheet now record overrides too.
- **Remove from Series** returns comics to automatic grouping and drops the override.
- Fix (WebKit): tapping Move while the name field had focus could lose the tap.

## cr-v22 (Oct 9, 2026)
- **The app always opens on Home.** Before this, the last tab was saved on the device (localStorage `cr.tab`), so reopening the Home Screen app landed on Library if that was the last tab you used. The tab is no longer saved, and the old saved value is ignored and cleared.
  - Opening the app fresh, reopening it, or restoring it from the back-forward cache all land on Home at the top: no series page and no search.
  - An unknown or stale address (for example, a deleted comic) is cleared and Home is shown.
  - Switching tabs during a session works as before. Closing a comic you opened from Library still returns you to Library.
  - Reloading the page while reading still reopens that comic, with Home underneath it.

## cr-v21 (Oct 9, 2026)
- **Guided panel view.** Double-tap a panel and the page zooms smoothly until that panel fills the screen. Everything else is dimmed.
  - Swipe, tap the edges, or use the arrow keys to move to the next or previous panel. Panels go in reading order: rows top to bottom, then left to right, or right to left in RTL mode. After the last panel, the next page opens on its first panel.
  - Double-tap again, or tap **Full Page**, to see the whole page. Pinching switches to normal free zoom.
  - Panels are found on the device by detecting the white or black gutters between them. Pages with no gutters (splash pages) are split into thirds. Each page's panel boxes are saved with the comic.
  - Works on half pages of fold comics, on the full sheet in landscape, and on 2-up spreads.
  - The setting is under Settings → Guided panel view and is on by default.
- **Sharp zoom.** Once a pinch, pan or panel zoom settles, the part of the page you can see is redrawn from the PDF at screen resolution × zoom. Text stays crisp even at 6×. Old redraws are cancelled, the size is capped for iPad memory, and the sharp copy is discarded when you zoom back out.
- **Reading lists.** You can make named reading orders, such as "Inferno", that mix issues from any series.
  - Add a comic by long-pressing it and choosing *Add to Reading List…*, or from ••• in the reader.
  - Each list gets its own Home row with progress ("3 of 8"). Tap the row title to rename the list, drag ≡ to reorder it, or remove comics.
  - A comic opened from a list shows the list's next comic on its end card ("Next in Inferno"), instead of the next issue in the series.
  - Lists are stored on the device in IndexedDB.
- The reader top-bar buttons are now 40 px tap targets.

## cr-v20 (Oct 8, 2026)
- One cached blank-page pipeline:
  - A strict detector for black pages, such as a black "TM & ©" page.
  - Nearly white pages are detected only on neutral paper.
  - Scanning runs in the background.
  - *Skip blank pages* can be set globally and for each comic.
- Fixed: the first service-worker install no longer reloads the page, which used to cut off a first import.

## cr-v19 (Oct 6, 2026)
- Redesigned the next-issue card: its caption sits above the cover, and the card is its own page.
- Near-blank pages are skipped. Added a cache bypass for index.html.

## cr-v14
- Added a next-issue card at the end of a comic, and a Kindle shortcut on series pages (the shortcut was removed in v19).

## cr-v13
- Fixed a flash after a page turn and a 1 px seam in the middle. The series page was simplified to a back chevron, and Rename/Merge moved to the ••• menu and Settings.

## cr-v12
- Fold comics in portrait show half pages. Series-page carousels are in strict issue order.
