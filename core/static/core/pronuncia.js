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
    return { heard: transcripts[0] || '', accepted: transcripts.find(text => matches(expected, text)) || '' };
  }
  window.SayItPronuncia = { normalize, matches, select };
})();
