"""Narrações contínuas com exemplos em inglês. Requer edge-tts e FFmpeg."""
import argparse
import array
import asyncio
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.resumos import RESUMOS

PT = 'pt-BR-FranciscaNeural'
EN = 'en-US-JennyNeural'
EXEMPLOS = {
    1: 'cat, cake. cap, cape. tap, tape. mad, made.',
    2: 'bit, bite. can, cane. pin, pine. sit, site.',
    3: 'hop, hope. not, note. rob, robe.',
    4: 'cub, cube. tub, tube. cut, cute.',
    5: 'ship, fish. shark, sheep. shop, shovel.',
    6: 'chair, chicken. cheese, beach. child, chocolate.',
    7: 'think, this. tooth, that. bath, mother.',
    8: 'phone, photo. elephant, dolphin. alphabet, trophy.',
    9: 'moon, book. food, good. room, look. school, foot.',
}
EXPLICACOES = {
    1: 'Percebeu a diferença? Nessas palavras, o ê no final fica em silêncio, mas muda o som da vogal á. Ela passa a soar como o nome dessa letra em inglês.',
    2: 'Percebeu a diferença? Nessas palavras, o ê no final fica em silêncio e muda o som da vogal. Compare cada par e escute como uma letra muda o jeito de falar e o significado da palavra.',
    3: 'Percebeu a diferença? Nessas palavras, o ê no final fica em silêncio, mas muda o som da vogal ó. Ela passa a soar como o nome dessa letra em inglês.',
    4: 'Percebeu a diferença? Nessas palavras, o ê no final fica em silêncio e pode mudar o som da vogal u. Ela pode soar como o nome dessa letra em inglês.',
    5: 'Agora, pense nas letras ésse e agá. Juntas, elas fazem aquele som de pedir silêncio. Esse som pode aparecer no começo ou no final da palavra.',
    6: 'Agora, pense nas letras cê e agá. Juntas, elas fazem um som parecido com o começo de tchau. Esse som pode aparecer no começo ou no final da palavra.',
    7: 'Para fazer esses sons, coloque de leve a ponta da língua entre os dentes e deixe o ar passar. Em algumas palavras, a garganta vibra. Em outras, não. Escute novamente e perceba essa diferença.',
    8: 'Nessas palavras, as letras pê e agá trabalham juntas e fazem o som de éfe. Essa combinação pode aparecer no começo ou no meio da palavra.',
    9: 'Você ouviu dois sons para as letras ó e ó. Em algumas palavras, o som é mais longo. Em outras, é mais curto. Observe a posição da boca e compare o som de cada par.',
}


def segmentos(numero):
    yield ('Muito bem! Vamos relembrar o que você praticou. Primeiro, escute as palavras e compare os sons.', PT, .4)
    yield (EXEMPLOS[numero], EN, .55)
    yield (EXPLICACOES[numero] + ' Você pode ouvir novamente e repetir, sem pressa.', PT, .45)
    if numero == 7:
        yield ('Em inglês, escute primeiro as palavras sem vibração na garganta.', PT, .3)
        yield ('think. tooth. bath.', EN, .4)
        yield ('Agora, escute as palavras com vibração.', PT, .3)
        yield ('this. that. mother.', EN, .4)
    if numero == 9:
        yield ('Escute primeiro os exemplos com o som longo.', PT, .3)
        yield ('moon. food. room. school.', EN, .4)
        yield ('Agora, os exemplos com o som curto.', PT, .3)
        yield ('book. good. look. foot.', EN, .4)
    yield (RESUMOS[numero]['reforco'], PT, .2)


async def gerar(numero, sobrescrever, ffmpeg):
    destino = ROOT / 'media' / RESUMOS[numero]['audio']
    if destino.exists() and not sobrescrever:
        print(f'Módulo {numero}: preservado', flush=True)
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='narracao-') as temp:
        temp = Path(temp)
        combinado = temp / 'combinado.wav'
        with wave.open(str(combinado), 'wb') as final:
            final.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            final.writeframes(bytes(24000 // 5 * 2))
            for indice, (texto, voz, pausa) in enumerate(segmentos(numero)):
                mp3, wav = temp / f'{indice}.mp3', temp / f'{indice}.wav'
                await edge_tts.Communicate(texto, voz, rate='-3%' if voz == PT else '-8%').save(str(mp3))
                subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', str(mp3), '-ar', '24000', '-ac', '1', str(wav)], check=True)
                with wave.open(str(wav), 'rb') as fonte:
                    amostras = array.array('h', fonte.readframes(fonte.getnframes()))
                ativos = [i for i, valor in enumerate(amostras) if abs(valor) > 100]
                if not ativos:
                    raise RuntimeError(f'Módulo {numero}: segmento sem fala')
                # Retire silêncio externo, preservando as pausas naturais da voz.
                inicio = max(0, ativos[0] - 1200)
                fim = min(len(amostras), ativos[-1] + 2400)
                final.writeframes(amostras[inicio:fim].tobytes())
                final.writeframes(bytes(round(24000 * pausa) * 2))
        pronto = temp / 'resumo.mp3'
        subprocess.run([ffmpeg, '-v', 'error', '-i', str(combinado), '-af', 'loudnorm=I=-18:TP=-2:LRA=11', '-ar', '24000', '-ac', '1', '-codec:a', 'libmp3lame', '-b:a', '96k', str(pronto)], check=True)
        subprocess.run([ffmpeg, '-v', 'error', '-i', str(pronto), '-f', 'null', '-'], check=True)
        temporario = destino.with_suffix('.tmp.mp3')
        try:
            shutil.copyfile(pronto, temporario)
            temporario.replace(destino)
        finally:
            temporario.unlink(missing_ok=True)
    print(f'Módulo {numero}: narração atualizada', flush=True)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--modulo', type=int, choices=sorted(RESUMOS))
    parser.add_argument('--sobrescrever', action='store_true')
    args = parser.parse_args()
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise SystemExit('FFmpeg não encontrado no PATH.')
    for numero in ([args.modulo] if args.modulo else sorted(RESUMOS)):
        await gerar(numero, args.sobrescrever, ffmpeg)


if __name__ == '__main__':
    asyncio.run(main())
