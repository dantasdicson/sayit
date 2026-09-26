const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { runInNewContext } = require('node:vm');
const source = readFileSync(join(__dirname, '../resumo_audio.js'), 'utf8');

function setup({ missing = false, play, alreadyComplete = false } = {}) {
  const element = () => ({
    hidden: true, textContent: '', listeners: {},
    addEventListener(name, fn) { this.listeners[name] = fn; },
    setAttribute(name, value) { this[name] = value; },
    removeAttribute(name) { delete this[name]; },
  });
  const player = element(), button = element(), label = element(), status = element(), complete = element();
  complete.dataset = alreadyComplete ? { alreadyComplete: '' } : {};
  let plays = 0, pauses = 0;
  player.controls = true;
  player.play = () => { plays++; return play ? play() : Promise.resolve(); };
  player.pause = () => { pauses++; player.listeners.pause?.(); };
  const window = element();
  const elements = { 'summary-audio': player, 'summary-listen': button, 'summary-listen-label': label,
    'audio-status': status, 'summary-complete': complete };
  runInNewContext(source, { window, document: { getElementById: id => missing ? null : elements[id] } });
  return { player, button, complete, label, status, window,
    click: () => button.listeners.click(), plays: () => plays, pauses: () => pauses };
}

test('sem áudio, o script não tenta reproduzir', () => {
  const app = setup({ missing: true });
  assert.equal(app.plays(), 0); assert.equal(app.button.hidden, true);
});

test('inicia automaticamente e permite repetir desde o início', async () => {
  const app = setup();
  await new Promise(setImmediate);
  assert.equal(app.plays(), 1);
  assert.equal(app.button.hidden, false);
  assert.equal(app.label.textContent, 'Ouvir explicação novamente');
  assert.equal(app.status.textContent, 'Reproduzindo explicação.');
  assert.equal(app.button['aria-busy'], undefined);
  assert.equal(app.complete.disabled, true);
  app.player.currentTime = 5;
  await app.click();
  assert.equal(app.pauses(), 1);
  assert.equal(app.plays(), 2);
  assert.equal(app.player.currentTime, 0);
});

test('bloqueio de autoplay permite iniciar pelo botão', async () => {
  let first = true;
  const app = setup({ play: () => {
    if (first) { first = false; return Promise.reject(Object.assign(new Error(), { name: 'NotAllowedError' })); }
    return Promise.resolve();
  }});
  await new Promise(setImmediate);
  assert.match(app.status.textContent, /Toque em Ouvir explicação novamente/);
  assert.equal(app.complete.disabled, false);
  await app.click();
  assert.equal(app.plays(), 2);
  assert.equal(app.status.textContent, 'Reproduzindo explicação.');
  assert.equal(app.complete.disabled, true);
});

test('resposta atrasada de autoplay não sobrescreve uma nova reprodução', async () => {
  const pending = [];
  const app = setup({ play: () => new Promise((resolve, reject) => pending.push({resolve, reject})) });
  const next = app.click();
  pending[1].resolve(); await next;
  pending[0].reject(new Error('interrompido')); await new Promise(setImmediate);
  assert.equal(app.status.textContent, 'Reproduzindo explicação.');
  assert.equal(app.plays(), 2);
});

test('fim da narração libera a conclusão mesmo durante uma repetição', async () => {
  const app = setup(); await new Promise(setImmediate); app.player.listeners.ended();
  assert.equal(app.label.textContent, 'Ouvir explicação novamente');
  assert.equal(app.button['aria-busy'], undefined);
  assert.equal(app.complete.disabled, false);
  await app.click(); assert.equal(app.plays(), 2); assert.equal(app.complete.disabled, false);
});

test('falha de mídia mostra mensagem e permite nova tentativa', async () => {
  const app = setup({ play: () => Promise.reject(new Error('media failure')) });
  await new Promise(setImmediate); assert.match(app.status.textContent, /Não foi possível/);
  assert.equal(app.complete.disabled, false);
  await app.click(); assert.equal(app.plays(), 2);
  app.player.listeners.error(); assert.match(app.status.textContent, /Tente novamente/);
  assert.equal(app.complete.disabled, false);
});

test('interrupção no celular não impede concluir descobertas já realizadas', async () => {
  const app = setup(); await new Promise(setImmediate);
  assert.equal(app.complete.disabled, true);
  app.player.paused = true;
  app.player.listeners.pause();
  assert.equal(app.complete.disabled, false);
  assert.match(app.status.textContent, /concluir o módulo/);
  await app.click();
  assert.equal(app.plays(), 2);
});

test('atributo booleano vazio preserva a conclusão durante revisão', async () => {
  const app = setup({ alreadyComplete: true }); await new Promise(setImmediate);
  assert.equal(app.complete.disabled, false);
  await app.click();
  assert.equal(app.complete.disabled, false);
});

test('sair da página interrompe inclusive autoplay pendente', async () => {
  let resolve;
  const app = setup({play: () => new Promise(done => { resolve = done; })});
  app.window.listeners.pagehide(); resolve(); await new Promise(setImmediate);
  assert.equal(app.pauses(), 1);
  assert.equal(app.button['aria-pressed'], 'false');
  assert.match(app.status.textContent, /interrompida/);
});
