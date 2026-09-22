(() => {
  'use strict';
  window.addEventListener('sayit:attempt-error', (event) => {
    const detail = event.detail || {};
    if (!detail.url || !detail.csrf || !Number.isSafeInteger(detail.comparisonId)
        || !Number.isSafeInteger(detail.wordId)
        || !['incorreto', 'nao_reconhecido'].includes(detail.result)) return;
    fetch(detail.url, {
      method: 'POST', credentials: 'same-origin', mode: 'same-origin', redirect: 'error',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': detail.csrf },
      body: JSON.stringify({
        comparacao_id: detail.comparisonId,
        palavra_id: detail.wordId,
        transcricao: typeof detail.transcript === 'string' ? detail.transcript : '',
        resultado: detail.result,
      }),
    }).catch(() => {});
  });
})();
