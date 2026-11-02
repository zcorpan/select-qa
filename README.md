# `<select>` QA: Firefox Nightly with customizable select vs Chrome Canary on pages that use it

A quick, local-only run. It tested Firefox Nightly 161.0a1 with `dom.select.customizable_select.enabled`
and `layout.css.appearance-base.enabled` on, against Chrome Canary 159.0.8136.0 and Nightly with
both prefs off, on 98 Common Crawl pages with `<select>` and on local test pages built from them.
Findings are in [`findings/`](findings/), one directory per cause, each with a test case and
per-browser results. Nothing has been filed.

## Findings, ranked by impact

| # | Target | Issues | Finding |
|---|---|---|---|
| [01](findings/01-picker-max-block-size/finding.md) | Bugzilla, Core :: Layout: Form Controls | not filed | A tall `::picker(select)` isn't capped to the viewport; options past the edge are unreachable (UA style uses `-moz-available`, spec says `stretch`) |
| [02](findings/02-picker-keyboard/finding.md) | Bugzilla | [bug 2071782](https://bugzil.la/2071782) (known) | Keyboard can't move through or commit options in the picker |

## Findings in the infrastructure the feature builds on

| # | Target | Issues | Finding |
|---|---|---|---|
| [infra-01](findings/infra-01-stretch-keyword/finding.md) | Bugzilla | [bug 1789477](https://bugzil.la/1789477) (known) | `stretch` sizing keyword is off by default, so anchored popovers with the spec's picker styles overflow |

Site differences, not engine bugs: artheroes.com and werkaandemuur.nl show Nightly a geo-based
"ship to…" modal and a cookie dialog that block the page until dismissed, and slangzone.net shows a
Funding Choices consent overlay. `sites.py` dismisses them. Firefox's window can't give a viewport
narrower than 500px, so slangzone.net ran at 500px in every setup.

## 1. Where the feature is used

Local Common Crawl CC-MAIN-2026-39, the 12 WARCs of seed 11397 (all crawled URLs, not only root
pages; no rank). No BigQuery. `scan/scan.py` regex-scans every HTTP 200 `text/html` response;
`scan/summarize.py` prints the counts:

- 255,716 HTML responses; 45,956 (18.0%) contain `<select`.
- 908 have a tag other than `option`/`optgroup`/`hr`/`script`/`template`/`noscript` between
  `<select>` and `</select>` (most often `span`, `i`, `div`, `a`, `img`). This is a regex superset.
- 35 match `base-select`, `::picker(select)`, `<selectedcontent`, `::picker-icon` or `::checkmark`.
  Most are a `base-select` CSS class name. Only 3 hosts really use customizable select:
  artheroes.com and werkaandemuur.nl (one platform, `<button><div><selectedcontent>` in a
  language dialog) and slangzone.net (`::picker(select)`, optgroups, flag images).
- Select libraries (pages): select2 2,889, chosen 1,000, bootstrap-select 690, nice-select 348,
  sumoselect 200, selectize 186, choices 145, slimselect 54, tom-select 44.

## 2. Live comparison

Setups: A and A2 Chrome Canary 159.0.8136.0 (reference, twice for noise; Playwright, headless);
B Firefox Nightly 161.0a1 with both prefs on (candidate; Selenium, BiDi, headless); C Nightly with
both off (control). B uses the same prefs Gecko's own wpt metadata sets for
`the-select-element/customizable-select`. `dom.select.customizable_select.enabled` alone gives
`appearance: base-select` without the base UA styles. Desktop 1366×768, load-only, 3s settle.

Pages ([`pages-batch1.txt`](pages-batch1.txt), seeded by sha256 of `select-qa` + URL, at most one
or two per host): 23 matching customizable-select syntax, 40 with rich content inside a select
(body ends in `</body>`/`</html>`), 25 with a select library, 10 other.

[`qa.py`](qa.py) records per `<select>` its options length, selected index, hashed value and
option text, size, `appearance`, `display`, and its non-option children. A preload trace counts
select and option API calls and listeners. It also records exceptions and console errors and
warnings. [`analyze_qa.py`](analyze_qa.py) flags B≠C in select state, B-only errors or console
messages, B≠A where C=A and A=A2, and `base-select` selects whose size in B is far off A.

Stopping rule: one batch plus rechecks, then targeted interaction on the customizable-select sites
and local tests (scope agreed for a quick run).

### Page results

98 visits per setup. Scripts called the select APIs on 88 pages in B. 5 pages (the 3 real hosts)
had a `base-select` select in A and B, and none of them was visible at load: each sits in a closed
dialog or collapsed nav. Load-only flagged 4 pages, all from console noise or select counts that
changed between loads. None reproduced in two rechecks per setup.

Since load-only never reached the customizable selects, [`sites.py`](sites.py) opened them with
real input on the 3 sites: open the dialog or nav, click the select, click another option. In B,
the picker opened with every option laid out on all 3. Picking fired `input` and `change` where
the page listens and updated `<selectedcontent>`, as in A. One difference: slangzone.net's picker
opens downward off-screen in B (finding 01).

## 3. Local tests

Served from [`tests/`](tests/), run by [`local.py`](local.py) (click, pick, keys) and
[`fallback.py`](fallback.py) (picker placement), in A, B, C.

- `t1-picker-flags.html` (slangzone.net pattern) and `t2-nested-selectedcontent.html`
  (artheroes.com pattern): `<selectedcontent>` cloning, mouse open and pick, and `change`/`input`
  match Canary in B. Keyboard doesn't (finding 02).
- `t3-legacy-rich.html`: `appearance: auto` select with `div`/`span`/`img` inside. Options and
  selection are the same in B and C.
- `f1`–`f4`: short picker and plain popover near the bottom-right corner, also inside a
  `position: fixed` container. They flip and fit in A and B.
- `f5`–`f8`: tall picker and controls (finding 01, infra-01). `wheel_check.py` checks
  reachability.

## Not covered

Safari TP, mobile emulation, Windows/Linux keyboard behavior (finding 02's code path is
macOS-specific), `<select multiple>` and list boxes with base appearance, pages that build
customizable selects from script, and anything beyond the 3 real customizable-select sites. The
crawl has too few of them to say more.

## Why the run stopped here

The agreed quick scope (one batch, rechecks, targeted interaction, local tests) is done. Few pages
use customizable select (3 hosts in 256k pages), so a bigger random batch wouldn't reach new code
paths. A follow-up would need pages found by their CSS (`::picker(select)`) in HTTP Archive and
pages that build customizable selects from script.

## Reproduce

```sh
python3 -m venv .venv && .venv/bin/pip install warcio selenium playwright pillow
.venv/bin/python -I scan/scan.py ~/git/commoncrawl/cc-data/CC-MAIN-2026-39 scan/pages.jsonl
for s in A A2 B C; do .venv/bin/python -I qa.py $s pages-batch1.txt out/b1-$s.jsonl; done
python3 analyze_qa.py out/b1 > out/b1-flags.json
.venv/bin/python -I sites.py local-out/sites5.json B C   # A: local-out/sites4.json
.venv/bin/python -I local.py local-out/run2.json A B C
HEADFUL=1 .venv/bin/python -I local.py local-out/run3-headful.json A B
.venv/bin/python -I fallback.py local-out/fallback4.json A B C
.venv/bin/python -I fallback_stretch.py local-out/fallback4-stretch.json
.venv/bin/python -I wheel_check.py chrome > local-out/wheel-chrome.txt
.venv/bin/python -I wheel_check.py > local-out/wheel-firefox.txt
python3 counts.py   # recomputes every number above
```

Live pages change, so a rerun won't match exactly. Screenshots and page text aren't committed.
