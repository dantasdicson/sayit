"""Gera somente o resumo do Módulo 3, no padrão dos resumos anteriores.

Execute com o Python da .venv. Requer edge-tts e FFmpeg já instalados.
Não sobrescreve um resumo existente. Temporários são removidos ao terminar.
"""
import asyncio
import array
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'media/modulos/3/resumo.mp3'
INTRO = ('Muito bem! Vamos lembrar o que você aprendeu. No Magic E, você descobriu '
         'que a letra E, quando aparece no final de algumas palavras, fica silenciosa, '
         'mas pode mudar o som da vogal O. Compare:')
OUTRO = ('Percebeu a diferença? O E final não é pronunciado, mas muda o som do O. '
         'Muito bem! Você terminou a revisão do Magic E, som do O.')

async def main():
    if OUTPUT.exists():
        raise SystemExit('Resumo já existe; arquivo preservado.')
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise SystemExit('FFmpeg não encontrado no PATH.')
    segments = [(INTRO, 'pt-BR-FranciscaNeural')]
    segments += [(word, 'en-US-JennyNeural') for word in ['hop', 'hope', 'not', 'note', 'rob', 'robe']]
    segments += [(OUTRO, 'pt-BR-FranciscaNeural')]
    scratch = ROOT.parent / 'work'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='resumo-modulo-3-', dir=scratch) as tmp:
        tmp = Path(tmp)
        chunks = []
        for i, (text, voice) in enumerate(segments):
            mp3, wav = tmp / f'{i}.mp3', tmp / f'{i}.wav'
            await edge_tts.Communicate(text, voice, rate='+0%').save(str(mp3))
            subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', str(mp3), '-ar', '24000', '-ac', '1', str(wav)], check=True)
            with wave.open(str(wav), 'rb') as f:
                samples = array.array('h', f.readframes(f.getnframes()))
            active = [j for j, v in enumerate(samples) if abs(v) > 160]
            if not active:
                raise RuntimeError('Segmento sem fala')
            chunks.append(samples[max(0, active[0]-120):min(len(samples), active[-1]+121)].tobytes())
            print(f'Segmento {i+1}/{len(segments)}: {voice}', flush=True)
        assembled = tmp / 'assembled.wav'
        with wave.open(str(assembled), 'wb') as f:
            f.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            f.writeframes(bytes(24000 // 5 * 2))
            for i, chunk in enumerate(chunks):
                f.writeframes(chunk)
                gap = .35 if i in [1, 3, 5] else .65
                f.writeframes(bytes(round(24000 * gap) * 2))
        final = tmp / 'resumo.mp3'
        subprocess.run([ffmpeg, '-v', 'error', '-i', str(assembled), '-codec:a', 'libmp3lame', '-b:a', '128k', str(final)], check=True)
        subprocess.run([ffmpeg, '-v', 'error', '-i', str(final), '-f', 'null', '-'], check=True)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT.open('xb') as destination, final.open('rb') as source:
            shutil.copyfileobj(source, destination)
        print(OUTPUT, flush=True)

if __name__ == '__main__':
    asyncio.run(main())
