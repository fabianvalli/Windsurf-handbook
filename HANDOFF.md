# Continue the handbook on another computer

This repository carries the editable project, its artwork, ready-to-open previews, and the decisions needed to continue without relying on a previous chat or this workstation's folders.

Start with the quick start in `README.md`. Then read `AGENTS.md`, this file, and the relevant section in `manifest.json`. A useful first instruction in a new conversation is:

> Read AGENTS.md, README.md, and HANDOFF.md, inspect the current changes, and continue the CSC windsurfing handbook. Do not commit, push, or publish without my explicit consent.

## Purpose and organization

Modernize CSC's April 2009 windsurfing PDF into maintainable HTML for the existing cal-sailing.org website. The work remains a review draft and is not deployed to the club site.

- **Before you sail:** `dist/index.html`, seven collapsible topics.
- **Sailing skills:** `dist/sailing-skills.html`, twelve topics.
- **Equipment & reference:** `dist/equipment-reference.html`, five topics.
- Editable fragments: `articles/`. Metadata and review notes: `manifest.json`.
- Joomla import bodies: three main files listed in `joomla/routes.json`. Other HTML files are legacy forwards, not extra articles.
- The live Joomla theme supplies shared CSS and branding. The publicly cloned redesign prototype is incomplete and has a different visual design.

## Latest completed work (October 17, 2026)

**Section 04, Checking equipment out and back in**, was rewritten from Fabian's current procedure. It covers board/sail IDs, tablet and on-site phone signout, login/location access, home-screen access, return and damage reporting, checking the active-signouts monitor, club hours, and no equipment time limit. All ten supplied photos are included as optimized WebP copies. The old paper signout and one-hour restrictions were removed from this section. Fabian accepted the wording/layout and then requested the two refinements below.

**Image close-ups and photo alignment:** linked photos and diagrams open in a modal viewer with Close image, Enlarge, and Fit to screen. Close, Escape, outside click, and browser Back preserve reading position. Two- and three-column checkout groups align photo tops independently of instruction lengths; phone steps stack. Desktop and 320px/390px previews were checked. See `editorial/validation.json` and the screenshot evidence it lists.

**Sticky navigation:** desktop shortcuts remain visible; phones have a sticky collapsible shortcuts bar. Open section headings pin while reading, shrink to the section number and one-line title, and leave with the section. Keep the summary-margin height compensation; body-padding compensation previously caused jumps.

## Editorial sequence review (October 17, 2026)

Fabian requested a full scan for repetition, missing topics, and premature jumps. He subsequently clarified that the handbook's existing work, including its diagrams, should be retained. Comparison with the main site's other pages and any decision about merging content are deferred.

On October 17, 2026, Fabian explicitly approved committing the reviewed editorial and navigation changes and pushing this revision to `main`. This records authorization, not completion; check Git history and the remote for the resulting state. Future commits and pushes require new explicit consent. Publishing to the live CSC website remains outside this approval.

01 stays focused on joining, lessons, and participation. 02 is now **Club rules and procedures**, the home for links to operating rules, conduct, ratings, areas, fleet, and hours. 03 retains safety preparation; 04 keeps the accepted signout/return procedure and ten photos; 05 retains dock/carrying instruction and the accepted dock illustration; 06 retains recovery instruction; 07 is a readiness recap. Historical safety and recovery guidance still require review.

The Sailing skills chapter retains its instructional text, original reference images, and accepted color diagrams. Equipment anatomy, terminology, rigging, and knot reference also remain available locally for review. Existing CSC lesson and reference links are supplementary. Downwind comes before Jibe; high wind and freestyle are optional later practice. Retaining historical material does not establish it as approved current guidance.

Fabian requested removal of the per-section Next footer links. Chapter tabs, sidebar shortcuts, and navigation between chapters remain. Optional Related links still exclude the following section and destinations already linked in the prose. The duplicate generic resource list was removed from the sidebar; resources sit with their relevant topics. See manifest notes and editorial/validation.json for details. The live 10-Step Guide is historical instruction, not a newly approved 2026 policy document.

## Current illustration choices

- Dock: `assets/dock-layout-color-v1.png`.
- Tacks: `assets/port-starboard-tacks-color-v2.png`; hand-forward mnemonic **added alongside** the wind captions.
- Points of sail: `assets/points-of-sail-color-v1.png`.
- Right-of-way flowchart: `assets/right-of-way-color-v1.png`.
- Hover/tap examples: `right-of-way-overtaking-v2.png`, `right-of-way-opposite-tacks-v2.png`, `right-of-way-same-tack-v3.png`. Two boards and sails per situation, no people, with mast/boom/clew details refined.
- Previous artwork versions remain as reference. Prompts are in `editorial/image-prompts/`; they are not instructions to regenerate accepted images.

## Remaining work

Continue section by section as Fabian supplies new material. Retain the handbook's instructional content and diagrams while reviewing the new sequence and transitions. Compare other CSC pages later before deciding whether content should merge; current policy, rating, area, and hour resources continue to use maintained site links. The manifest records per-topic review notes. Priorities include safety/PFD guidance, rating boundaries, self-rescue locations, current rigging/equipment care, historical glossary definitions and angles, and remaining diagrams. The duplicate rule list and blanket towing-priority statement were removed during the sequence review; the accepted right-of-way flowchart and examples remain.

Do not remove draft notices or treat the entire handbook as approved. No next rewrite has been chosen yet. Club-site Joomla integration, routing, editor preservation of details/summary, and final staging checks remain outstanding.

## Portable files and originals

The source PDF is public: https://static.cal-sailing.org/images/official_files/windsurf_0409.pdf

It is not bundled. `editorial/source-2009.txt` retains the extracted historical text. Original checkout photos remain outside this repository; their filenames and asset mapping are in `editorial/checkout-photo-sources.json`. The committed web copies are sufficient for ongoing editing, viewing, and builds. Reprocessing originals is optional and requires supplying their folder to `tools/prepare_checkout_photos.py`.

All artwork, source fragments, prompts, review records, generated HTML, and preview assets are included. Check `git status` and recent history when resuming; the previous chat's statements about local or remote state may be older than the checkout.
