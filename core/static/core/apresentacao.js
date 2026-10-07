(() => {
  const dialog = document.getElementById('welcome-dialog');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  dialog.close();
  dialog.showModal();
  dialog.addEventListener('cancel', (event) => {
    event.preventDefault();
    document.getElementById('welcome-form').requestSubmit(dialog.querySelector('.welcome-close'));
  });
})();
