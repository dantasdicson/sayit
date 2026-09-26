(() => {
  'use strict';
  // O estado de montagem usa índices: a palavra "the" aparece duas vezes.
  function createAssembly(words) {
    let order = [];
    return {
      add(id) { if (Number.isInteger(id) && id >= 0 && id < words.length && !order.includes(id)) order.push(id); },
      remove(id) { order = order.filter(value => value !== id); },
      reset() { order = []; },
      ids() { return [...order]; },
      words() { return order.map(id => words[id]); },
      full() { return order.length === words.length; },
    };
  }
  if (typeof module !== 'undefined') module.exports = { createAssembly };
  if (typeof document === 'undefined') return;
  const data = document.getElementById('desafio-config');
  if (!data) return;
  const config = JSON.parse(data.textContent);
  const byId = id => document.getElementById(id);
  const assembly = createAssembly(config.palavras);
  const bank = [...document.querySelectorAll('[data-token]')];
  const tray = byId('sentence-tray'), check = byId('assembly-check'), reset = byId('assembly-reset');
  const speak = byId('challenge-speak'), next = byId('challenge-next'), status = byId('challenge-status');
  const retry = byId('retry-save'), feedback = byId('challenge-feedback');
  const players = [...document.querySelectorAll('audio')];
  const audioButtons = [...document.querySelectorAll('[data-audio]')];
  const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
  const supported = !!(window.SpeechRecognition || window.webkitSpeechRecognition) && window.isSecureContext;
  let verified = false, busy = false, passed = config.aprovado, active = null, token = '';
  let pending = null, leaving = false, controller = null;
  const permissionMessage = 'O microfone é necessário. Permita o acesso nas configurações do navegador e tente novamente.';

  function controls() {
    bank.forEach(button => { button.disabled = busy || !!pending || assembly.ids().includes(Number(button.dataset.token)); });
    tray.querySelectorAll('button').forEach(button => { button.disabled = busy || !!pending; });
    check.disabled = busy || !!pending || !assembly.full();
    reset.disabled = busy || !!pending || !assembly.ids().length;
    speak.disabled = !supported || !verified || busy || !!pending;
    speak.setAttribute('aria-busy', String(busy));
    next.disabled = !passed || busy || !!pending;
    audioButtons.forEach(button => { button.disabled = busy; });
    retry.hidden = !pending || busy;
  }
  function redraw() {
    verified = false; token = '';
    tray.replaceChildren();
    for (const id of assembly.ids()) {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'word-token'; button.lang = 'en';
      button.textContent = config.palavras[id];
      button.setAttribute('aria-label', 'Remover ' + config.palavras[id]);
      button.addEventListener('click', () => { if (!busy && !pending) { assembly.remove(id); redraw(); } });
      tray.appendChild(button);
    }
    byId('assembly-status').textContent = 'Monte a frase e toque em Conferir frase.';
    controls();
  }
  async function post(url, payload) {
    controller = new AbortController();
    const timer = setTimeout(() => controller?.abort(), 15000);
    try {
      const response = await fetch(url, { method: 'POST', credentials: 'same-origin', mode: 'same-origin',
        redirect: 'error', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
        body: JSON.stringify(payload), signal: controller.signal });
      if (response.redirected) throw new Error('Entre novamente na sua conta.');
      const result = await response.json();
      if (!response.ok) {
        const error = new Error(result.mensagem || 'Não foi possível salvar agora.');
        error.code = result.erro; throw error;
      }
      return result;
    } finally { clearTimeout(timer); controller = null; }
  }
  async function verify() {
    const result = await post(config.montagemUrl, {palavras: assembly.words()});
    if (typeof result.token !== 'string' || !result.token) throw new Error('Resposta inválida. Tente novamente.');
    token = result.token;
    verified = true;
    byId('assembly-status').textContent = 'Muito bem! Agora fale a frase usando o microfone.';
  }
  function show(result, transcript) {
    const a = result.avaliacao;
    if (!a || !Number.isInteger(a.nota) || a.nota < 0 || a.nota > 100
      || typeof result.liberado !== 'boolean' || !Array.isArray(a.faltantes)) throw new Error('Resposta inválida.');
    passed = result.liberado;
    byId('challenge-score').textContent = a.nota + ' / 100';
    byId('challenge-stars').textContent = '★'.repeat(a.estrelas) + '☆'.repeat(5 - a.estrelas);
    byId('challenge-stars').setAttribute('aria-label', a.estrelas + ' de 5 estrelas');
    byId('feedback-title').textContent = a.titulo;
    byId('feedback-message').textContent = a.mensagem;
    byId('feedback-count').textContent = a.reconhecidas + ' de ' + a.total + ' palavras reconhecidas.';
    byId('feedback-correct').textContent = 'Reconhecidas: ' + (a.corretas.join(', ') || 'nenhuma');
    byId('feedback-missing').textContent = 'Não identificadas: ' + (a.faltantes.join(', ') || 'nenhuma');
    byId('feedback-important').textContent = 'Palavras importantes para praticar: ' + (a.importantes_faltantes.join(', ') || 'todas reconhecidas!');
    byId('feedback-extra').textContent = 'Outras palavras reconhecidas ou fora de ordem: ' + (a.extras.join(', ') || 'nenhuma');
    byId('best-score').textContent = 'Sua melhor nota: ' + result.melhor + '/100';
    const li = document.createElement('li');
    li.textContent = a.nota + '/100 · ' + a.reconhecidas + ' de ' + a.total + ' palavras. Reconhecimento: '
      + (transcript || 'nenhuma fala reconhecida') + '. Reconhecidas: ' + (a.corretas.join(', ') || 'nenhuma')
      + '. Não identificadas: ' + (a.faltantes.join(', ') || 'nenhuma') + '.';
    byId('challenge-history').appendChild(li);
    feedback.hidden = false;
    feedback.focus();
    status.textContent = passed ? 'Você já pode avançar ou tentar melhorar sua nota!'
      : 'Vamos tentar de novo? Precisamos de pelo menos ' + config.minimo + ' pontos.';
  }
  async function save() {
    if (!pending || leaving) return;
    busy = true; controls();
    status.textContent = 'Avaliando e salvando sua tentativa...';
    try {
      const result = await post(config.avaliacaoUrl, pending);
      if (leaving) return;
      show(result, pending.transcricao);
      pending = null; token = '';
    } catch (error) {
      if (!leaving) {
        status.textContent = error.message || 'Não foi possível salvar. Tente novamente.';
        if (['montagem_expirada', 'tentativa_repetida', 'etapa_bloqueada'].includes(error.code)) {
          pending = null; token = ''; verified = false;
          status.textContent += ' Confira a montagem e fale novamente.';
        }
      }
    } finally { busy = false; controls(); }
  }
  bank.forEach(button => button.addEventListener('click', () => {
    if (!busy && !pending) { assembly.add(Number(button.dataset.token)); redraw(); }
  }));
  reset.addEventListener('click', () => { if (!busy && !pending) { assembly.reset(); redraw(); } });
  check.addEventListener('click', async () => {
    if (busy || pending || !assembly.full()) return;
    busy = true; controls();
    try { await verify(); }
    catch (error) { verified = false; byId('assembly-status').textContent = error.message; }
    finally { busy = false; controls(); }
  });
  async function start() {
    if (!verified || !supported || busy || pending || leaving) return;
    busy = true; controls(); players.forEach(player => player.pause());
    try {
      // Nova tentativa ganha novo ticket. Um reenvio de rede usa o mesmo ticket.
      if (!token) await verify();
      if (leaving) return;
      const recognition = window.SayItPronuncia.createRecognition();
      const session = {recognition, transcript: '', ended: false, timer: null};
      active = session;
      const current = () => active === session && !leaving && !session.ended;
      const finish = async (error = '') => {
        if (!current()) return;
        session.ended = true; clearTimeout(session.timer); active = null;
        if (error && error !== 'no-speech') {
          status.textContent = ['not-allowed', 'service-not-allowed'].includes(error) ? permissionMessage
            : error === 'audio-capture' ? 'Não encontrei um microfone. Conecte um e tente novamente.'
            : 'Não foi possível reconhecer agora. Confira a conexão e tente novamente.';
          busy = false; controls(); return;
        }
        pending = {token, transcricao: error === 'no-speech' ? '' : session.transcript};
        await save();
      };
      recognition.onstart = () => { if (current()) status.textContent = 'Estou ouvindo... fale a frase inteira.'; };
      recognition.onspeechend = () => { if (current()) { status.textContent = 'Processando sua fala...'; recognition.stop(); } };
      recognition.onresult = event => {
        if (!current()) return;
        const result = event.results?.[event.resultIndex ?? 0];
        if (result?.isFinal && typeof result[0]?.transcript === 'string') session.transcript = result[0].transcript;
      };
      recognition.onerror = event => { if (current()) { finish(event.error || 'network'); recognition.abort(); } };
      recognition.onend = () => finish();
      session.timer = setTimeout(() => { finish('no-speech'); recognition.abort(); }, 25000);
      status.textContent = 'Preparando o microfone...';
      try { recognition.start(); }
      catch (error) { await finish(['NotAllowedError', 'SecurityError'].includes(error.name) ? 'not-allowed' : 'network'); }
    } catch (error) {
      busy = false; status.textContent = error.message || 'Não foi possível iniciar. Tente novamente.'; controls();
    }
  }
  speak.addEventListener('click', start);
  retry.addEventListener('click', () => { if (!busy) return save(); });
  next.addEventListener('click', () => { if (passed && !busy && !pending) window.location.assign(config.proximaUrl); });
  window.addEventListener('pagehide', () => {
    leaving = true; controller?.abort();
    if (active) { clearTimeout(active.timer); active.ended = true; active.recognition.abort(); active = null; }
    players.forEach(player => player.pause());
  });
  window.addEventListener('pageshow', event => { if (event.persisted) window.location.reload(); });
  if (!supported) status.textContent = window.isSecureContext
    ? 'Seu navegador não oferece reconhecimento de voz. Abra em um navegador compatível para continuar.'
    : 'O microfone precisa de HTTPS ou localhost. Abra o endereço seguro para continuar.';
  controls();
})();
