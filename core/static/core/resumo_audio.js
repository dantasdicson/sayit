(() => {
  'use strict';
  const player = document.getElementById('summary-audio');
  const button = document.getElementById('summary-listen');
  if (!player || !button) return;
  const label = document.getElementById('summary-listen-label');
  const status = document.getElementById('audio-status');
  let active = false;
  let attempt = 0;

  function reset(message = '') {
    active = false;
    attempt += 1;
    button.setAttribute('aria-pressed', 'false');
    button.removeAttribute('aria-busy');
    label.textContent = 'Ouvir explicação';
    status.textContent = message;
  }

  function stop() {
    reset('Reprodução interrompida. Você pode ouvir novamente.');
    player.pause();
    player.currentTime = 0;
  }

  button.addEventListener('click', async () => {
    if (active) { stop(); return; }
    const current = ++attempt;
    active = true;
    button.setAttribute('aria-pressed', 'true');
    button.setAttribute('aria-busy', 'true');
    label.textContent = 'Interromper explicação';
    status.textContent = 'Carregando explicação...';
    try {
      player.currentTime = 0;
      await player.play();
      if (current === attempt) status.textContent = 'Reproduzindo explicação.';
    } catch (error) {
      if (current === attempt) reset('Não foi possível ouvir agora. Tente novamente.');
    }
  });
  player.addEventListener('ended', () => reset('Você ouviu a explicação. Pode ouvir novamente ou concluir o módulo.'));
  player.addEventListener('error', () => reset('Não foi possível ouvir agora. Tente novamente.'));
  player.addEventListener('pause', () => { if (active) reset('Reprodução interrompida. Você pode ouvir novamente.'); });
  window.addEventListener('pagehide', stop);
  player.controls = false;
  button.hidden = false;
})();
