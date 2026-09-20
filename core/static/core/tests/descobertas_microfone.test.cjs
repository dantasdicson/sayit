const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../descobertas_microfone.js'), 'utf8');

function setup(pair = ['cat', 'cake'], options = {}) {
  class Element {
    constructor() { this.dataset = {}; this.listeners = {}; this.disabled = false; this.hidden = true; this.textContent = ''; }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    setAttribute(name, value) { this[name] = value; }
    focus() {}
    click() { if (!this.disabled) this.listeners.click?.(); }
    dispatch() { this.listeners.click?.(); }
  }
  const roots = pair.map(expected => {
    const root = new Element();
    root.dataset.practiceWord = expected;
    root.children = Object.fromEntries(['speak', 'speak-label', 'speech-title', 'speech-message', 'word-complete'].map(key => [key, new Element()]));
    root.querySelector = selector => root.children[selector.slice(1)];
    return root;
  });
  const next = new Element();
  next.dataset.nextUrl = options.url || '/modulos/1/descoberta/2/';
  const status = new Element();
  const audio = new Element();
  const player = { pause() {} };
  const instances = [], navigations = [], timers = new Map();
  class Recognition {
    constructor() { if (options.constructorError) throw new Error('unavailable'); instances.push(this); }
    start() { if (options.startError) throw options.startError; this.onstart?.(); }
    stop() {}
    abort() { this.onerror?.({ error: 'aborted' }); this.onend?.(); }
    result(text, isFinal = true) { const result = [{ transcript: text }]; result.isFinal = isFinal; this.onresult({ resultIndex: 0, results: [result] }); }
    end() { this.onend(); }
    error(error) { this.onerror({ error }); this.onend(); }
  }
  const window = {
    isSecureContext: options.secure !== false,
    location: { assign: url => navigations.push(url) },
    addEventListener(name, fn) { this[name] = fn; },
  };
  if (!options.unsupported) window[options.webkit ? 'webkitSpeechRecognition' : 'SpeechRecognition'] = Recognition;
  vm.runInNewContext(source, {
    window,
    document: {
      getElementById: id => id === 'discovery-next' ? next : status,
      querySelectorAll: selector => selector === '[data-practice-word]' ? roots : selector === 'audio' ? [player] : [audio],
    },
    setTimeout(fn) { const id = timers.size + 1; timers.set(id, fn); return id; },
    clearTimeout(id) { timers.delete(id); },
  });
  const start = index => { roots[index].children.speak.click(); return instances.at(-1); };
  const say = (index, text) => { const r = start(index); r.result(text); r.end(); return r; };
  const locked = () => { assert.equal(next.disabled, true); next.click(); next.dispatch(); assert.deepEqual(navigations, []); };
  const done = index => !roots[index].children['word-complete'].hidden;
  return { roots, next, status, start, say, locked, done, instances, navigations, timers, window, audio };
}

for (const [index, pair] of [['cat', 'cake'], ['cap', 'cape'], ['tap', 'tape'], ['mad', 'made']].entries()) {
  test(`Descoberta ${index + 1}: ambas obrigatórias e destino preservado`, () => {
    const url = index === 3 ? '/modulos/1/resumo/' : `/modulos/1/descoberta/${index + 2}/`;
    const app = setup(pair, { url });
    app.locked();
    app.audio.click(); app.locked();
    app.say(0, pair[0]); app.locked();
    assert.equal(app.done(0), true); assert.equal(app.done(1), false);
    app.say(1, 'wrong'); app.locked();
    assert.equal(app.done(0), true); assert.equal(app.done(1), false);
    app.say(1, pair[1]);
    assert.equal(app.next.disabled, false);
    assert.equal(app.done(0), true); assert.equal(app.done(1), true);
    app.next.click(); assert.deepEqual(app.navigations, [url]);
    assert.match(app.status.textContent, new RegExp(pair.join(' e '), 'i'));
  });
}

test('CAT errado + CAKE correto continua bloqueado; repetir CAT libera', () => {
  const app = setup(); app.say(0, 'dog'); app.say(1, 'cake'); app.locked();
  assert.equal(app.done(0), false); assert.equal(app.done(1), true);
  app.say(0, ' CAT! '); assert.equal(app.next.disabled, false);
});

for (const error of ['no-speech', 'not-allowed', 'service-not-allowed', 'network', 'audio-capture', 'aborted']) {
  test(`${error}: bloqueia, preserva a outra palavra e ignora resultado tardio`, () => {
    const app = setup(); app.say(0, 'cat');
    const r = app.start(1); r.error(error); r.result('cake');
    app.locked(); assert.equal(app.done(0), true); assert.equal(app.done(1), false);
    if (!error.includes('allowed')) { app.say(1, 'cake'); assert.equal(app.next.disabled, false); }
  });
}

for (const text of ['', '   ', '...', 'cat cake', 'dog', null]) {
  test(`resultado inválido ${JSON.stringify(text)} não conclui`, () => {
    const app = setup(); app.say(0, text); app.locked(); assert.equal(app.done(0), false);
  });
}

test('silêncio, resultado parcial e fim sem resultado não concluem', () => {
  const app = setup(); app.start(0).end(); app.locked();
  const r = app.start(0); r.result('cat', false); r.end();
  app.locked(); assert.equal(app.done(0), false);
  app.say(0, 'cat'); assert.equal(app.done(0), true);
});

test('resultado final aguarda fim normal; erro posterior invalida a tentativa', () => {
  const app = setup(); app.say(0, 'cat');
  const r = app.start(1); r.result('cake'); app.locked();
  r.error('aborted'); app.locked(); assert.equal(app.done(1), false);
});

test('timeout e saída da página cancelam sem aceitar eventos tardios', () => {
  for (const exit of [false, true]) {
    const app = setup(); app.say(0, 'cat');
    const r = app.start(1); r.result('cake');
    if (exit) app.window.pagehide(); else [...app.timers.values()][0]();
    r.result('cake'); r.end(); app.locked();
    assert.equal(app.done(0), true); assert.equal(app.done(1), false);
    app.say(1, 'cake'); assert.equal(app.next.disabled, false);
  }
});

for (const options of [{ unsupported: true }, { secure: false }, { constructorError: true }, { startError: new Error('failed') }, { startError: { name: 'NotAllowedError' } }]) {
  test(`indisponibilidade ${JSON.stringify(options)} bloqueia`, () => {
    const app = setup(undefined, options); app.start(0); app.locked();
    assert.equal(app.done(0), false); assert.equal(app.done(1), false);
  });
}

test('API prefixada funciona; cliques durante reconhecimento não iniciam outra sessão', () => {
  const app = setup(undefined, { webkit: true });
  const r = app.start(0); app.roots[1].children.speak.dispatch();
  assert.equal(app.instances.length, 1); app.locked();
  r.result('cat'); r.end(); app.say(1, 'cake'); assert.equal(app.next.disabled, false);
});

test('configuração incompleta nunca libera avanço', () => {
  const app = setup(['cat']); app.say(0, 'cat'); app.locked();
});
