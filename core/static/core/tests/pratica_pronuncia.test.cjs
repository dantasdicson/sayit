const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup(word = 'fin') {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      dataset: {}, textContent: '', hidden: false, listeners: {},
      addEventListener(event, fn) { this.listeners[event] = fn; },
      setAttribute() {}, removeAttribute() {}, focus() {}, pause() {},
      click() { if (!this.disabled) this.listeners.click(); },
    });
    return elements.get(id);
  }
  element('practice-words').textContent = JSON.stringify([{ palavra: word, audio: '', imagem: '', traducao: '' }]);
  element('pronuncia-variantes').textContent = fs.readFileSync(path.join(__dirname, '../../../data/pronuncia_variantes.json'), 'utf8');
  let recognition;
  class Recognition {
    constructor() { recognition = this; }
    start() { this.onstart(); }
  }
  const context = { window: { SpeechRecognition: Recognition, isSecureContext: true, addEventListener() {} },
    document: { getElementById: element }, setTimeout() {}, clearTimeout() {} };
  vm.runInNewContext(['pronuncia.js', 'pratica_modulo_1.js'].map(name => fs.readFileSync(path.join(__dirname, '..', name), 'utf8')).join('\n'), context);
  element('microphone').click();
  return { element, recognition };
}

test('prática reutiliza variantes e alternativas mostrando a palavra esperada', () => {
  const { element, recognition } = setup();
  const result = [{ transcript: '10' }, { transcript: 'Finn!' }]; result.isFinal = true;
  recognition.onresult({ results: [result] }); recognition.onend();
  assert.equal(element('feedback').dataset.result, 'correct');
  assert.equal(element('feedback-text').textContent, 'Eu entendi: fin');
  assert.equal(recognition.maxAlternatives, 3);
});

test('prática recusa eleven sozinho e ignora alternativa parcial', () => {
  const { element, recognition } = setup();
  const partial = [{ transcript: 'Finn' }]; partial.isFinal = false;
  recognition.onresult({ results: [partial] });
  assert.notEqual(element('feedback').dataset.result, 'correct');
  const result = [{ transcript: 'eleven' }]; result.isFinal = true;
  recognition.onresult({ results: [result] }); recognition.onend();
  assert.equal(element('feedback').dataset.result, 'incorrect');
  assert.equal(element('feedback-text').textContent, 'Eu entendi: eleven');
});

test('prática mostra mad para a exceção Matt', () => {
  const { element, recognition } = setup('mad');
  const result = [{ transcript: 'Matt' }]; result.isFinal = true;
  recognition.onresult({ results: [result] }); recognition.onend();
  assert.equal(element('feedback').dataset.result, 'correct');
  assert.equal(element('feedback-text').textContent, 'Eu entendi: mad');
});

test('prática mostra cat para a exceção cats', () => {
  const { element, recognition } = setup('cat');
  const result = [{ transcript: 'cats' }]; result.isFinal = true;
  recognition.onresult({ results: [result] }); recognition.onend();
  assert.equal(element('feedback').dataset.result, 'correct');
  assert.equal(element('feedback-text').textContent, 'Eu entendi: cat');
});
