const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../pronuncia.js'), 'utf8') + '\n' + fs.readFileSync(path.join(__dirname, '../descobertas_microfone.js'), 'utf8');

for (const transcript of ['fin', 'Finn', ' FIN! ', '  Finn...  ', 'fine', 'ten', '10']) {
  test(`FIN aceita variante normalizada ${JSON.stringify(transcript)}`, async () => {
    const app = setup(['fin', 'fine'], { module: 2 });
    await app.say(0, transcript);
    assert.equal(app.done(0), true);
    app.locked();
    assert.equal(JSON.parse(app.requests[0].body).transcricao, transcript);
    assert.equal(app.roots[0].children['speech-message'].textContent, 'Eu entendi: fin');
  });
}

for (const transcript of ['fins', 'Finn fine']) {
  test(`FIN recusa ${transcript}`, async () => {
    const app = setup(['fin', 'fine']);
    await app.say(0, transcript);
    assert.equal(app.requests.length, 0); app.locked();
    assert.equal(app.roots[0].children['speech-message'].textContent, `Eu entendi: ${transcript}`);
  });
}

for (const pair of [['cat', 'cake'], ['cap', 'cape'], ['kit', 'kite'], ['hop', 'hope'], ['cub', 'cube']]) {
  test(`par ${pair.join('/')} permanece distinto nos dois sentidos`, async () => {
    const app = setup(pair);
    await app.say(0, pair[1]); await app.say(1, pair[0]);
    assert.equal(app.requests.length, 0); app.locked();
  });
}

test('alternativa válida é enviada ao servidor; feedback mostra a palavra esperada', async () => {
  const app = setup(['fin', 'fine']);
  const r = app.start(0);
  assert.equal(r.lang, 'en-US'); assert.equal(r.maxAlternatives, 3);
  const result = [{ transcript: '10' }, { transcript: 'Finn' }, { transcript: 'fin' }];
  result.isFinal = true;
  r.onresult({ resultIndex: 0, results: [result] });
  await r.end();
  assert.equal(app.done(0), true); app.locked();
  assert.equal(JSON.parse(app.requests[0].body).transcricao, '10');
  assert.equal(app.roots[0].children['speech-message'].textContent, 'Eu entendi: fin');
});

test('alternativas parciais ou sem equivalência não enviam acerto', async () => {
  for (const final of [false, true]) {
    const app = setup(['fin', 'fine']); const r = app.start(0);
    const result = [{ transcript: 'eleven' }, { transcript: final ? 'fins' : 'Finn' }];
    result.isFinal = final;
    r.onresult({ resultIndex: 0, results: [result] }); await r.end();
    assert.equal(app.requests.length, 0); app.locked();
  }
});

function setup(pair = ['cat', 'cake'], options = {}) {
  class Element {
    constructor() { this.dataset = {}; this.listeners = {}; this.disabled = false; this.hidden = true; this.textContent = ''; }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    setAttribute(name, value) { this[name] = value; }
    focus() {}
    click() { if (!this.disabled) this.listeners.click?.(); }
    dispatch() { this.listeners.click?.(); }
  }
  const roots = pair.map((expected, index) => {
    const root = new Element();
    root.dataset.practiceWord = expected;
    root.dataset.palavraId = String(41 + index);
    root.dataset.acertada = String((options.saved || []).includes(41 + index));
    root.children = Object.fromEntries(['speak', 'speak-label', 'speech-title', 'speech-message', 'word-complete'].map(key => [key, new Element()]));
    root.querySelector = selector => root.children[selector.slice(1)];
    return root;
  });
  const next = new Element();
  next.dataset.nextUrl = options.url || '/modulos/1/descoberta/2/';
  const status = new Element();
  const state = new Element();
  state.dataset = { modulo: String(options.module || 1), comparacaoId: '17', acertosUrl: `/modulos/${options.module || 1}/progresso/acertos/`,
    percentual: String(options.percentual || 0), concluida: String(options.complete || false) };
  state.querySelector = () => ({ value: options.noCsrf ? '' : 'token-csrf-teste' });
  const audio = new Element();
  const player = { pause() {} };
  const instances = [], navigations = [], timers = new Map(), requests = [];
  const saved = new Set(options.saved || []);
  const respond = (request) => {
    saved.add(JSON.parse(request.body).palavra_id);
    const complete = roots.length === 2 && roots.every(root => saved.has(Number(root.dataset.palavraId)));
    return { ok: true, json: async () => ({ modulo: options.module || 1, palavras_acertadas: [...saved],
      comparacoes_concluidas: complete ? [17] : [], percentual: complete ? ([2, 3, 4, 5].includes(options.module) ? 33 : 25) : 0 }) };
  };
  class Recognition {
    constructor() { if (options.constructorError) throw new Error('unavailable'); instances.push(this); }
    start() { if (options.startError) throw options.startError; this.onstart?.(); }
    stop() {}
    abort() { this.onerror?.({ error: 'aborted' }); this.onend?.(); }
    result(text, isFinal = true) { const result = [{ transcript: text }]; result.isFinal = isFinal; this.onresult({ resultIndex: 0, results: [result] }); }
    end() { return this.onend(); }
    error(error) { this.onerror({ error }); this.onend(); }
  }
  const window = {
    isSecureContext: options.secure !== false,
    location: { assign: url => navigations.push(url), reload: () => navigations.push('reload') },
    addEventListener(name, fn) { this[name] = fn; },
  };
  if (!options.unsupported) window[options.webkit ? 'webkitSpeechRecognition' : 'SpeechRecognition'] = Recognition;
  vm.runInNewContext(source, {
    window,
    AbortController,
    fetch: async (url, request) => {
      requests.push({ url, ...request });
      return options.fetch ? options.fetch(url, request, respond) : respond(request);
    },
    document: {
      getElementById: id => ({ 'pronuncia-variantes': { textContent: fs.readFileSync(path.join(__dirname, '../../../data/pronuncia_variantes.json'), 'utf8') }, 'discovery-next': next, 'speech-status': status, 'discovery-state': state })[id],
      querySelectorAll: selector => selector === '[data-practice-word]' ? roots : selector === 'audio' ? [player] : [audio],
    },
    setTimeout(fn) { const id = timers.size + 1; timers.set(id, fn); return id; },
    clearTimeout(id) { timers.delete(id); },
  });
  const start = index => { roots[index].children.speak.click(); return instances.at(-1); };
  const say = async (index, text) => { const r = start(index); r.result(text); await r.end(); return r; };
  const locked = () => { assert.equal(next.disabled, true); next.click(); next.dispatch(); assert.deepEqual(navigations, []); };
  const done = index => !roots[index].children['word-complete'].hidden;
  return { roots, next, status, state, start, say, locked, done, instances, navigations, timers, window, audio, requests };
}

for (const [index, pair] of [['kit', 'kite'], ['bit', 'bite'], ['fin', 'fine']].entries()) {
  test(`Módulo 2 par ${index + 1}: erro, dois acertos, áudio disponível e avanço`, async () => {
    const url = index === 2 ? '/modulos/2/resumo/' : `/modulos/2/descobertas/${index + 2}/`;
    const app = setup(pair, { module: 2, url });
    await app.say(0, 'wrong');
    assert.equal(app.requests.length, 0); app.locked();
    await app.say(0, pair[0]); app.locked();
    assert.equal(app.requests[0].url, '/modulos/2/progresso/acertos/');
    await app.say(1, pair[1]);
    assert.equal(app.done(0), true); assert.equal(app.done(1), true);
    assert.equal(app.audio.disabled, false);
    app.next.click(); assert.deepEqual(app.navigations, [url]);
    const restored = setup(pair, { module: 2, url, saved: [41, 42], complete: true, percentual: 33 });
    assert.equal(restored.next.disabled, false);
    assert.equal(restored.requests.length, 0);
  });
}

for (const [index, pair] of [['cat', 'cake'], ['cap', 'cape'], ['tap', 'tape'], ['mad', 'made']].entries()) {
  test(`Descoberta ${index + 1}: ambas obrigatórias e destino preservado`, async () => {
    const url = index === 3 ? '/modulos/1/resumo/' : `/modulos/1/descoberta/${index + 2}/`;
    const app = setup(pair, { url });
    app.locked();
    app.audio.click(); app.locked();
    await app.say(0, pair[0]); app.locked();
    assert.equal(app.done(0), true); assert.equal(app.done(1), false);
    await app.say(1, 'wrong'); app.locked();
    assert.equal(app.done(0), true); assert.equal(app.done(1), false);
    await app.say(1, pair[1]);
    assert.equal(app.next.disabled, false);
    assert.equal(app.done(0), true); assert.equal(app.done(1), true);
    app.next.click(); assert.deepEqual(app.navigations, [url]);
    assert.match(app.status.textContent, new RegExp(pair.join(' e '), 'i'));
  });
}

test('CAT errado + CAKE correto continua bloqueado; repetir CAT libera', async () => {
  const app = setup(); await app.say(0, 'dog'); await app.say(1, 'cake'); app.locked();
  assert.equal(app.done(0), false); assert.equal(app.done(1), true);
  await app.say(0, ' CAT! '); assert.equal(app.next.disabled, false);
});

for (const error of ['no-speech', 'not-allowed', 'service-not-allowed', 'network', 'audio-capture', 'aborted']) {
  test(`${error}: bloqueia, preserva a outra palavra e ignora resultado tardio`, async () => {
    const app = setup(); await app.say(0, 'cat');
    const r = app.start(1); r.error(error); r.result('cake');
    app.locked(); assert.equal(app.done(0), true); assert.equal(app.done(1), false);
    if (!error.includes('allowed')) { await app.say(1, 'cake'); assert.equal(app.next.disabled, false); }
  });
}

for (const text of ['', '   ', '...', 'cat cake', 'dog', null]) {
  test(`resultado inválido ${JSON.stringify(text)} não conclui`, async () => {
    const app = setup(); await app.say(0, text); app.locked(); assert.equal(app.done(0), false);
  });
}

test('silêncio, resultado parcial e fim sem resultado não concluem', async () => {
  const app = setup(); await app.start(0).end(); app.locked();
  const r = app.start(0); r.result('cat', false); await r.end();
  app.locked(); assert.equal(app.done(0), false);
  await app.say(0, 'cat'); assert.equal(app.done(0), true);
});

test('resultado final aguarda fim normal; erro posterior invalida a tentativa', async () => {
  const app = setup(); await app.say(0, 'cat');
  const r = app.start(1); r.result('cake'); app.locked();
  r.error('aborted'); app.locked(); assert.equal(app.done(1), false);
});

test('timeout e saída da página cancelam sem aceitar eventos tardios', async () => {
  for (const exit of [false, true]) {
    const app = setup(); await app.say(0, 'cat');
    const r = app.start(1); r.result('cake');
    if (exit) app.window.pagehide(); else [...app.timers.values()][0]();
    r.result('cake'); await r.end(); app.locked();
    assert.equal(app.done(0), true); assert.equal(app.done(1), false);
    await app.say(1, 'cake'); assert.equal(app.next.disabled, false);
  }
});

for (const options of [{ unsupported: true }, { secure: false }, { constructorError: true }, { startError: new Error('failed') }, { startError: { name: 'NotAllowedError' } }]) {
  test(`indisponibilidade ${JSON.stringify(options)} bloqueia`, async () => {
    const app = setup(undefined, options); app.start(0); app.locked();
    assert.equal(app.done(0), false); assert.equal(app.done(1), false);
  });
}

test('API prefixada funciona; cliques durante reconhecimento não iniciam outra sessão', async () => {
  const app = setup(undefined, { webkit: true });
  const r = app.start(0); app.roots[1].children.speak.dispatch();
  assert.equal(app.instances.length, 1); app.locked();
  r.result('cat'); await r.end(); await app.say(1, 'cake'); assert.equal(app.next.disabled, false);
});

test('configuração incompleta nunca libera avanço', async () => {
  const app = setup(['cat']); app.start(0); app.locked();
  assert.equal(app.requests.length, 0);
});

test('acerto local envia IDs reais, transcrição original e CSRF, sem autoridades do cliente', async () => {
  const app = setup();
  await app.say(0, ' CAT! ');
  assert.equal(app.requests.length, 1);
  const request = app.requests[0];
  assert.equal(request.url, '/modulos/1/progresso/acertos/');
  assert.equal(request.method, 'POST');
  assert.equal(request.credentials, 'same-origin');
  assert.equal(request.headers['X-CSRFToken'], 'token-csrf-teste');
  assert.equal(request.headers['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(request.body), { comparacao_id: 17, palavra_id: 41, transcricao: ' CAT! ' });
  assert.equal(app.done(0), true);
  app.locked();
});

test('aguarda o backend e impede cliques, resultados e onend duplicados durante o POST', async () => {
  let release;
  const app = setup(undefined, { fetch: (_, request, respond) => new Promise(resolve => {
    release = () => resolve(respond(request));
  }) });
  const r = app.start(0); r.result('cat');
  const pending = r.end();
  assert.equal(app.done(0), false); app.locked();
  assert.match(app.roots[0].children['speech-message'].textContent, /Salvando/);
  app.roots[0].children.speak.dispatch(); app.roots[1].children.speak.dispatch();
  r.result('cat'); await r.end();
  assert.equal(app.requests.length, 1);
  assert.equal(app.instances.length, 1);
  release(); await pending;
  assert.equal(app.done(0), true); app.locked();
});

test('segunda confirmação do servidor libera Próxima e usa percentual retornado', async () => {
  const app = setup();
  await app.say(0, 'cat'); app.locked();
  assert.equal(app.state.dataset.percentual, '0');
  await app.say(1, 'cake');
  assert.equal(app.state.dataset.percentual, '25');
  assert.equal(app.state.dataset.concluida, 'true');
  assert.equal(app.next.disabled, false);
});

test('percentual vem do backend mesmo ao revisitar uma descoberta anterior', async () => {
  const app = setup(undefined, { fetch: async () => ({ ok: true, json: async () => ({
    modulo: 1, palavras_acertadas: [41], comparacoes_concluidas: [], percentual: 50,
  }) }) });
  await app.say(0, 'cat');
  assert.equal(app.state.dataset.percentual, '50'); app.locked();
});

test('erro de rede preserva acerto anterior e permite tentar novamente', async () => {
  let fail = true;
  const app = setup(undefined, { saved: [41], fetch: async (_, request, respond) => {
    if (fail) throw new Error('network');
    return respond(request);
  } });
  await app.say(1, 'cake');
  assert.equal(app.done(0), true); assert.equal(app.done(1), false); app.locked();
  assert.match(app.roots[1].children['speech-message'].textContent, /Não foi possível salvar/);
  assert.equal(app.roots[1].children.speak.disabled, false);
  fail = false; await app.say(1, 'cake');
  assert.equal(app.next.disabled, false);
});

for (const code of [400, 403, 409, 500, 503]) {
  test(`backend HTTP ${code} não confirma acerto nem libera Próxima`, async () => {
    const app = setup(undefined, { fetch: async () => ({ ok: false, status: code }) });
    await app.say(0, 'cat');
    assert.equal(app.done(0), false); app.locked();
    assert.equal(app.roots[0].children.speak.disabled, false);
  });
}

for (const invalid of [null, {}, { modulo: 1, percentual: 100, palavras_acertadas: [41, 42], comparacoes_concluidas: [] },
  { modulo: 2, percentual: 25, palavras_acertadas: [41, 42], comparacoes_concluidas: [17] },
  { modulo: 1, percentual: 0, palavras_acertadas: [], comparacoes_concluidas: [] }]) {
  test(`resposta inválida não confirma acerto: ${JSON.stringify(invalid)}`, async () => {
    const app = setup(undefined, { fetch: async () => ({ ok: true, json: async () => invalid }) });
    await app.say(0, 'cat'); assert.equal(app.done(0), false); app.locked();
  });
}

test('HTML de sessão expirada ou JSON malformado não confirma acerto', async () => {
  const app = setup(undefined, { fetch: async () => ({ ok: true, json: async () => { throw new SyntaxError('HTML'); } }) });
  await app.say(0, 'cat'); assert.equal(app.done(0), false); app.locked();
});

test('timeout do POST permite nova tentativa e ignora confirmação tardia', async () => {
  let release;
  const app = setup(undefined, { fetch: (_, request, respond) => new Promise(resolve => {
    release = () => resolve(respond(request));
  }) });
  const pending = app.say(0, 'cat');
  [...app.timers.values()][0]();
  await pending;
  assert.equal(app.requests[0].signal.aborted, true);
  assert.equal(app.done(0), false); app.locked();
  assert.equal(app.roots[0].children.speak.disabled, false);
  release(); await new Promise(resolve => setImmediate(resolve));
  assert.equal(app.done(0), false); app.locked();
});

test('sair durante o POST cancela a espera e ignora resposta tardia', async () => {
  let release;
  const app = setup(undefined, { fetch: (_, request, respond) => new Promise(resolve => {
    release = () => resolve(respond(request));
  }) });
  const pending = app.say(0, 'cat');
  app.window.pagehide(); release(); await pending;
  assert.equal(app.requests[0].signal.aborted, true);
  assert.equal(app.done(0), false); app.locked();
});

test('uma palavra persistida é restaurada sem POST e mantém Próxima bloqueado', () => {
  const app = setup(undefined, { saved: [41] });
  assert.equal(app.done(0), true); assert.equal(app.done(1), false);
  assert.equal(app.roots[0].dataset.state, 'correct');
  app.start(0); assert.equal(app.instances.length, 0);
  assert.equal(app.requests.length, 0); app.locked();
});

test('duas palavras persistidas restauram Próxima sem exigir microfone novamente', () => {
  const app = setup(undefined, { saved: [41, 42], complete: true, percentual: 25, unsupported: true });
  assert.equal(app.done(0), true); assert.equal(app.done(1), true);
  assert.equal(app.next.disabled, false);
  assert.equal(app.state.dataset.percentual, '25');
  app.next.click(); assert.equal(app.navigations.length, 1);
  assert.equal(app.requests.length, 0);
});

test('transcrição incorreta não envia POST', async () => {
  const app = setup(); await app.say(0, 'dog');
  assert.equal(app.requests.length, 0); app.locked();
});

test('token CSRF ausente bloqueia envio', () => {
  const app = setup(undefined, { noCsrf: true });
  app.start(0); assert.equal(app.requests.length, 0); app.locked();
});

test('retorno pelo histórico recarrega o estado do usuário atual', () => {
  const app = setup();
  app.window.pageshow({ persisted: false }); assert.deepEqual(app.navigations, []);
  app.window.pageshow({ persisted: true }); assert.deepEqual(app.navigations, ['reload']);
});

test('Descoberta 4 usa os 100% retornados sem solicitar conclusão formal', async () => {
  const app = setup(['mad', 'made'], { url: '/modulos/1/resumo/', fetch: async (_, request, respond) => {
    const data = await respond(request).json();
    data.percentual = data.comparacoes_concluidas.length ? 100 : 75;
    return { ok: true, json: async () => data };
  } });
  await app.say(0, 'mad'); await app.say(1, 'made');
  assert.equal(app.state.dataset.percentual, '100');
  app.next.click(); assert.deepEqual(app.navigations, ['/modulos/1/resumo/']);
  assert.equal(app.requests.length, 2);
  assert.ok(app.requests.every(request => request.url.endsWith('/acertos/')));
});

for (const transcript of ['Matt', ' MATT! ']) {
  test(`MAD apresenta mad ao aceitar ${transcript}`, async () => {
    const app = setup(['mad', 'made']);
    await app.say(0, transcript);
    assert.equal(app.done(0), true);
    assert.equal(app.roots[0].children['speech-message'].textContent, 'Eu entendi: mad');
    assert.equal(JSON.parse(app.requests[0].body).transcricao, transcript);
  });
}
test('MADE não esconde Matt quando a resposta é incorreta', async () => {
  const app = setup(['mad', 'made']);
  await app.say(1, 'Matt');
  assert.equal(app.done(1), false);
  assert.equal(app.requests.length, 0);
  assert.equal(app.roots[1].children['speech-message'].textContent, 'Eu entendi: Matt');
});

for (const transcript of ['cats', 'Cats', ' CATS! ']) {
  test(`CAT apresenta cat ao aceitar ${transcript}`, async () => {
    const app = setup(['cat', 'cake']);
    await app.say(0, transcript);
    assert.equal(app.done(0), true);
    assert.equal(app.roots[0].children['speech-message'].textContent, 'Eu entendi: cat');
    assert.equal(JSON.parse(app.requests[0].body).transcricao, transcript);
  });
}
test('CAKE não esconde cats quando a resposta é incorreta', async () => {
  const app = setup(['cat', 'cake']);
  await app.say(1, 'cats');
  assert.equal(app.done(1), false);
  assert.equal(app.requests.length, 0);
  assert.equal(app.roots[1].children['speech-message'].textContent, 'Eu entendi: cats');
});

for (const [index, pair] of [['hop', 'hope'], ['not', 'note'], ['rob', 'robe']].entries()) {
  test(`Módulo 3 par ${index + 1}: erro, dois acertos, áudio disponível e avanço`, async () => {
    const url = index === 2 ? '/modulos/3/resumo/' : `/modulos/3/descobertas/${index + 2}/`;
    const app = setup(pair, { module: 3, url });
    await app.say(0, 'wrong');
    assert.equal(app.requests.length, 0); app.locked();
    await app.say(0, pair[0]); app.locked();
    assert.equal(app.requests[0].url, '/modulos/3/progresso/acertos/');
    await app.say(1, pair[1]);
    assert.equal(app.done(0), true); assert.equal(app.done(1), true);
    assert.equal(app.audio.disabled, false);
    app.next.click(); assert.deepEqual(app.navigations, [url]);
    const restored = setup(pair, { module: 3, url, saved: [41, 42], complete: true, percentual: 33 });
    assert.equal(restored.next.disabled, false);
    assert.equal(restored.requests.length, 0);
  });
}


for (const error of ['no-speech', 'not-allowed', 'service-not-allowed', 'audio-capture', 'network']) {
  test(`Módulo 3: ${error} preserva acerto individual e bloqueio`, async () => {
    const app = setup(['hop', 'hope'], { module: 3 });
    await app.say(0, ' HOP! ');
    app.start(1).error(error);
    assert.equal(app.done(0), true);
    assert.equal(app.done(1), false);
    app.locked();
    assert.equal(app.requests.length, 1);
  });
}
for (const options of [{unsupported: true}, {secure: false}]) {
  test(`Módulo 3: ambiente indisponível ${JSON.stringify(options)}`, () => {
    const app = setup(['hop', 'hope'], {module: 3, ...options});
    app.locked();
    assert.equal(app.roots[0].children.speak.disabled, true);
    assert.equal(app.requests.length, 0);
  });
}
test('Módulo 3: silêncio e fala parcial não salvam nem liberam avanço', async () => {
  const app = setup(['hop', 'hope'], {module: 3});
  const r = app.start(0); r.result('hop', false); await r.end();
  app.locked(); assert.equal(app.requests.length, 0);
  await app.say(0, '...'); app.locked(); assert.equal(app.requests.length, 0);
});

for (const [index, pair] of [['cub', 'cube'], ['tub', 'tube'], ['cut', 'cute']].entries()) {
  test(`Módulo 4 par ${index + 1}: exige os dois acertos e avança`, async () => {
    const url = index === 2 ? '/modulos/4/resumo/' : `/modulos/4/descobertas/${index + 2}/`;
    const app = setup(pair, { module: 4, url });
    await app.say(0, 'wrong');
    assert.equal(app.requests.length, 0);
    app.locked();
    await app.say(0, pair[0]);
    assert.equal(app.next.disabled, true);
    await app.say(1, pair[1]);
    assert.equal(app.next.disabled, false);
    app.next.click();
    assert.deepEqual(app.navigations, [url]);
  });
}

for (const [index, pair] of [['ship', 'fish'], ['shoe', 'sheep'], ['shop', 'shell']].entries()) {
  test(`Módulo 5 par ${index + 1}: erro, dois acertos independentes e avanço`, async () => {
    const url = index === 2 ? '/modulos/5/resumo/' : `/modulos/5/descobertas/${index + 2}/`;
    const app = setup(pair, { module: 5, url });
    app.locked();
    await app.say(0, pair[1]);
    assert.equal(app.requests.length, 0); app.locked();
    await app.say(0, `  ${pair[0].toUpperCase()}!... `);
    assert.equal(app.done(0), true); assert.equal(app.done(1), false); app.locked();
    assert.equal(app.requests[0].url, '/modulos/5/progresso/acertos/');
    const restored = setup(pair, {module: 5, saved: [41], complete: false});
    restored.locked(); assert.equal(restored.done(0), true); assert.equal(restored.done(1), false);
    await app.say(1, pair[1]);
    assert.equal(app.next.disabled, false); assert.equal(app.audio.disabled, false);
    app.next.click(); assert.deepEqual(app.navigations, [url]);
    const completed = setup(pair, {module: 5, saved: [41, 42], complete: true});
    assert.equal(completed.next.disabled, false); assert.equal(completed.requests.length, 0);
  });
}

for (const error of ['no-speech', 'not-allowed', 'service-not-allowed', 'audio-capture', 'network']) {
  test(`Módulo 5: ${error} mantém acerto individual e bloqueio`, async () => {
    const app = setup(['ship', 'fish'], {module: 5});
    await app.say(0, 'ship');
    const r = app.start(1); r.error(error); r.result('fish');
    assert.equal(app.done(0), true); assert.equal(app.done(1), false);
    app.locked(); assert.equal(app.requests.length, 1);
  });
}
for (const options of [{unsupported: true}, {secure: false}]) {
  test(`Módulo 5: ambiente indisponível ${JSON.stringify(options)}`, () => {
    const app = setup(['ship', 'fish'], {module: 5, ...options});
    app.locked(); assert.equal(app.roots[0].children.speak.disabled, true);
    assert.equal(app.requests.length, 0);
  });
}
test('Módulo 5: silêncio e fala parcial não contam como acerto', async () => {
  const app = setup(['ship', 'fish'], {module: 5});
  const r = app.start(0); r.result('ship', false); await r.end();
  await app.say(0, '...'); app.locked(); assert.equal(app.requests.length, 0);
});
test('Módulo 5: alternativa correta usa seleção compartilhada', async () => {
  const app = setup(['ship', 'fish'], {module: 5});
  const r = app.start(0);
  const result = [{transcript: 'sheep'}, {transcript: ' SHIP! '}]; result.isFinal = true;
  r.onresult({resultIndex: 0, results: [result]}); await r.end();
  assert.equal(app.done(0), true); app.locked();
  assert.equal(JSON.parse(app.requests[0].body).transcricao, ' SHIP! ');
});
