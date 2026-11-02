// Shared by the local tests: window.state() reports the first select's state as JSON.
window.log = [];
for (const e of ['change', 'input', 'click', 'mousedown', 'keydown'])
  document.addEventListener(e, ev => log.push(e + ':' + (ev.target.localName || '')), true);
window.state = () => {
  const s = document.querySelector('select'), r = s.getBoundingClientRect();
  const sc = s.querySelector('selectedcontent');
  const vis = [...s.querySelectorAll('option')].map(o => { const q = o.getBoundingClientRect(); return [Math.round(q.left), Math.round(q.top), Math.round(q.width), Math.round(q.height)]; });
  let open = null; try { open = s.matches(':open'); } catch (e) { open = 'unsupported'; }
  return {
    app: getComputedStyle(s).appearance, display: getComputedStyle(s).display,
    rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
    value: s.value, idx: s.selectedIndex, open,
    focused: document.activeElement === s || s.contains(document.activeElement),
    active: document.activeElement ? document.activeElement.localName + (document.activeElement.value !== undefined ? '=' + document.activeElement.value : '') : null,
    selectedcontent: sc ? sc.innerHTML.replace(/\s+/g, ' ').trim() : null,
    options: vis, log: log.splice(0),
  };
};
