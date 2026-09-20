(() => {
  'use strict';
  const next = document.getElementById('discovery-next');
  if (!next) return;
  const status = document.getElementById('speech-status');
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const normalize = (text) => text.toLowerCase().replace(/[.,!?;:"'“”‘’…()[\]{}-]/g, '').replace(/\s+/g, ' ').trim();
  const words = [...document.querySelectorAll('[data-practice-word]')].map((root) => ({
    root, expected: normalize(root.dataset.practiceWord), done: false,
    button: root.querySelector('.speak'), label: root.querySelector('.speak-label'),
    title: root.querySelector('.speech-title'), message: root.querySelector('.speech-message'),
    complete: root.querySelector('.word-complete'),
  }));
  const audioButtons = [...document.querySelectorAll('[data-audio]')];
  const audioPlayers = [...document.querySelectorAll('audio')];
  const pair = words.map((word) => word.expected.toUpperCase()).join(' e ');
  let active = null;
  let blocked = !Recognition;
  const permissionMessage = 'O microfone é necessário para continuar. Permita o acesso ao microfone no navegador.';

  function updateControls() {
    words.forEach((word) => { word.button.disabled = blocked || !!active || word.done; });
    audioButtons.forEach((button) => { button.disabled = !!active; });
    next.disabled = blocked || !!active || words.length !== 2 || !words.every((word) => word.done);
    if (!next.disabled) status.textContent = `Você concluiu ${pair}! Pode continuar.`;
  }

  function display(word, state, title, message) {
    word.root.dataset.state = state;
    word.title.textContent = title;
    word.message.textContent = message;
    word.label.textContent = state === 'listening' ? 'Estou ouvindo...'
      : state === 'processing' ? 'Processando...'
      : state === 'correct' ? 'Concluído' : 'Falar';
    word.button.setAttribute('aria-busy', String(state === 'listening' || state === 'processing'));
    word.complete.hidden = !word.done;
  }

  function block(message) {
    blocked = true;
    status.textContent = message;
    words.filter((word) => !word.done).forEach((word) => display(word, 'error', '', message));
    updateControls();
  }

  function start(word) {
    if (blocked || active || word.done) return;
    audioPlayers.forEach((player) => player.pause());
    let recognition;
    try { recognition = new Recognition(); }
    catch (error) {
      display(word, 'error', '', 'Não foi possível iniciar o microfone. Tente novamente.');
      return;
    }
    const session = { recognition, word, settled: false, accepted: '', timer: null };
    active = session;
    const current = () => active === session;
    const unheard = () => {
      session.settled = true;
      display(word, 'waiting', '', 'Não consegui ouvir. Tente novamente.');
    };
    const finish = (cancelled = false) => {
      if (!current()) return;
      clearTimeout(session.timer);
      // Commit only after a final matching result and a normal recognition end.
      if (session.accepted && !cancelled) {
        word.done = true;
        display(word, 'correct', 'Great job!', `Você falou: ${session.accepted}`);
      }
      if (!session.settled) unheard();
      active = null;
      updateControls();
      if (!blocked) {
        const target = words.find((item) => !item.done);
        (word.done ? (target ? target.button : next) : word.button).focus();
      }
    };
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => {
      if (current() && !session.settled) display(word, 'listening', '', 'Estou ouvindo...');
    };
    recognition.onspeechend = () => {
      if (!current() || session.settled) return;
      display(word, 'processing', '', 'Processando...');
      recognition.stop();
    };
    recognition.onresult = (event) => {
      if (!current() || session.settled) return;
      const result = event.results?.[event.resultIndex ?? 0];
      if (!result?.isFinal) return;
      const transcript = result[0]?.transcript;
      const text = typeof transcript === 'string' ? normalize(transcript) : '';
      session.settled = true;
      if (!text) unheard();
      else if (text === word.expected) {
        session.accepted = text;
        display(word, 'processing', '', 'Processando...');
      } else display(word, 'retry', 'Try again!', `Eu entendi: ${text}`);
    };
    recognition.onnomatch = () => { if (current() && !session.settled) unheard(); };
    recognition.onerror = (event) => {
      if (!current()) return;
      session.accepted = '';
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        session.settled = true;
        block(permissionMessage);
      } else {
        session.settled = true;
        if (event.error === 'no-speech') unheard();
        else display(word, 'error', '', event.error === 'audio-capture'
          ? 'Não encontrei um microfone. Conecte um microfone e tente novamente.'
          : 'Não foi possível reconhecer agora. Confira sua conexão e tente novamente.');
      }
      finish(true);
    };
    recognition.onend = () => finish();
    display(word, 'processing', '', 'Preparando o microfone. Permita o acesso se o navegador pedir.');
    updateControls();
    session.timer = setTimeout(() => {
      if (!current()) return;
      session.settled = false;
      finish(true);
      recognition.abort();
    }, 20000);
    try { recognition.start(); }
    catch (error) {
      session.settled = true;
      if (error.name === 'NotAllowedError' || error.name === 'SecurityError') block(permissionMessage);
      else display(word, 'error', '', 'Não foi possível iniciar o microfone. Tente novamente.');
      finish(true);
    }
  }

  words.forEach((word) => word.button.addEventListener('click', () => start(word)));
  next.addEventListener('click', () => {
    if (!blocked && !active && words.length === 2 && words.every((word) => word.done)) {
      window.location.assign(next.dataset.nextUrl);
    }
  });
  window.addEventListener('pagehide', () => {
    audioPlayers.forEach((player) => player.pause());
    if (!active) return;
    const session = active;
    active = null;
    clearTimeout(session.timer);
    session.recognition.abort();
    if (!session.word.done) display(session.word, 'waiting', '', 'Fale esta palavra');
    updateControls();
  });
  if (!Recognition) block('Seu navegador não oferece suporte ao reconhecimento de voz necessário para esta atividade.');
  else if (!window.isSecureContext) block('O microfone precisa de uma conexão segura. Abra este site por HTTPS ou localhost.');
  else updateControls();
})();
