"""Narração CH: mesmas vozes, taxa e concatenação dos módulos anteriores."""
import asyncio
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'media/modulos/6/resumo.mp3'
SEGMENTOS = [
    ('Muito bem! Vamos lembrar o que você aprendeu. C e H juntos fazem um som parecido com tch. Você ouviu e falou:', 'pt-BR-FranciscaNeural'),
    ('chair', 'en-US-JennyNeural'),
    ('chicken', 'en-US-JennyNeural'),
    ('cheese', 'en-US-JennyNeural'),
    ('beach', 'en-US-JennyNeural'),
    ('child', 'en-US-JennyNeural'),
    ('chocolate', 'en-US-JennyNeural'),
    ('Esse som aparece no começo de', 'pt-BR-FranciscaNeural'),
    ('chair', 'en-US-JennyNeural'),
    ('e no final de', 'pt-BR-FranciscaNeural'),
    ('beach', 'en-US-JennyNeural'),
    ('Escute e repita com calma! Muito bem! Você terminou a revisão do som CH.', 'pt-BR-FranciscaNeural'),
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
    OUTPUT.write_bytes(b''.join(chunks))
    print(OUTPUT)


if __name__ == '__main__':
    asyncio.run(main())
