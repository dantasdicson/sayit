(() => {
  'use strict';
  const next = document.getElementById('discovery-next');
  if (!next) return;
  const status = document.getElementById('speech-status');
  const state = document.getElementById('discovery-state');
  const csrf = state?.querySelector('[name=csrfmiddlewaretoken]')?.value;
  const moduleNumber = Number(state?.dataset.modulo);
  const comparisonId = Number(state?.dataset.comparacaoId);
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const { normalize, select } = window.SayItPronuncia;
  const words = [...document.querySelectorAll('[data-practice-word]')].map((root) => ({
    root, expected: normalize(root.dataset.practiceWord), done: root.dataset.acertada === 'true',
    id: Number(root.dataset.palavraId),
    button: root.querySelector('.speak'), label: root.querySelector('.speak-label'),
    title: root.querySelector('.speech-title'), message: root.querySelector('.speech-message'),
    complete: root.querySelector('.word-complete'),
  }));
  const audioButtons = [...document.querySelectorAll('[data-audio]')];
  const audioPlayers = [...document.querySelectorAll('audio')];
  const pair = words.map((word) => word.expected.toUpperCase()).join(' e ');
  let active = null;
  const configured = !!csrf && !!state?.dataset.acertosUrl && Number.isSafeInteger(moduleNumber)
    && moduleNumber > 0 && Number.isSafeInteger(comparisonId) && comparisonId > 0
    && words.length === 2 && words.every((word) => Number.isSafeInteger(word.id) && word.id > 0)
    && new Set(words.map((word) => word.id)).size === 2;
  let blocked = !Recognition || !configured;
  let discoveryComplete = state?.dataset.concluida === 'true';
  const permissionMessage = 'O microfone é necessário para continuar. Permita o acesso ao microfone no navegador.';

  function recordError(word, transcript, result) {
    if (typeof window.CustomEvent !== 'function' || typeof window.dispatchEvent !== 'function') return;
    window.dispatchEvent(new window.CustomEvent('sayit:attempt-error', { detail: {
      url: state.dataset.errosUrl, csrf, moduleNumber, comparisonId,
      wordId: word.id, transcript, result,
    } }));
  }

  async function saveCorrect(word, transcript, session) {
    session.controller = new AbortController();
    let timeout;
    try {
      const data = await Promise.race([
        (async () => {
          const response = await fetch(state.dataset.acertosUrl, {
            method: 'POST', credentials: 'same-origin', mode: 'same-origin', redirect: 'error',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
            body: JSON.stringify({ comparacao_id: comparisonId, palavra_id: word.id, transcricao: transcript }),
            signal: session.controller.signal,
          });
          if (!response.ok || response.redirected) throw new Error('Falha ao salvar');
          return response.json();
        })(),
        new Promise((_, reject) => {
          timeout = setTimeout(() => {
            session.controller.abort();
            reject(new Error('Tempo esgotado'));
          }, 15000);
        }),
      ]);
      const ids = data?.palavras_acertadas;
      const comparisons = data?.comparacoes_concluidas;
      if (data?.modulo !== moduleNumber || !Number.isInteger(data?.percentual)
          || data.percentual < 0 || data.percentual > 100
          || !Array.isArray(ids) || !ids.every((id) => Number.isSafeInteger(id) && id > 0)
          || !ids.includes(word.id) || !Array.isArray(comparisons)
          || !comparisons.every((id) => Number.isSafeInteger(id) && id > 0)
          || comparisons.includes(comparisonId) !== words.every((item) => ids.includes(item.id))) {
        throw new Error('Resposta inválida');
      }
      return data;
    } finally {
      clearTimeout(timeout);
    }
  }

  function updateControls() {
    words.forEach((word) => { word.button.disabled = blocked || !!active || word.done; });
    audioButtons.forEach((button) => { button.disabled = !!active; });
    next.disabled = !configured || !!active || !discoveryComplete || !words.every((word) => word.done);
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
    try { recognition = window.SayItPronuncia.createRecognition(); }
    catch (error) {
      display(word, 'error', '', 'Não foi possível iniciar o microfone. Tente novamente.');
      return;
    }
    const session = { recognition, word, settled: false, accepted: '', timer: null, ending: false };
    active = session;
    const current = () => active === session;
    const unheard = () => {
      session.settled = true;
      recordError(word, '', 'nao_reconhecido');
      display(word, 'waiting', '', 'Não consegui ouvir. Tente novamente.');
    };
    const finish = async (cancelled = false) => {
      if (!current() || session.ending) return;
      session.ending = true;
      clearTimeout(session.timer);
      // A fala local só vira acerto após confirmação do servidor.
      if (session.accepted && !cancelled) {
        display(word, 'processing', '', 'Salvando seu progresso...');
        try {
          const data = await saveCorrect(word, session.accepted, session);
          if (!current()) return;
          discoveryComplete = data.comparacoes_concluidas.includes(comparisonId);
          state.dataset.percentual = String(data.percentual);
          state.dataset.concluida = String(discoveryComplete);
          words.forEach((item) => {
            item.done = data.palavras_acertadas.includes(item.id);
            item.root.dataset.acertada = String(item.done);
            if (item.done) display(item, 'correct', 'Great job!', item === word
              ? `Eu entendi: ${session.heard}` : 'Você já acertou esta palavra.');
            else display(item, 'waiting', '', 'Aguardando sua vez.');
          });
        } catch (error) {
          if (!current()) return;
          display(word, 'error', '', 'Não foi possível salvar seu progresso. Tente novamente.');
        }
      }
      if (!session.settled) unheard();
      active = null;
      updateControls();
      if (!blocked) {
        const target = words.find((item) => !item.done);
        (word.done ? (target ? target.button : next) : word.button).focus();
      }
    };
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
      const { heard, accepted } = select(result, word.expected);
      const text = normalize(heard);
      session.heard = heard;
      session.settled = true;
      if (accepted) {
        session.accepted = accepted;
        display(word, 'processing', '', 'Processando...');
      } else if (!text) unheard();
      else {
        recordError(word, heard, 'incorreto');
        display(word, 'retry', 'Try again!', `Eu entendi: ${heard}`);
      }
    };
    recognition.onnomatch = () => { if (current() && !session.settled) unheard(); };
    recognition.onerror = (event) => {
      if (!current() || session.ending) return;
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
    if (configured && !active && discoveryComplete && words.every((word) => word.done)) {
      window.location.assign(next.dataset.nextUrl);
    }
  });
  window.addEventListener('pagehide', () => {
    audioPlayers.forEach((player) => player.pause());
    if (!active) return;
    const session = active;
    active = null;
    clearTimeout(session.timer);
    session.controller?.abort();
    session.recognition.abort();
    if (!session.word.done) display(session.word, 'waiting', '', 'Fale esta palavra');
    updateControls();
  });
  // Ao voltar pelo histórico, consultar novamente o estado do usuário atual.
  window.addEventListener('pageshow', (event) => { if (event.persisted) window.location.reload(); });
  words.filter((word) => word.done).forEach((word) => display(word, 'correct', 'Great job!', 'Você já acertou esta palavra.'));
  if (!configured) block('Não foi possível carregar a atividade. Atualize a página e tente novamente.');
  else if (!Recognition) block('Seu navegador não oferece suporte ao reconhecimento de voz necessário para esta atividade.');
  else if (!window.isSecureContext) block('O microfone precisa de uma conexão segura. Abra este site por HTTPS ou localhost.');
  else updateControls();
})();
