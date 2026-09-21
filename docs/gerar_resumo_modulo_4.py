"""Gera o resumo do Módulo 4 com as vozes oficiais do projeto."""
import asyncio
from pathlib import Path
import edge_tts

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'media/modulos/4/resumo.mp3'

SEGMENTOS = [
    ('Muito bem! Vamos lembrar o que você aprendeu. No Magic E, você descobriu que a letra E, quando aparece no final de algumas palavras, fica silenciosa, mas pode mudar o som da vogal U. Compare:', 'pt-BR-FranciscaNeural'),
    ('cub', 'en-US-JennyNeural'),
    ('cube', 'en-US-JennyNeural'),
    ('tub', 'en-US-JennyNeural'),
    ('tube', 'en-US-JennyNeural'),
    ('cut', 'en-US-JennyNeural'),
    ('cute', 'en-US-JennyNeural'),
    ('Percebeu a diferença? O E final não é pronunciado, mas pode mudar o som do U. Muito bem! Você terminou a revisão do Magic E, som do U.', 'pt-BR-FranciscaNeural'),
]


async def main():
    if OUTPUT.exists():
        print(f'Arquivo já existe; preservado: {OUTPUT}')
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    chunks = []
    for text, voice in SEGMENTOS:
        response = edge_tts.Communicate(text, voice, rate='+0%')
        chunks.append(b''.join([chunk['data'] async for chunk in response.stream() if chunk['type'] == 'audio']))
    with OUTPUT.open('wb') as destination:
        for chunk in chunks:
            destination.write(chunk)
    print(OUTPUT)


if __name__ == '__main__':
    asyncio.run(main())
