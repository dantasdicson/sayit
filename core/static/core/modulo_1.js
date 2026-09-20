const players = [...document.querySelectorAll('audio')];
const status = document.getElementById('audio-status');
document.querySelectorAll('[data-audio]').forEach((button) => {
  const player = document.getElementById(button.dataset.audio);
  player.controls = false;
  button.hidden = false;
  const reset = () => button.removeAttribute('aria-busy');
  player.addEventListener('ended', reset);
  player.addEventListener('pause', reset);
  player.addEventListener('error', () => {
    reset();
    status.textContent = 'Não foi possível ouvir agora. Tente novamente.';
  });
  button.addEventListener('click', async () => {
    players.forEach((other) => { if (other !== player) other.pause(); });
    status.textContent = '';
    button.setAttribute('aria-busy', 'true');
    try {
      player.currentTime = 0;
      await player.play();
    } catch (error) {
      reset();
      if (error.name !== 'AbortError') status.textContent = 'Não foi possível ouvir agora. Tente novamente.';
    }
  });
});
