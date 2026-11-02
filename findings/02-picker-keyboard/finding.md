# Customizable select: keyboard can't move through or commit options in the picker (known: bug 2071782)

**Target:** existing [bug 2071782](https://bugzil.la/2071782)
(DOM: Core & HTML, ASSIGNED, "Customizable Select: Implement proper keyboard navigation for
picker"). A data point, not a new report.

In Firefox Nightly 161.0a1 with both prefs on (macOS), focusing a `base-select` `<select>` and
pressing ArrowDown opens the picker, but focus stays on the `<select>`. A second ArrowDown closes
the picker again, and Enter commits nothing. On macOS, `HTMLSelectElement::HandleKeyDown` toggles
the picker on every Up/Down and returns early on Enter for non-`multiple` selects
([`dom/html/HTMLSelectElement.cpp#2684`](https://searchfox.org/firefox-main/rev/e924f94175311819d7b549a732d0d8ee1263b31d/dom/html/HTMLSelectElement.cpp#2684),
[`#2758`](https://searchfox.org/firefox-main/rev/e924f94175311819d7b549a732d0d8ee1263b31d/dom/html/HTMLSelectElement.cpp#2758)).
Chrome Canary 159 focuses the selected option when the picker opens: ArrowDown moves between options
and Enter commits and closes.

Tests: [`tests/t1-picker-flags.html`](../../tests/t1-picker-flags.html) (slangzone.net pattern:
optgroups, options with images) and
[`tests/t2-nested-selectedcontent.html`](../../tests/t2-nested-selectedcontent.html)
(artheroes.com pattern: `<button><div><selectedcontent>` plus an icon). Key sequence: Tab,
ArrowDown, Enter, Escape, ArrowDown, ArrowDown, Enter.

| Browser | After ArrowDown, focus | After Enter | ArrowDown, ArrowDown, Enter |
|---|---|---|---|
| Chrome Canary 159.0.8136.0 | the selected option | closed | next option selected, closed |
| Firefox Nightly 161.0a1, prefs on | the `<select>` | still open | second ArrowDown closes; nothing selected |

Same headful (`local-out/run3-headful.json`) and headless (`local-out/run2.json`). Mouse selection
works on all 3 sites reached (`local-out/sites5.json`). Pages: all 3 customizable-select sites in the
sample use a `base-select` picker that keyboard users can't operate this way.
