const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function browser(hostname = '192.168.1.190', protocol = 'http:') {
  class Element {
    constructor() { this.children = []; this.textContent = ''; this.className = ''; this.parent = null; this.scrollTop = 0; this.clientHeight = 250; this.listeners = {}; }
    get scrollHeight() { return this.children.length * 30; }
    appendChild(child) { child.remove(); child.parent = this; this.children.push(child); }
    append(...children) { children.forEach(c => this.appendChild(c)); }
    replaceChildren() { this.children.forEach(c => c.parent = null); this.children = []; this.textContent = ''; }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(c => c !== this); this.parent = null; }
    addEventListener(name, fn) { this.listeners[name] = fn; }
  }
  const elements = Object.fromEntries(['status', 'live', 'recall'].map(id => [id, new Element()]));
  const buttons = [30, 15, 60].map(seconds => { const e = new Element(); e.dataset = { seconds: String(seconds) }; return e; });
  const sockets = [], timers = new Map();
  let clock = 1800000000000, nextTimer = 1;
  class Socket {
    constructor(url) { this.url = url; this.listeners = {}; this.sent = []; sockets.push(this); }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    emit(name, event = {}) { this.listeners[name]?.(event); }
    send(raw) { this.sent.push(JSON.parse(raw)); }
    close() { this.emit('close'); }
  }
  const storage = new Map();
  const context = vm.createContext({
    window: { location: { hostname, protocol } },
    document: { getElementById: id => elements[id], createElement: () => new Element(), querySelectorAll: () => buttons },
    WebSocket: Socket, console: { log() {} },
    sessionStorage: { getItem: k => storage.get(k), setItem: (k, v) => storage.set(k, v) },
    Date: class extends Date { static now() { return clock; } },
    setTimeout(fn) { const id = nextTimer++; timers.set(id, fn); return id; },
    clearTimeout(id) { timers.delete(id); }, setInterval() {},
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../client/app.js'), 'utf8'), context);
  sockets[0].emit('open');
  return {
    elements, sockets, timers, buttons,
    now: () => clock / 1000,
    advance: seconds => clock += seconds * 1000,
    update: msg => sockets.at(-1).emit('message', { data: JSON.stringify(msg) }),
    evaluate: code => vm.runInContext(code, context),
    reconnect() { const [id, fn] = timers.entries().next().value; timers.delete(id); fn(); sockets.at(-1).emit('open'); },
  };
}
function caption(b, segment, revision = 3, final = true, age = 0) {
  return { type: 'CAPTION_UPDATE', session: 'L1', segment, revision, final, source_ts: b.now() - age, text: `Caption ${segment} revision ${revision}` };
}

test('browser connects to the host serving the page, including file fallback', () => {
  assert.equal(browser().sockets[0].url, 'ws://192.168.1.190:8765');
  assert.equal(browser('', 'file:').sockets[0].url, 'ws://127.0.0.1:8765');
  assert.equal(browser('example.test', 'https:').sockets[0].url, 'wss://example.test:8765');
});
test('new revisions replace one line and older revisions cannot overwrite a final', () => {
  const b = browser();
  b.update(caption(b, 1, 1, false)); b.update(caption(b, 1, 2, false));
  assert.equal(b.elements.live.children.length, 1);
  assert.match(b.elements.live.children[0].textContent, /revision 2/);
  b.update(caption(b, 1)); b.update(caption(b, 1, 2, false));
  assert.equal(b.elements.live.children.length, 1);
  assert.equal(b.elements.live.children[0].className, 'caption final');
  assert.match(b.elements.live.children[0].textContent, /revision 3/);
});
test('15/30/60-second recall uses local finals without a server request', () => {
  const b = browser();
  b.update(caption(b, 1, 3, true, 50)); b.update(caption(b, 2, 3, true, 25)); b.update(caption(b, 3, 3, true, 5));
  for (const [seconds, count] of [[15, 1], [30, 2], [60, 3]]) {
    b.buttons.find(e => e.dataset.seconds === String(seconds)).listeners.click();
    assert.equal(b.elements.recall.children.length, count);
  }
  assert.equal(b.sockets[0].sent.length, 1);
  b.advance(71); b.evaluate('remove_old_entries()');
  assert.equal(b.evaluate('finalizedHistory.size'), 0);
  assert.equal(b.elements.live.children.length, 0);
});
test('reconnect sends the final checkpoint and merges HISTORY without duplicates', () => {
  const b = browser(); b.update(caption(b, 1));
  b.sockets[0].emit('close');
  assert.equal(b.elements.status.textContent, 'reconnecting');
  assert.equal(b.timers.size, 1);
  b.reconnect();
  assert.equal(b.sockets[1].sent[0].last_segment, 1);
  assert.equal(b.sockets[1].sent[0].last_revision, 3);
  b.update({ type: 'HISTORY', items: [caption(b, 1), caption(b, 2), caption(b, 2)] });
  assert.equal(b.elements.live.children.length, 2);
  assert.equal(b.evaluate('finalizedHistory.size'), 2);
});
test('a later recovered final removes an abandoned provisional after a long outage', () => {
  const b = browser(); b.update(caption(b, 1, 1, false)); b.advance(80);
  b.update({ type: 'HISTORY', items: [caption(b, 100)] });
  assert.equal(b.elements.live.children.length, 1);
  assert.equal(b.evaluate('captions.has(1)'), false);
});
