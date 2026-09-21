"""Narração SH: mesmas vozes, taxa e concatenação do Módulo 4."""
import asyncio
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'media/modulos/5/resumo.mp3'
SEGMENTOS = [
    ('Muito bem! Vamos lembrar o que você aprendeu. S e H juntos fazem um som parecido com o pedido de silêncio: shhh! Você ouviu e falou:', 'pt-BR-FranciscaNeural'),
    ('ship', 'en-US-JennyNeural'),
    ('fish', 'en-US-JennyNeural'),
    ('shoe', 'en-US-JennyNeural'),
    ('sheep', 'en-US-JennyNeural'),
    ('shop', 'en-US-JennyNeural'),
    ('shell', 'en-US-JennyNeural'),
    ('Esse som aparece no começo de', 'pt-BR-FranciscaNeural'),
    ('ship', 'en-US-JennyNeural'),
    ('e no final de', 'pt-BR-FranciscaNeural'),
    ('fish', 'en-US-JennyNeural'),
    ('Escute e repita com calma! Muito bem! Você terminou a revisão do som SH.', 'pt-BR-FranciscaNeural'),
]


async def main():
    if OUTPUT.exists():
        print(f'Arquivo já existe; preservado: {OUTPUT}')
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    chunks = []
    for text, voice in SEGMENTOS:
        response = edge_tts.Communicate(text, voice, rate='+0%')
        chunks.append(b''.join([chunk['data'] async for chunk in response.stream()
                               if chunk['type'] == 'audio']))
    # Preserva as pausas naturais dos segmentos, como no gerador do Módulo 4.
    OUTPUT.write_bytes(b''.join(chunks))
    print(OUTPUT)


if __name__ == '__main__':
    asyncio.run(main())
