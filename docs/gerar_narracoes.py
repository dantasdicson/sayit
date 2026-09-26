"""Narração validada: PCM, pausas, ganho consistente e codificação MP3 única."""
import argparse
import asyncio
from array import array
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import edge_tts

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sayit.settings')
import django
django.setup()
from core.management.commands.popular_sayit import PARES_DIDATICOS
from core.narracao_resumos import roteiro, VERSAO_AUDIO
from core.resumos import RESUMOS
SR = 24000


def pcm(ffmpeg, path):
    return subprocess.check_output([ffmpeg, '-v', 'error', '-i', str(path),
                                   '-f', 's16le', '-ar', str(SR), '-ac', '1', '-'])


def volume(ffmpeg, path):
    result = subprocess.run([ffmpeg, '-hide_banner', '-i', str(path), '-af',
        'loudnorm=I=-18:TP=-1.5:LRA=7:print_format=json', '-f', 'null', '-'],
        capture_output=True, text=True, check=True)
    return json.JSONDecoder().raw_decode(result.stderr[result.stderr.rfind('{'):])[0]


def preparar(raw):
    samples = array('h', raw)
    if sys.byteorder != 'little':
        samples.byteswap()
    voiced = [i for i in range(0, len(samples), 240)
              if max(map(abs, samples[i:i + 240]), default=0) > 60]
    if not voiced:
        raise ValueError('Segmento sem fala detectável.')
    samples = samples[max(0, voiced[0] - 1920):min(len(samples), voiced[-1] + 3120)]
    rms = math.sqrt(sum(float(x) ** 2 for x in samples) / len(samples))
    peak = max(map(abs, samples))
    gain = min(10 ** (6 / 20), (32767 * 10 ** (-23 / 20)) / rms,
               (32767 * 10 ** (-3 / 20)) / peak)
    for i in range(len(samples)):
        fade = min(1, i / 120, (len(samples) - 1 - i) / 120)
        samples[i] = round(samples[i] * gain * max(0, fade))
    if sys.byteorder != 'little':
        samples.byteswap()
    return samples.tobytes()


def analisar(ffmpeg, path):
    raw = pcm(ffmpeg, path)
    samples = array('h', raw)
    if sys.byteorder != 'little':
        samples.byteswap()
    silent = longest = 0
    for start in range(0, len(samples), 240):
        if max(map(abs, samples[start:start + 240]), default=0) < 60:
            silent += 1
            longest = max(longest, silent)
        else:
            silent = 0
    loud = volume(ffmpeg, path)
    return {'duracao_s': round(len(samples) / SR, 3),
            'lufs': float(loud['input_i']), 'pico_dbtp': float(loud['input_tp']),
            'lra': float(loud['input_lra']), 'maior_silencio_s': longest / 100,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


async def sintetizar(texto, voz, rate, path):
    for tentativa in range(3):
        try:
            await edge_tts.Communicate(texto, voz, rate=rate).save(str(path))
            return
        except Exception:
            if tentativa == 2:
                raise
            await asyncio.sleep(1 + tentativa)


async def gerar(numero, ffmpeg, output):
    segmentos = roteiro(numero, PARES_DIDATICOS[numero])
    destino = output / RESUMOS[numero]['audio']
    with tempfile.TemporaryDirectory(prefix=f'sayit-voz-{numero}-') as pasta:
        pasta = Path(pasta)
        combined = bytearray(bytes(SR // 5))
        for i, segmento in enumerate(segmentos):
            path = pasta / f'{i}.mp3'
            await sintetizar(segmento['texto'], segmento['voz'], segmento['rate'], path)
            combined.extend(preparar(pcm(ffmpeg, path)))
            combined.extend(bytes(int(SR * 2 * segmento['pausa_ms'] / 1000)))
            print(f'Módulo {numero}: bloco {i + 1}/{len(segmentos)}', flush=True)
        combined.extend(bytes(SR // 3))
        wav = pasta / 'montagem.wav'
        subprocess.run([ffmpeg, '-v', 'error', '-f', 's16le', '-ar', str(SR),
                        '-ac', '1', '-i', '-', str(wav)], input=combined, check=True)
        measured = volume(ffmpeg, wav)
        filtro = ('loudnorm=I=-18:TP=-1.5:LRA=7:linear=true:'
                  f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
                  f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:"
                  f"offset={measured['target_offset']}")
        final = pasta / 'final.mp3'
        subprocess.run([ffmpeg, '-v', 'error', '-i', str(wav), '-af', filtro,
                        '-ar', str(SR), '-ac', '1', '-codec:a', 'libmp3lame',
                        '-b:a', '128k', str(final)], check=True)
        metrics = analisar(ffmpeg, final)
        if not (10 < metrics['duracao_s'] < 180 and -19 < metrics['lufs'] < -17
                and metrics['pico_dbtp'] < -1 and metrics['maior_silencio_s'] < 2.5):
            raise ValueError(f'Validação sonora falhou: {metrics}')
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.exists():
            raise FileExistsError(f'Destino já existe; use outra pasta de saída: {destino}')
        shutil.copyfile(final, destino)
        metadata = {'versao': VERSAO_AUDIO, 'modulo': numero, 'segmentos': segmentos,
                    'texto_exibido': RESUMOS[numero], 'pares': PARES_DIDATICOS[numero],
                    'metricas': metrics}
        destino.with_suffix('.json').write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        return metadata


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--modulo', type=int, choices=sorted(RESUMOS))
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--audit-only', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('FFmpeg não encontrado.')
    numeros = [args.modulo] if args.modulo else sorted(RESUMOS)
    output = args.output_dir or ROOT / '.runlogs' / ('narracao-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    if args.audit_only:
        resultado = {n: analisar(ffmpeg, ROOT / 'media' / RESUMOS[n]['audio']) for n in numeros}
    else:
        resultado = {}
        for numero in numeros:
            resultado[numero] = await gerar(numero, ffmpeg, output)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(resultado if args.audit_only else
        {n: item['metricas'] for n, item in resultado.items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
