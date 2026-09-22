"""Narração PH com as vozes e a taxa usadas nos módulos anteriores."""
import asyncio
from pathlib import Path
import edge_tts

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'media/modulos/8/resumo.mp3'
SEGMENTOS = [
    ('Muito bem! Vamos lembrar o que você aprendeu. P e H juntos podem fazer o som de F. Você ouviu e falou:', 'pt-BR-FranciscaNeural'),
    ('phone', 'en-US-JennyNeural'), ('photo', 'en-US-JennyNeural'),
    ('elephant', 'en-US-JennyNeural'), ('dolphin', 'en-US-JennyNeural'),
    ('alphabet', 'en-US-JennyNeural'), ('trophy', 'en-US-JennyNeural'),
    ('O som de P H pode aparecer no começo ou no meio das palavras. Escute e repita com calma! Muito bem! Você terminou a revisão do som P H.', 'pt-BR-FranciscaNeural'),
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
