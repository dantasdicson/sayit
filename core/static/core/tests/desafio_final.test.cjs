const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {createAssembly} = require('../desafio_final.js');
const source = fs.readFileSync(path.join(__dirname, '../pronuncia.js'), 'utf8') + '\n'
  + fs.readFileSync(path.join(__dirname, '../desafio_final.js'), 'utf8');

class Element {
  constructor() { this.disabled = false; this.hidden = false; this.textContent = ''; this.children = []; this.dataset = {}; this.handlers = {}; }
  addEventListener(name, fn) { this.handlers[name] = fn; }
  click() { if (!this.disabled) return this.handlers.click?.(); }
  setAttribute(name, value) { this[name] = value; }
  appendChild(child) { this.children.push(child); }
  replaceChildren() { this.children = []; }
  querySelectorAll() { return this.children; }
  focus() {}
}
function setup(options = {}) {
  const ids = ['desafio-config','sentence-tray','assembly-check','assembly-reset','challenge-speak',
    'challenge-next','challenge-status','retry-save','challenge-feedback','assembly-status',
    'challenge-score','challenge-stars','feedback-title','feedback-message','feedback-count',
    'feedback-correct','feedback-missing','feedback-important','feedback-extra','best-score','challenge-history'];
  const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
  const words = ['I','like','cake'];
  elements['desafio-config'].textContent = JSON.stringify({palavras: words, numero:1, montagemUrl:'/montar',
    avaliacaoUrl:'/avaliar', proximaUrl:'/desafio/2', aprovado:false, minimo:70, melhor:0});
  const bank = words.map((_, i) => { const b = new Element(); b.dataset.token = String(i); return b; });
  const instances = [], requests = [], navigations = [], timers = new Map();
  let nonce = 0, saves = 0;
  class Recognition {
    constructor() { instances.push(this); }
    start() { if (options.startError) throw options.startError; this.onstart?.(); }
    stop() {}
    abort() { this.onerror?.({error:'aborted'}); this.onend?.(); }
    result(text, final = true) { const r = [{transcript:text}]; r.isFinal = final; this.onresult({results:[r],resultIndex:0}); }
    end() { return this.onend(); }
  }
  const window = {isSecureContext: options.secure !== false, location:{assign:url=>navigations.push(url)},
    addEventListener(name, fn) { this[name] = fn; }};
  if (!options.unsupported) window[options.webkit ? 'webkitSpeechRecognition' : 'SpeechRecognition'] = Recognition;
  const fetch = async (url, init) => {
    const payload = JSON.parse(init.body); requests.push({url, payload});
    if (url === '/montar') {
      if (JSON.stringify(payload.palavras) !== JSON.stringify(words)) return {ok:false, json:async()=>({mensagem:'Confira a ordem.'})};
      return {ok:true, json:async()=>({token:'token-' + (++nonce)})};
    }
    if (options.saveFailure && saves++ === 0) throw new Error('Sem conexão');
    const nota = payload.transcricao === 'I like cake' ? 100 : payload.transcricao === 'I cake' ? 70 : payload.transcricao ? 50 : 0;
    return {ok:true, json:async()=>({liberado:nota>=70, melhor:nota, avaliacao:{
      nota, estrelas:nota>=90?5:nota>=70?3:1, titulo:'Continue!', mensagem:'Tente de novo',
      reconhecidas:nota===100?3:1,total:3,corretas:['cake'],faltantes:nota===100?[]:['like'],
      importantes_faltantes:[],extras:[],
    }})};
  };
  vm.runInNewContext(source, {window, fetch, AbortController,
    document: {getElementById:id=>elements[id], querySelector:()=>({value:'csrf'}),
      querySelectorAll:selector=>selector==='[data-token]'?bank:[], createElement:()=>new Element()},
    setTimeout(fn) { const id=timers.size+1; timers.set(id,fn); return id; }, clearTimeout(id) {timers.delete(id);},
  });
  const assemble = async (order=[0,1,2]) => { for (const i of order) bank[i].click(); await elements['assembly-check'].click(); };
  const start = async () => { await elements['challenge-speak'].click(); return instances.at(-1); };
  const say = async text => { const r=await start(); r.result(text); await r.end(); };
  return {elements, bank, instances, requests, navigations, timers, window, assemble, start, say};
}
test('montagem usa índices e preserva duas ocorrências de the', () => {
  const a=createAssembly(['The','cat','on','the']);
  for (const i of [0,1,2,3,3,99,-1]) a.add(i);
  assert.deepEqual(a.words(), ['The','cat','on','the']); assert.equal(a.full(),true);
  a.remove(0); assert.deepEqual(a.words(),['cat','on','the']); a.reset(); assert.equal(a.full(),false);
});
test('microfone e próximo bloqueados antes de montagem', () => {
  const a=setup(); a.elements['challenge-speak'].click(); a.elements['challenge-next'].click();
  assert.equal(a.instances.length,0); assert.equal(a.requests.length,0); assert.equal(a.navigations.length,0);
});
test('ordem errada mantém microfone bloqueado; corrigir libera', async () => {
  const a=setup(); await a.assemble([2,0,1]); assert.equal(a.elements['challenge-speak'].disabled,true);
  a.elements['assembly-reset'].click(); await a.assemble(); assert.equal(a.elements['challenge-speak'].disabled,false);
});
test('microfone em inglês compartilha configuração existente', async () => {
  const a=setup({webkit:true}); await a.assemble(); const r=await a.start();
  assert.equal(r.lang,'en-US'); assert.equal(r.interimResults,false); assert.equal(r.continuous,false);
  assert.equal(a.elements['challenge-next'].disabled,true);
});
for (const [text, passed] of [['cake',false],['I cake',true],['I like cake',true],['',false]]) {
  test('avaliação da fala e avanço: '+JSON.stringify(text), async () => {
    const a=setup(); await a.assemble(); await a.say(text);
    assert.equal(a.elements['challenge-next'].disabled,!passed);
    assert.equal(a.elements['challenge-history'].children.length,1);
    a.elements['challenge-next'].click();
    assert.equal(a.navigations.length,passed?1:0);
  });
}
test('novas tentativas mantêm histórico visual', async () => {
  const a=setup(); await a.assemble(); await a.say('cake'); await a.say('I like cake');
  assert.equal(a.elements['challenge-history'].children.length,2);
  const tokens=a.requests.filter(r=>r.url==='/avaliar').map(r=>r.payload.token);
  assert.notEqual(tokens[0],tokens[1]);
});
for (const options of [{unsupported:true},{secure:false}]) {
  test('sem suporte ou HTTPS não libera fala '+JSON.stringify(options), async () => {
    const a=setup(options); await a.assemble(); assert.equal(a.elements['challenge-speak'].disabled,true);
    assert.equal(a.instances.length,0); assert.match(a.elements['challenge-status'].textContent,/navegador|HTTPS/);
  });
}
for (const error of ['not-allowed','service-not-allowed','audio-capture','network']) {
  test('erro de microfone não avalia nem avança: '+error, async () => {
    const a=setup(); await a.assemble(); const r=await a.start(); r.onerror({error});
    r.result('I like cake'); await r.end();
    assert.equal(a.requests.filter(r=>r.url==='/avaliar').length,0);
    assert.equal(a.elements['challenge-next'].disabled,true);
  });
}
test('sem fala ou apenas resultado parcial registra nota zero', async () => {
  const a=setup(); await a.assemble(); const r=await a.start(); r.result('I like cake',false); await r.end();
  assert.equal(a.requests.at(-1).payload.transcricao,'');
  assert.equal(a.elements['challenge-score'].textContent,'0 / 100');
});
test('no-speech ignora resultado tardio', async () => {
  const a=setup(); await a.assemble(); const r=await a.start(); r.onerror({error:'no-speech'});
  r.result('I like cake'); await new Promise(resolve=>setImmediate(resolve));
  assert.equal(a.requests.at(-1).payload.transcricao,'');
});
test('falha de rede preserva envio e usa mesmo ticket ao tentar salvar', async () => {
  const a=setup({saveFailure:true}); await a.assemble(); await a.say('I like cake');
  assert.equal(a.elements['challenge-next'].disabled,true);
  assert.equal(a.elements['retry-save'].hidden,false);
  await a.elements['retry-save'].click();
  const attempts=a.requests.filter(r=>r.url==='/avaliar');
  assert.equal(attempts[0].payload.token,attempts[1].payload.token);
  assert.equal(a.elements['challenge-history'].children.length,1);
  assert.equal(a.elements['challenge-next'].disabled,false);
});
test('sair da página aborta captura e impede envio tardio', async () => {
  const a=setup(); await a.assemble(); const r=await a.start(); a.window.pagehide();
  r.result('I like cake'); await r.end();
  assert.equal(a.requests.filter(r=>r.url==='/avaliar').length,0);
});
test('clique duplo não abre dois microfones', async () => {
  const a=setup(); await a.assemble(); await a.start(); await a.start();
  assert.equal(a.instances.length,1);
});
