# Customizable select: a tall `::picker(select)` isn't capped to the viewport, so options past its edge can't be reached

**Target:** Bugzilla, Core :: Layout: Form Controls (customizable select,
`dom.select.customizable_select.enabled` + `layout.css.appearance-base.enabled`).

With customizable select enabled in Firefox Nightly 161.0a1, a `base-select` picker taller than the
space around its `<select>` grows to its full content height. It doesn't flip to the side with more
room, and it isn't capped or scrollable. Options past the viewport edge can't be reached with the
mouse or the wheel. Chrome Canary 159 flips the picker above the select, caps it to the viewport,
and makes it scrollable.

Gecko's UA style for the picker uses `max-block-size: -moz-available`
([`layout/style/res/forms.css#278`](https://searchfox.org/firefox-main/rev/e924f94175311819d7b549a732d0d8ee1263b31d/layout/style/res/forms.css#278),
from bug 2044275). The HTML spec's
[select rendering styles](https://html.spec.whatwg.org/multipage/rendering.html#the-select-element-2)
give `::picker(select) { max-block-size: stretch; position-try-order: most-block-size; ... }`.
In the block axis, `-moz-available` doesn't limit an anchor-positioned box to its
`position-area` (test f8). Nothing caps the picker, so no position option fits, and
`most-block-size` can't pick the larger side. With `layout.css.stretch-size-keyword.enabled` also
on, a plain popover with the spec's picker styles behaves like Chrome (f6), but the select picker
still overflows (f5), because the UA sheet doesn't use `stretch`.

## Test

[`tests/f5-select-fallback-tall.html`](../../tests/f5-select-fallback-tall.html): a `base-select`
with 40 options, 100px above the bottom of an 800×600 viewport. Click it.

| Browser | Picker | Options on screen after opening | After a wheel scroll over the picker |
|---|---|---|---|
| Chrome Canary 159.0.8136.0 | above the select, capped, scrolls | 0–23 | 21–39 |
| Firefox Nightly 161.0a1, both prefs on | below the select, runs off the viewport | 0–3 | 0–3 (page `scrollY` 0) |
| Firefox Nightly 161.0a1, both prefs on, plus `layout.css.stretch-size-keyword.enabled` | below, runs off the viewport | (same) | |

Controls, same viewport: [`f6`](../../tests/f6-popover-fallback-tall.html) (a plain popover with the
spec's picker styles) flips above and fits in Chrome. In Firefox it does that only with
`layout.css.stretch-size-keyword.enabled` (see infra-01).
[`f8`](../../tests/f8-moz-available-only.html) (`max-block-size: -moz-available`, no fallbacks)
overflows in Firefox with and without that pref. Screenshots: [`f5-f6-screenshots.png`](f5-f6-screenshots.png)
(rows f5, f6; columns Chrome, Firefox with the prefs on, Firefox default). Results:
`local-out/fallback4.json`, `local-out/fallback4-stretch.json`, `local-out/wheel-*.txt`.

## Pages

1 of the 3 sites in the sample whose customizable select we could open: slangzone.net, whose
language `<select>` sits at the bottom of a `position: fixed` mobile nav. At a 500px viewport the
picker opens downward and off-screen. [`slangzone-canary-left-nightly-right.png`](slangzone-canary-left-nightly-right.png)
(Canary left, Nightly with the prefs on right; the page's dark theme in Nightly comes from the OS
color scheme). The other two sites (artheroes.com, werkaandemuur.nl) have 8-option pickers that fit.

## Existing reports

None found for the picker. Searched Bugzilla for "picker max-block-size", "moz-available picker",
"customizable select picker overflow viewport", "customizable select picker tall". Related:
[bug 1789477](https://bugzil.la/1789477) (`stretch` sizing keyword),
[bug 2057629](https://bugzil.la/2057629) (anchor positioning for
customizable select). Gecko expects all eight
`customizable-select/select-appearance-fallback-*.html` reftests to FAIL.
