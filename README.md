# CSC windsurfing handbook: HTML migration

This is a local working draft for the existing **cal-sailing.org** website. It has not been published. The April 2009 material is now grouped into three subject pages: Before you sail, Sailing skills, and Equipment & reference. The 24 topics are collapsible sections within those pages, with related links opening the relevant section. Handbook instruction and illustrations remain available for review; current club policies, ratings, sailing areas, and hours link to maintained CSC resources.

Repository: [fabianvalli/Windsurf-handbook](https://github.com/fabianvalli/Windsurf-handbook). This project converts the current handbook document to a set of HTML pages that can be added to the existing CSC website.

The [original April 2009 PDF](https://static.cal-sailing.org/images/official_files/windsurf_0409.pdf) is available publicly and is not bundled. The editable sources, artwork, generated previews, and handoff notes are all included here; no files from the original workstation are needed for normal editing or builds.

## Start on another computer

Clone the repository, then open that folder as your project:

```sh
git clone https://github.com/fabianvalli/Windsurf-handbook.git
cd Windsurf-handbook
```

Read `HANDOFF.md` for the current decisions and pending work, and `AGENTS.md` for the editing and permission rules. Use these files as the starting context in a new chat.

To view the existing preview, open `dist/index.html`. For rebuilding and a local web preview, install Python 3.10 or newer and run:

```sh
python tools/build.py
python tools/preview.py
```

Open the printed address, normally `http://127.0.0.1:8000/`. Stop the preview with Ctrl+C. On systems where the command is `python3` or `py`, use that instead of `python`. Normal builds and previews use only Python's standard library. Internet access is needed for the live CSC stylesheets and banner.

Before switching computers, have any approved changes committed and pushed. On the other computer, pull the latest changes before editing; review local changes before pulling. Generated `dist/` and `joomla/` files are tracked alongside their sources so previews stay current. GitHub synchronization does not deploy the handbook to the CSC website.

## Review

- Open `dist/index.html` to browse the handbook. Internet access is needed for the live site CSS.
- The desktop sidebar stays visible while scrolling. Below 992px it becomes a sticky, collapsible shortcut menu. Below 601px the preview's global menu also collapses.
- Open section headings stay visible while reading that section. Once pinned, they shrink to one line showing the section number and main caption, and slide out as the section ends. They remain compact offscreen to avoid a height change at the lower boundary. Phone headings sit beneath the shortcuts bar. The full heading returns when scrolling back to the start. Long captions use an ellipsis visually; their complete text remains accessible.
- `editorial/responsive-preview.html` loads the actual pages in 390px and 320px frames for phone review.
- Open `editorial/review.html` for the topic-by-topic migration map and pending corrections.
- `editorial/repository-review.html` records what is useful in the separately cloned redesign prototype and its content limitations.
- `manifest.json` records the source PDF pages, related topics, site links, and review status.
- `editorial/source-2009.txt` retains the extracted historical source for editorial reference. Its inclusion does not establish any historical procedure as current club policy.

## Editing

Edit `articles/<topic>.html` for a section's content. These are source fragments, not individual reading pages. Update titles, summaries, relationships, and status in `manifest.json`. Chapter assignments are in `tools/build.py`; `chapters.json` is its generated navigation map. Run `tools/build.py` with the bundled Python runtime to regenerate previews and Joomla bodies. The build requires only Python's standard library and checks local links, anchors, assets, heading structure, and coverage of all 24 sections.

`tools/migrate.py` is an archived one-time migration tool, not the normal build. Rerunning it overwrites article edits and the manifest, so it requires `--allow-overwrite`. If deliberately reimporting into a disposable copy, supply the downloaded public PDF with `--pdf` and Poppler's `pdftoppm` through PATH or `--pdftoppm`. Optional Python packages are listed in `tools/requirements-optional.txt`. None are needed for ordinary builds.

## Styling and integration

The live site uses Joomla with JA Edenite II, its orange theme, and Bootstrap 3. Standalone previews load the **live** bootstrap.css, legacy-grid.css, template.css, and custom.css from cal-sailing.org, and use the site's actual banner and logo. `assets/handbook.css` adds scoped layout, responsive spacing, disclosures, and sticky positioning. It does not copy the site's stylesheets or define a second color palette. `assets/handbook.js` opens linked sections, manages the responsive menus, expands/collapses sections, and expands a chapter for printing. It has no library dependency or framework build. Native disclosure controls still work without JavaScript.

For the real website, use **three Joomla articles under the existing template**. Import only the three bodies listed in `joomla/routes.json`; Joomla supplies its own header, global navigation, footer, title, and CSS. The preview shell is not part of the production article. Keep the Joomla title visible so each page has one H1. The small article files retained from the first attempt now contain forwarding links; do not import those as additional reading articles.

1. Create an unpublished Windsurfing Handbook category and three articles: Before you sail, Sailing skills, and Equipment & reference. Preserve native `details`, `summary`, section IDs, and classes when using the Joomla editor.
2. Use `joomla/routes.json` as the proposed menu/alias map. The route `/lessons-menu/windsurfing/handbook` is **proposed**, not an existing verified URL. Create menu aliases (including hidden menu items as appropriate), or adapt the route mapping to the webmaster's preferred routing.
3. Upload the image assets (JPG, PNG, and WebP) to `/images/windsurfing/handbook-2026/`, or adjust `IMAGE_ROUTE` in `tools/build.py`. Register `assets/handbook.css` and `assets/handbook.js` through Joomla's template/asset manager for these three menu items; do not paste script tags into rich-text article content. The script scopes template overflow adjustments to handbook pages so sticky navigation works. Use a full-width Joomla article layout without a second CMS sidebar, and remove the outer content wrapper's extra padding if the template supplies it.
4. Check every topic and cross-link in Joomla staging, including mobile, narrow screens, sidebar behavior, responsive figures, and keyboard navigation. The local preview verifies the inherited styles but cannot reproduce every CMS wrapper or module.
5. Resolve the editorial register and review the procedures before removing draft notices or publishing. Both the 2009 source and the existing site contain inconsistencies; neither has been assumed to be an approved 2026 rewrite.
6. Link Before you sail from the Windsurfing menu/lessons page. `joomla/legacy-redirects.json` maps the first draft's topic URLs to chapter anchors. Static forwarding files keep local first-draft links working. Keep the existing 10-Step Guide and PDF available until archival policy is agreed. Avoid competing copies of shared rating requirements and sailing boundaries.

Once installed in Joomla, the template will continue to provide styling after future theme changes. Use semantic headings, paragraphs, lists, figures, and links. Avoid inline fonts/colors pasted by a rich-text editor. The CMS, not these files, should supply modification dates for future edits. The current migration date is not a content approval date.

## Illustration plan and credits

Original diagrams and photographs are retained as individual assets for this review. Tiled photos were rendered from their original PDF bounds to preserve the full sequence. The 10-Step Guide is by Bill Prinzmetal; the source's 2007 revision credits photographs by Rob Weinberg. The full original revision history remains in `editorial/source-2009.txt`.

The accepted color dock, port/starboard tacks, points-of-sail and right-of-way illustrations are installed in the local handbook. The tacks image uses version 2, retaining the wind captions and adding the left/right hand-forward mnemonic. Each diagram scales to the available width. Linked photos and diagrams open in an accessible close-up dialog with Close image and Enlarge/Fit to screen controls. Close, Escape, an outside click, or browser Back returns to the same reading position. Native image links remain as the no-JavaScript fallback. Generation prompts are retained in `editorial/image-prompts/`.

The right-of-way flowchart has three interactive rows: overtaking, opposite tacks, and the same tack. Hover or keyboard focus previews two boards and their rigs; clicking or tapping keeps the example open. Close it with the Close button, Escape, or an outside click. The examples remain ordinary figures without JavaScript and are included when printing. The current example artwork omits people and emphasizes sail and boom geometry.

Replace diagrams individually with reviewed SVGs and descriptive alternative text. Priorities are points of sail, rig anatomy, dock layout, right-of-way, self-rescue, maneuver sequences, and knots. Current sailing boundaries should continue to come from the site's Sailing Areas page. No new map has been inferred from the 2009 landmarks.

## Checkout procedure update

Section 04 was rewritten on 2026-10-17 from the user-provided tablet/phone procedure. It includes all ten supplied photos, exact screen labels, equipment IDs, location and sign-in requirements, damage reporting, return verification, and no equipment time limit. The old paper signout and one-hour restrictions are removed from this section. Final user review is pending.

The web photos preserve the complete supplied images and link to larger views. WebP copies are proportionally reduced to at most 1600 pixels; originals remain outside this repository. `editorial/checkout-photo-sources.json` records their filenames, asset mapping, and encoding details. These originals are optional: the included web copies are sufficient for normal work. To reprocess the originals, install Pillow and run `python tools/prepare_checkout_photos.py --source "/path/to/original/photos"`, then run the normal build. The optional `source/` folder is ignored by Git. Phone layouts stack the steps and images; the desktop layout groups related steps side by side. Shared text rows align photo tops across the two- and three-column step groups, even when their instructions wrap differently.

## Reading sequence and shared topics

The editorial pass of October 17, 2026 keeps orientation, club rules, safety, checkout, dock handling, recovery, and the readiness checklist in that order. Section 02 now groups the links to rules, conduct, ratings, boundaries, fleet, and hours; section 01 no longer repeats them or jumps into technique. Section 04 retains the accepted checkout workflow and photos.

Fabian's latest decision is to retain the handbook's instructional text, anatomy/glossary, original reference images, and accepted color diagrams. Existing CSC lesson links are supplementary. We will review the main site's other pages later and then decide whether a content merge is needed. Current club policies, rating requirements, sailing areas, and hours continue to link to maintained resources. Downwind comes before Jibe, with optional higher-wind practice at the end. Historical instruction still requires review and has not been approved as 2026 club policy.

Per-section Next footer links have been removed at Fabian's request. Chapter tabs, sidebar shortcuts, and navigation between chapters remain. Optional related links exclude the following section and destinations already linked in the prose; shared club resources are presented in their relevant sections.

## Maintenance

After import, Joomla can be the editing source of truth. Keep these HTML sources synchronized only if a source-controlled workflow is desired; do not maintain independent divergent copies. Record actual content review dates and review triggers such as equipment, dock, rating, or procedure changes. This draft does not schedule an automation or publish anything.

## Repository context and consent

`https://github.com/calsailing/website-redesign` was reviewed in a separate local checkout. It contains one self-contained HTML prototype, not the full live Joomla source. The user confirmed that useful context can come from this prototype and the rest must come from the actual site. The live site remains the visual reference for this handbook. The prototype clone has not been edited and is not required to work on this repository.

The user requires explicit consent before **any commit or push**. The initial handbook import and push to this repository’s `main` branch were explicitly authorized on October 17, 2026. Fabian also approved committing the reviewed editorial and navigation revision and pushing it to `main` on October 17, 2026. This records authorization, not confirmation of a completed push; check Git history and the remote for the resulting state. Future commits and pushes require new explicit consent. Neither approval publishes the handbook to the CSC website.
