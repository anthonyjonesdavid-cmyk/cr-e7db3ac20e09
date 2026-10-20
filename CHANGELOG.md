# Comic Shelf: change log

## cr-v49 — 2026-10-20

- **Pin to Continue Reading.** Long-press a cover (on Home or in the Library) and choose **Pin to Continue Reading** to keep it at the front of the Continue Reading row, with a small pin badge. Pinned issues come first in the order you pinned them and stay there even after you finish them, until you choose **Unpin**. Everything else follows, most recently read first. Pins are saved with your other settings on this device.
- New suite `test/e2e_v49.py`.

## cr-v48 — 2026-10-20

- **Bigger Home carousel covers.** The carousel now grows into any spare height (portrait iPads had an empty band of about 80px under the shelf), so the shelf moves down and sits a normal section gap above Continue Reading. Covers stay whole, clear of the header, tilted, and level on the shelf; Home still fits without scrolling.
- New suite `test/e2e_v48.py` (also 834x1194 and 768x1024).

## cr-v47 — 2026-10-20

- **Home carousel covers now stand on the shelf in a line.** The side covers are turned and pushed back around their middle, and the 3D view was centred above the shelf, so the further a cover was pushed back the higher its bottom corners floated. The covers now pivot on their bottom edge and the 3D view is centred on the shelf line, so every cover's bottom-left (and bottom-right) corner sits level on the top of the shelf. The tilt, depth and overlap look the same, and covers stay whole.
- New suite `test/e2e_v47.py` (every visible cover's bottom-left corner within 2px of the others and of the shelf top, tilt kept, at 5 sizes).

## cr-v46 — 2026-10-20

- **Whole covers on the Home carousel.** The covers were being cut off at the top (under the header) and at the bottom (at the shelf) on iPad. They now always show in full, fitted to their real shape with nothing cropped, and still sit right on the spine shelf, clear of the header. The carousel size is worked out from the space available, so this holds on iPad landscape (including the 11-inch 1180×820), iPad portrait and iPhone.
- Continue Reading is more compact in landscape (smaller covers with the title, page and progress bar), so the carousel, shelf and Continue Reading all fit on the screen without scrolling.
- New suite `test/e2e_v46.py` (checks every carousel cover's full image is visible and not clipped, at 5 sizes).

## cr-v45 — 2026-10-19

- **Also on sale this month**, at the bottom of the end-of-issue page (both the “Next” card and the End page): a compact row of the other comics in your library with the same cover month and year as the issue you just finished, using the Timeline dates (set by you, looked up, built-in list, metadata, file name). A year-only date shows “Also on sale around 1987” with that year’s issues. Hidden when the issue has no usable date or nothing else is from that month. Covers open the issue; when more than fit, a “+N more” tile opens the full grid page (back returns to the reader).
- Coming back from an issue opened on a creator page now returns to that page.
- New suite `test/e2e_v45.py`.

## cr-v44 — 2026-10-18

- Home is now the carousel, the shelf and Continue Reading. The category rows (series and reading lists) are hidden behind **Settings › Show category rows on Home** (off by default; turn it on to bring them back exactly as before, including your arranged order).
- The shelf now has a spine for every reading list and a **Misc** spine for issues without a series, next to the series spines (Mini-Series included). A reading-list spine opens the list in its order (issues opened from it continue in the list); Misc opens the issues without a series. Library is unchanged.
- Without the rows, the shelf and Continue Reading spread to fill the screen, so iPad doesn't end in an empty band.
- Tests that expected the rows now turn the setting on first; new suite `test/e2e_v44.py`.

## cr-v43 — 2026-10-17

- Home: **Continue Reading** row directly under the spine shelf, above the series rows. In-progress issues (started, not finished), most recently read first, with the thin progress bar and “p. 12 of 24” under each cover; tapping resumes at the saved page. When a series’ most recently read issue is finished, its next unread issue joins the row (“Next · p. 1 of …”). Hidden when empty.
- Long-press an issue in the row › **Remove from Continue Reading**: hides it without touching its progress; it comes back if you read it again.
- Reuses the existing row/cover/progress components and the long-press sheet. The v1 single “Continue reading” card was removed in v7 and no code of it remained, so nothing is duplicated.
- New suite `test/e2e_v43.py`.

## cr-v42 — 2026-10-17

- **Creator credits.** The issue info sheet (long-press) and the reader's More › Issue Info show Writer and Artist (penciller) as tappable names. A name opens a dark, compact creator page: every issue in your library by that creator, grouped by series, oldest first; covers open the issue. Name variants are merged (Jim Lee / James Lee, John Romita Jr. / John Romita, Jr., Erik Larsen / Erik J. Larsen, Louise Simonson / Louise Jones, …). Built-in data (`src/credits-data.js`) covers 778 issues, 202 creators, from the Fandom comics wikis.
- **Home carousel in release order**, oldest → newest, with the Timeline's dates (yours > built-in/looked-up > file name > estimate); undated issues at the end; still circular (newest wraps to oldest). Opens on the issue you read most recently, otherwise on the oldest.
- Amazing Spider-Man ASM001–ASM012 (the "400's" folder) confirmed as Vol 2 (1999): dated Jan–Dec 1999 and credited. Undated issues in the library: 89 → 77.
- New suite `test/e2e_v42.py`.

## cr-v41 — 2026-10-17

- Timeline: **decade chips fixed.** Every chip now jumps to the first issue of its decade and stays lit. Root causes: (1) the scroll-spy ran on every frame of the smooth jump and called `scrollIntoView` on the chip strip, which in WebKit cancels the in-flight scroll of the grid — the jump stopped and the previous chip re-lit; (2) the jump offset used `offsetTop` (measured from the Timeline view, not the scroller), so it overshot by the bar height; (3) a decade near the end can't scroll to the top, so the spy re-highlighted the previous decade. Now the target is measured with rects, the tapped chip stays lit until you scroll the grid yourself, the strip is scrolled without `scrollIntoView`, the strip pans horizontally only and chips use `touch-action: manipulation`.
- Chips cover every decade in range; a decade with no issues jumps to the nearest one with a short note.
- **Built-in release list**: 766 issues of your Drive library dated from the Fandom comics wikis (series and volume matched by folder — e.g. Fantastic Four Heroes Reborn → Vol 2, X-Men (1991) → Vol 2, Wolverine → Vol 2). Used only when an issue has no date from you, the file, its metadata or an online lookup; dates you set by hand are never changed. Undated/estimated issues in the library: 855 → 89.
- New suite `test/e2e_v41.py` (touch taps on every chip at 4 sizes, after scrolling the strip and the grid, empty decade, built-in list vs manual dates).

## cr-v40 — 2026-10-16

- Timeline: **Back-issue bin** (button beside the rack). A longbox seen from slightly above — our own cardboard box and clear bags drawn with CSS — with bagged comics standing in a row, tops showing. Drag or swipe to riffle forward (120ms a card, momentum on a flick); the front comic lifts to show its cover; tap it to read. **Dig** shuffles a random handful from the whole collection in right after the front comic. Drawn from the full library, virtualized to a pool of 30 cards. Close button; Esc/arrow keys too.
- Rack screen: **Night at the comic shop** toggle (also in Settings; off by default, persisted). Dim shop and warm lamp glow from CSS gradients + vignette, as flat 2D layers beside the 3D scene (never inside the rotor — v37 lesson). The rack slowly auto-rotates when idle; touch pauses it and it resumes ~5s after the last touch. No auto-rotate with prefers-reduced-motion.
- **Rain sound** toggle (rack screen + Settings; off by default): soft rain generated with the Web Audio API (white + brown noise through high/low-pass filters). Starts only after a user tap; plays while the Timeline tab (list, rack or bin) is on screen; stops when leaving Timeline, opening a comic, or when the app is hidden.
- Home unchanged.
- Tests: new e2e_v40 (bin layout/riffle/momentum/Dig/tap-to-read/close, 2,000-comic virtualization, night toggle + persistence + Settings mirror, auto-rotate idle/pause/resume/reduced-motion, sign stable every frame while rotating, rain start/stop rules) at 4 sizes.

## cr-v39 — 2026-10-16

- Settings: "Keep screen awake while reading" toggle (off by default, stored in localStorage `cr.keepAwake`). When on, holds a Screen Wake Lock (`navigator.wakeLock.request('screen')`) only while the reader is open; re-acquired on `visibilitychange` when the app becomes visible again mid-read; released when leaving the reader or turning the toggle off.
- Unsupported browsers show a short note under the toggle (needs iOS 16.4+); no video fallback.
- Tests: new e2e_v39 (mocked wakeLock): default off, ≥40px target, acquire on open, drop on hide / re-acquire on show, release on close and on toggle off, nothing outside the reader, persistence, unsupported note — 4 sizes.

## cr-v38 — 2026-10-15

- Home: removed the "This week in… / On sale this month in past years" row and the "Recently Added" row (Arrange Categories now lists series and reading lists only).
- New 4th switcher segment: Home | Library | Timeline | Recently Added ("Recent" on narrow screens). Compact newest-first grid of every comic; tap opens the issue; scroll position kept across tab switches and reader round-trips. Re-renders only when the list changes.
- Home cover carousel is now circular: covers wrap around, so the first cover has the last ones to its left and flicks past either end keep cycling; momentum and snapping unchanged. With very few comics the list repeats so both sides stay full. Fixed DOM slots (±window) instead of one node per item.
- Tests: new e2e_v38 (replaces the v28 This-week suite): removed rows, 4-segment switcher fit (≥40px, no clipping/clash, below status bar), Recent order/open/scroll memory, 980-issue render time, carousel filled on both sides at load at 4 sizes, wrap past start, 2-comic repeat. e2e / v21 / v30 updated for the removed rows.

## cr-v37 — 2026-10-15

- Fix: rack header sign flickered while spinning (red "FOR ALL AGES" z-fighting with the white board). The sign is now one flat layer: board and lettering baked into a single SVG background, no child text layers, `transform-style: flat`, lifted 2px off the pole's plane (pole pushed back 1px).
- Audited the rest of the rack: pockets/covers/lips are flat children of each pocket; wings sit 3px behind pockets; base lives outside the rotor — no other coplanar 3D layers.
- Tests: e2e_v26 checks the sign is a single SVG layer, not coplanar with the pole (66 checks).

## cr-v36 — 2026-10-15

- Timeline rack redesigned after real spinner racks: fixed tilt direction — each comic's bottom sits in the wire pocket by the pole and its TOP leans OUT, cover facing out and tilted back.
- Cream/off-white wire frame, pole and base; tier wires on every wing; wire pocket lips at the bottom of each pocket; lower tiers overlap so issues behind peek out above.
- Two-line header sign "COMICS / FOR ALL AGES" (own text, no logos).
- Always-full/backfill, month logic, taps and performance unchanged.
- Tests: e2e_v26 adds tilt-direction and cream-frame checks (62 checks); screenshots renamed webkit-v36-rack-*.

## cr-v35 — 2026-10-14

- Spines: issue count and volume/years line removed (both still in the accessible label).
- Real-book look: subtly rounded spine edges, cylindrical shading (lighter centre, darker edges), thin raised accent bands near top and bottom. Glowing titles, v31 fonts and ≥7:1 contrast unchanged.
- Selection: tapped book slides up and tips toward the viewer (translateY + rotateX + scale, deeper shadow) over 220ms, then the volume opens (≤250ms). Skipped under prefers-reduced-motion.
- Tests: e2e_v30 updated for v35 (58 checks, incl. open-time ≤250ms and a mid-animation screenshot).

## cr-v34 — 2026-10-14

- Spines: cover-art panel removed (smart-crop no longer used for spines; stored crops dropped).
- Bigger books: shelf ~220px tall on iPad / ~165px on iPhone; spine width 50–90px scaled by issue count; 5px gaps.
- Titles: full names, large (fill most of spine width) with v31 per-series fonts; near-white accent tint (85% white mix) with soft dark glow on a near-black body; contrast ≥ 7:1; shrink-to-fit before truncation.
- Thin accent rule near the top; small issue count at foot; volume/years line only on spines ≥ 60px (light grey).
- Soft shelf lighting: subtle top-down gradient and faint shadow under books.
- Tests: e2e_v30 updated for v34 (57 checks).

## cr-v33 — 2026-10-14
- **Trade-paperback spines** (after David's reference photo): mostly dark spine body (the cover's colour, 90% toward black); the top ~28% is an art panel cropped from that volume's own first cover; big vertical title in the v31 per-series font in a bright accent colour from the cover (lifted toward white until it clears 5:1 on the body; ≥4.5:1 verified on a 4,913-colour sweep); smaller light subtitle line for volume/years; small issue count at the foot (no publisher logo).
- **Smart crop**: edge/contrast density on a 48px-wide grey copy, upper-centre bias; lettering bands (logo, tagline, credits: strong edges across most of the width) and the top band are down-weighted, so the panel shows art rather than the cover title. 5:4 crop, stored as a small JPEG.
- Sampled once per volume and cached in IndexedDB with the colours (resampled only if that cover image is regenerated).
- Taller, more uniform spines (170px iPad / 130px iPhone, heights within 4px); widths still 40–76px; long titles shrink to fit (min 11px) before ellipsis.

## cr-v32 — 2026-10-14
- **Sharper pages on iPad**: the per-page bitmap cap on iOS was 4.2 MP. That forced full-screen spreads (2732×2048 on iPad landscape) to 88% resolution and portrait pages on large iPads to ~93%, below screen × devicePixelRatio. Raised to 7 MP (well under the iOS 16.7 MP per-canvas limit); the total cache budget is still bounded (36 MP on iOS).
- Placeholders (a cached render from another size/orientation) are always upgraded: the exact-size render is re-requested if its job was dropped.
- Diagnostics: `__cr.srcRes(page)` reports the pixel size of the scan embedded in a page.
- Investigated Excalibur 006 pp.18–19: the soft left page is the file itself. Pages 11–18 embed their art as 329×499 images (≈50 ppi), the rest at 988×1500 (150 ppi). The reader renders both at full screen resolution; nothing in the app can recover the missing detail (a better scan is needed).
- New test e2e_v32.py: with an iPad/iPhone user agent (iOS caps on), every visible page's canvas backing ≥ CSS size × DPR after opening, turns, fast turns while renders are slow, jumps, the Rotate button and device rotation — both pages in 2-up included.

## cr-v31 — 2026-10-14
- **Spine typography**: each series gets a display face that evokes its genre (never a copy of a logo), from 8 bundled open-licensed fonts (fonts/README.md): Bangers (Spider-Man-style comic), Bungee + italic skew (X-Men blocky), Luckiest Guy (Fantastic Four heavy retro), Cinzel Decorative (Batman / Hellboy / Sandman gothic serif), Creepster (horror), Orbitron (sci-fi geometric), Black Ops One (military/war), Permanent Marker (indie). Unknown series get a deterministic varied fallback. Letter-spacing per face; Latin subsets (~150 KB total), cached by the service worker.
- **Full names on spines**: ASM → Amazing Spider-Man, UXM → Uncanny X-Men, FF → Fantastic Four, TMNT, JLA, GotG, TEC and more (small alias map; Library names unchanged).
- **Contrast**: ink is a tint of the spine colour when it clears 5:1, else white or black (which always clears 4.5:1), plus a thin opposite-colour stroke/shadow. Tested on every spine and on a 4,913-colour sweep including mid-tones.

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
