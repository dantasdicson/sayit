const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { runInNewContext } = require('node:vm');
const source = readFileSync(join(__dirname, '../resumo_audio.js'), 'utf8');

function setup({ missing = false, play } = {}) {
  const element = () => ({
    hidden: true, textContent: '', listeners: {},
    addEventListener(name, fn) { this.listeners[name] = fn; },
    setAttribute(name, value) { this[name] = value; },
    removeAttribute(name) { delete this[name]; },
  });
  const player = element(), button = element(), label = element(), status = element();
  let plays = 0, pauses = 0;
  player.controls = true;
  player.play = () => { plays++; return play ? play() : Promise.resolve(); };
  player.pause = () => { pauses++; player.listeners.pause?.(); };
  const window = element();
  const elements = { 'summary-audio': player, 'summary-listen': button, 'summary-listen-label': label, 'audio-status': status };
  runInNewContext(source, { window, document: { getElementById: id => missing ? null : elements[id] } });
  return { player, button, label, status, window, click: () => button.listeners.click(), plays: () => plays, pauses: () => pauses };
}

test('sem áudio, o script não tenta reproduzir', () => {
  const app = setup({ missing: true });
  assert.equal(app.plays(), 0); assert.equal(app.button.hidden, true);
});

test('inicia por botão e fornece feedback textual e acessível', async () => {
  const app = setup();
  assert.equal(app.button.hidden, false);
  await app.click();
  assert.equal(app.plays(), 1);
  assert.equal(app.button['aria-pressed'], 'true');
  assert.equal(app.label.textContent, 'Interromper explicação');
  assert.equal(app.status.textContent, 'Reproduzindo explicação.');
});

test('segundo clique interrompe, terceiro reproduz do início', async () => {
  const app = setup(); await app.click(); app.player.currentTime = 5;
  await app.click();
  assert.equal(app.pauses(), 1); assert.equal(app.plays(), 1);
  assert.equal(app.player.currentTime, 0); assert.equal(app.button['aria-pressed'], 'false');
  await app.click(); assert.equal(app.plays(), 2);
});

test('cliques enquanto carrega não sobrepõem reprodução nem aceitam resposta tardia', async () => {
  let resolve;
  const app = setup({ play: () => new Promise(done => { resolve = done; }) });
  const first = app.click(); await app.click(); resolve(); await first;
  assert.equal(app.plays(), 1); assert.equal(app.pauses(), 1);
  assert.equal(app.button['aria-pressed'], 'false');
  assert.match(app.status.textContent, /interrompida/);
});

test('fim da narração permite ouvir novamente', async () => {
  const app = setup(); await app.click(); app.player.listeners.ended();
  assert.equal(app.label.textContent, 'Ouvir explicação');
  assert.equal(app.button['aria-busy'], undefined);
  await app.click(); assert.equal(app.plays(), 2);
});

test('falha de play ou erro de mídia mostra mensagem e permite nova tentativa', async () => {
  const app = setup({ play: () => Promise.reject(new Error('media failure')) });
  await app.click(); assert.match(app.status.textContent, /Não foi possível/);
  assert.equal(app.button['aria-pressed'], 'false');
  await app.click(); assert.equal(app.plays(), 2);
  app.player.listeners.error(); assert.match(app.status.textContent, /Tente novamente/);
});

test('sair da página interrompe a narração', async () => {
  const app = setup(); await app.click(); app.window.listeners.pagehide();
  assert.equal(app.pauses(), 1); assert.equal(app.button['aria-pressed'], 'false');
});
