const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../registro_erros.js'), 'utf8');

function setup() {
  const listeners = {};
  const requests = [];
  const window = { addEventListener: (name, fn) => { listeners[name] = fn; } };
  vm.runInNewContext(source, {
    window,
    fetch: async (url, options) => { requests.push({ url, ...options }); return { ok: true }; },
  });
  const emit = detail => listeners['sayit:attempt-error']({ detail });
  return { requests, emit };
}

test('registra fala incorreta com os identificadores e CSRF', async () => {
  const app = setup();
  app.emit({ url: '/modulos/5/progresso/erros/', csrf: 'token', comparisonId: 17,
    wordId: 41, transcript: 'show', result: 'incorreto' });
  await Promise.resolve();
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0].headers['X-CSRFToken'], 'token');
  assert.deepEqual(JSON.parse(app.requests[0].body), {
    comparacao_id: 17, palavra_id: 41, transcricao: 'show', resultado: 'incorreto',
  });
});

test('registra silêncio e rejeita tipos de resultado não permitidos', async () => {
  const app = setup();
  const base = { url: '/erros/', csrf: 'token', comparisonId: 17, wordId: 41, transcript: '' };
  app.emit({ ...base, result: 'nao_reconhecido' });
  app.emit({ ...base, result: 'correto' });
  await Promise.resolve();
  assert.equal(app.requests.length, 1);
  assert.equal(JSON.parse(app.requests[0].body).resultado, 'nao_reconhecido');
});
