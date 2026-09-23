"""Narração OO com as vozes e a taxa usadas nos módulos anteriores."""
import asyncio
from pathlib import Path
import edge_tts

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'media/modulos/9/resumo.mp3'
SEGMENTOS = [
    ('Muito bem! Vamos lembrar o que você aprendeu. A combinação O O pode ter dois sons. Você ouviu e falou:', 'pt-BR-FranciscaNeural'),
    ('moon', 'en-US-JennyNeural'), ('book', 'en-US-JennyNeural'),
    ('food', 'en-US-JennyNeural'), ('good', 'en-US-JennyNeural'),
    ('room', 'en-US-JennyNeural'), ('look', 'en-US-JennyNeural'),
    ('school', 'en-US-JennyNeural'), ('foot', 'en-US-JennyNeural'),
    ('Em moon, food, room e school, o som é longo. Em book, good, look e foot, o som é curto. Escute e repita sem pressa! Muito bem! Você terminou a revisão dos sons de O O.', 'pt-BR-FranciscaNeural'),
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
    OUTPUT.write_bytes(b''.join(chunks))
    print(OUTPUT)


if __name__ == '__main__':
    asyncio.run(main())
