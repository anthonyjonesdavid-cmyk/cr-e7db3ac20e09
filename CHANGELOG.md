# Comic Shelf: change log

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
