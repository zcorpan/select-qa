# `stretch` sizing keyword is off by default, so anchored popovers styled like the spec's picker overflow (known: bug 1789477)

**Target:** existing [bug 1789477](https://bugzil.la/1789477)
(CSS Parsing and Computation, NEW, "Implement `stretch` keyword for sizing properties"). A data
point. `layout.css.stretch-size-keyword.enabled` is `false` in Nightly 161.0a1.

Without it, `max-block-size: stretch` is invalid (computes to `none`). An anchor-positioned popover
using the spec's picker styles then isn't capped to its `position-area`, and
`position-try-order: most-block-size` can't make the larger side fit. Same in Nightly with the
customizable-select prefs on and off, so it isn't the feature itself. Gecko's picker UA style uses
`-moz-available` instead, which doesn't cap either; see finding 01.

| Test | Chrome Canary 159 | Nightly 161 (default and prefs on) | Nightly + `layout.css.stretch-size-keyword.enabled` |
|---|---|---|---|
| [`f6`](../../tests/f6-popover-fallback-tall.html) tall popover, spec picker styles | flips above, fits | below, overflows | flips above, fits |
| [`f7`](../../tests/f7-stretch-only.html) `max-block-size: stretch`, no fallbacks | capped below | overflows | capped below |

Results: `local-out/fallback4.json`, `local-out/fallback4-stretch.json`.
