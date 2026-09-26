(() => {
  'use strict';
  const data = document.getElementById('pronuncia-variantes');
  const variants = data ? JSON.parse(data.textContent) : {};
  const normalize = text => typeof text === 'string'
    ? text.toLowerCase().replace(/[.,!?;:"'“”‘’…()[\]{}-]/g, '').replace(/\s+/g, ' ').trim() : '';
  function matches(expected, transcript) {
    const word = normalize(expected), text = normalize(transcript);
    return !!text && (text === word || (Object.hasOwn(variants, word) && variants[word].includes(text)));
  }
  function select(result, expected) {
    const transcripts = Array.from(result || []).map(item => item?.transcript)
      .filter(text => typeof text === 'string');
    const accepted = transcripts.find(text => matches(expected, text)) || '';
    // As exceções aceitas são apresentadas como as palavras pedagógicas.
    // A transcrição aceita permanece intacta para validação e registro no servidor.
    const word = normalize(expected), text = normalize(accepted);
    const displayExpected = (word === 'mad' && text === 'matt')
      || (word === 'cat' && text === 'cats')
      || (word === 'peach' && text === 'beach')
      || (word === 'fin' && !!accepted);
    const heard = displayExpected ? word : transcripts[0] || '';
    return { heard, accepted };
  }
  function createRecognition() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new Recognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 3;
    return recognition;
  }
  window.SayItPronuncia = { normalize, matches, select, createRecognition };
})();
