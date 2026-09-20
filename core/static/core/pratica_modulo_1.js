(() => {
  'use strict';
  const data = document.getElementById('practice-words');
  if (!data) return;
  const words = JSON.parse(data.textContent);
  if (!words.length) return;
  const byId = (id) => document.getElementById(id);
  const card = byId('practice');
  const mic = byId('microphone');
  const listen = byId('listen');
  const audio = byId('word-audio');
  const retry = byId('retry');
  const next = byId('next');
  const status = byId('mic-status');
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const { normalize, select } = window.SayItPronuncia;
  let index = 0;
  let active = null;
  let blocked = false;
  let correct = false;
  let watchdog;

  function state(value, message = '') {
    mic.dataset.state = value;
    mic.setAttribute('aria-busy', String(value === 'listening' || value === 'processing'));
    byId('mic-label').textContent = {
      idle: 'Falar · microfone parado',
      listening: 'Estou ouvindo...',
      processing: 'Processando...',
      blocked: 'Microfone indisponível',
    }[value];
    status.textContent = message;
    controls();
  }

  function controls() {
    mic.disabled = blocked || !!active || correct;
    listen.disabled = !!active || !words[index].audio;
    retry.disabled = blocked || !!active;
    next.disabled = blocked || !!active;
  }

  function feedback(result, title, text) {
    byId('feedback').dataset.result = result;
    byId('feedback-title').textContent = title;
    byId('feedback-text').textContent = text;
    correct = result === 'correct';
    next.hidden = !correct;
    retry.hidden = correct || blocked;
    controls();
  }

  function block(message) {
    blocked = true;
    feedback('', '', '');
    next.hidden = true;
    state('blocked', message);
  }

  function showWord(focus = false) {
    correct = false;
    const word = words[index];
    byId('word').textContent = word.palavra;
    byId('progress').textContent = `Palavra ${index + 1} de ${words.length}`;
    byId('word-image').src = word.imagem;
    byId('word-image').alt = word.traducao;
    audio.pause();
    if (word.audio) audio.src = word.audio;
    else audio.removeAttribute('src');
    listen.setAttribute('aria-label', `Ouvir ${word.palavra}`);
    mic.setAttribute('aria-label', `Falar ${word.palavra} usando o microfone`);
    feedback('', '', '');
    retry.hidden = true;
    state('idle');
    if (focus) byId('word').focus();
  }

  function start() {
    if (blocked || active || correct) return;
    audio.pause();
    feedback('', '', '');
    retry.hidden = true;
    let recognition;
    let settled = false;
    function silence() {
      settled = true;
      feedback('unheard', '', 'Não consegui ouvir. Tente novamente.');
    }
    function finish() {
      if (active !== recognition) return;
      clearTimeout(watchdog);
      active = null;
      if (!settled && !blocked) silence();
      state(blocked ? 'blocked' : 'idle', blocked ? status.textContent : '');
      if (!blocked) (correct ? next : retry).focus();
    }
    try {
      recognition = new Recognition();
      active = recognition;
      recognition.lang = 'en-US';
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.maxAlternatives = 3;
      recognition.onstart = () => {
        if (active === recognition && !settled) state('listening', 'Estou ouvindo...');
      };
      recognition.onspeechend = () => {
        if (active !== recognition || settled) return;
        state('processing', 'Processando...');
        recognition.stop();
      };
      recognition.onaudioend = () => {
        if (active === recognition && !settled) state('processing', 'Processando...');
      };
      recognition.onresult = (event) => {
        if (active !== recognition || settled) return;
        const result = event.results?.[event.resultIndex ?? 0];
        if (!result?.isFinal) return;
        const { heard, accepted } = select(result, words[index].palavra);
        const text = normalize(heard);
        settled = true;
        if (accepted) feedback('correct', 'Great job!', `Eu entendi: ${heard}`);
        else if (!text) silence();
        else feedback('incorrect', 'Try again!', `Eu entendi: ${heard}`);
      };
      recognition.onnomatch = () => {
        if (active === recognition && !settled) silence();
      };
      recognition.onerror = (event) => {
        if (active !== recognition) return;
        settled = true;
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          block('O acesso ao microfone foi bloqueado. Peça ajuda a um adulto: abra as permissões deste site no navegador, permita o microfone e recarregue a página. Se continuar bloqueado, confira também as permissões de microfone do sistema.');
        } else if (event.error === 'no-speech') silence();
        else feedback('unavailable', '', event.error === 'audio-capture'
          ? 'Não encontrei um microfone. Conecte um microfone e tente novamente.'
          : 'Não foi possível reconhecer agora. Confira sua conexão e tente novamente.');
        finish();
      };
      recognition.onend = finish;
      state('processing', 'Preparando o microfone. Permita o acesso se o navegador pedir.');
      recognition.start();
      watchdog = setTimeout(() => {
        if (active !== recognition) return;
        finish();
        recognition.abort();
      }, 20000);
    } catch (error) {
      settled = true;
      if (error.name === 'NotAllowedError' || error.name === 'SecurityError') {
        block('Permita o microfone nas configurações deste site no navegador e recarregue a página. Peça ajuda a um adulto.');
      } else feedback('unavailable', '', 'Não foi possível iniciar o microfone. Tente novamente.');
      if (recognition) finish();
      else { active = null; controls(); }
    }
  }

  listen.addEventListener('click', async () => {
    if (active) return;
    status.textContent = '';
    try { audio.currentTime = 0; await audio.play(); }
    catch (error) {
      if (error.name !== 'AbortError' && !active) status.textContent = 'Não foi possível ouvir agora. Tente novamente.';
    }
  });
  mic.addEventListener('click', start);
  retry.addEventListener('click', start);
  next.addEventListener('click', () => {
    if (!correct || active || blocked) return;
    audio.pause();
    if (index === words.length - 1) {
      card.hidden = true;
      byId('complete').hidden = false;
      byId('complete').querySelector('h2').focus();
    } else { index += 1; showWord(true); }
  });
  window.addEventListener('pagehide', () => {
    audio.pause();
    clearTimeout(watchdog);
    const recognition = active;
    active = null;
    if (recognition) recognition.abort();
    if (!blocked) state('idle');
  });
  card.hidden = false;
  showWord();
  if (!Recognition) block('Este navegador não oferece reconhecimento de voz. Abra a prática em um navegador compatível com SpeechRecognition para usar o microfone.');
  else if (!window.isSecureContext) block('O microfone precisa de uma conexão segura. Abra este site por HTTPS (ou localhost durante o desenvolvimento).');
})();
