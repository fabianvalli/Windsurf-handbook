# Working on the CSC Windsurfing Handbook

Read `README.md`, `HANDOFF.md`, and the relevant article/manifest entry before editing.

## User decisions and permission

- Fabian requires explicit consent before **any new commit or push**. Preparing changes, building, and local testing are authorized. Show the concrete changes before requesting commit/push consent.
- Do not publish the handbook, enable GitHub Pages, change repository visibility, or modify the live CSC site without a specific request.
- Keep work in this repository. The separate `calsailing/website-redesign` prototype is background context, not the handbook's source or the live site's complete source.

## Source and build

- Edit `articles/*.html` and `manifest.json`; shared behavior is in `assets/handbook.css` and `assets/handbook.js`.
- Run `python tools/build.py` after changes. It rebuilds `dist/`, `joomla/`, the chapter map, and the editorial register, and validates links, images, anchors, and section coverage.
- Track generated outputs with their source changes so the previews remain usable after cloning.
- Preview with `python tools/preview.py`. Ordinary builds and previews use only Python's standard library.
- Never run `tools/migrate.py` for normal work. It is an archived one-time import that overwrites the reviewed article sources. An explicit `--allow-overwrite` flag is required as an additional guard.
- The public PDF is linked in `manifest.json` and `README.md`. The optional `source/` directory and original checkout photos are not required to build or edit the handbook.

## Design and content

- Retain the live CSC site's shared stylesheets, banner, colors, and typography. Keep handbook-specific CSS scoped under `.hb-app` or `.hb-preview`.
- Keep three cohesive reading pages with collapsible topics and related links. Do not return to one separate page per small topic.
- Preserve sticky shortcuts and section headings. Compact headings retain the section number and title. Their height compensation must not move the body or bounce at section boundaries.
- Linked images open in the shared close-up dialog. Close, Escape, and browser Back must preserve reading position; keep the native image-link fallback.
- Keep photo tops aligned in column groups, with steps stacked on narrow phones. Check at 320px and 390px after layout changes.
- Preserve the accepted dock and general-sailing artwork. Right-of-way examples show boards and rigs **without people**. Retain both wind-direction captions and the hand-forward mnemonic in the tacks illustration.
- Treat the 2009 PDF and unrelated prototype as historical reference. Rewrite current procedures from Fabian's supplied instructions; keep unresolved sections marked for review.
- Do not invent club policies or hardcode opening times. Link to maintained CSC resources.
- Record material content changes and remaining review items in the manifest and handoff. Update validation evidence for changed behavior; avoid unrelated refactors.
