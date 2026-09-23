"""Gera o resumo atualizado do I; use --sobrescrever para substituir a versão FIN/FINE."""
import argparse
import asyncio
from pathlib import Path
import edge_tts

OUTPUT = Path(__file__).resolve().parents[1] / 'media/modulos/2/resumo.mp3'
SEGMENTOS = [
    ('Muito bem! Vamos lembrar o que você aprendeu. O E no final fica silencioso e pode mudar o som da vogal I. Você ouviu e falou:', 'pt-BR-FranciscaNeural'),
    *[(word, 'en-US-JennyNeural') for word in ('kit', 'kite', 'bit', 'bite', 'pin', 'pine')],
    ('Nessas palavras, o E final faz o I soar como o nome da letra I em inglês. Uma letra muda o som e o significado! Muito bem! Você terminou a revisão do Magic E, som do I.', 'pt-BR-FranciscaNeural'),
]

async def main(sobrescrever=False):
    if OUTPUT.exists() and not sobrescrever:
        print('Resumo existente preservado; use --sobrescrever para atualizar.')
        return
    chunks = []
    for text, voice in SEGMENTOS:
        speech = edge_tts.Communicate(text, voice, rate='+0%')
        chunks.append(b''.join([part['data'] async for part in speech.stream() if part['type'] == 'audio']))
    if not all(chunks):
        raise RuntimeError('Segmento sem áudio')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix('.tmp.mp3')
    try:
        temporary.write_bytes(b''.join(chunks))
        temporary.replace(OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)
    print(OUTPUT)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sobrescrever', action='store_true')
    asyncio.run(main(parser.parse_args().sobrescrever))
