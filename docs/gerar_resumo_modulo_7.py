"""Narração TH: mesmas vozes, taxa e concatenação dos módulos anteriores."""
import asyncio
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'media/modulos/7/resumo.mp3'
SEGMENTOS = [
    ('Muito bem! Vamos lembrar o que você aprendeu. T e H juntos podem fazer dois sons. Coloque de leve a ponta da língua entre os dentes e sopre. Você ouviu e falou:', 'pt-BR-FranciscaNeural'),
    ('think', 'en-US-JennyNeural'),
    ('this', 'en-US-JennyNeural'),
    ('tooth', 'en-US-JennyNeural'),
    ('that', 'en-US-JennyNeural'),
    ('bath', 'en-US-JennyNeural'),
    ('mother', 'en-US-JennyNeural'),
    ('Em', 'pt-BR-FranciscaNeural'),
    ('think', 'en-US-JennyNeural'),
    ('a garganta não vibra. Em', 'pt-BR-FranciscaNeural'),
    ('this', 'en-US-JennyNeural'),
    ('ela vibra. Escute e repita com calma! Muito bem! Você terminou a revisão dos sons de T H.', 'pt-BR-FranciscaNeural'),
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
