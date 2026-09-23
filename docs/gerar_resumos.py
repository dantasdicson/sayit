"""Gera resumos a partir do texto da tela, alternando as vozes oficiais."""
import argparse
import asyncio
import re
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.resumos import RESUMOS


def segmentos(numero):
    resumo = RESUMOS[numero]
    for texto in (*resumo['paragrafos'], resumo['reforco']):
        for trecho in re.split(r'(\b[A-Z]{3,}\b)', texto):
            if not re.search(r'\w', trecho):
                continue
            ingles = bool(re.fullmatch(r'[A-Z]{3,}', trecho))
            yield (trecho.lower() if ingles else trecho,
                   'en-US-JennyNeural' if ingles else 'pt-BR-FranciscaNeural')


async def gerar(numero, sobrescrever):
    destino = ROOT / 'media' / RESUMOS[numero]['audio']
    if destino.exists() and not sobrescrever:
        print(f'Módulo {numero}: preservado', flush=True)
        return
    partes = []
    for texto, voz in segmentos(numero):
        fala = edge_tts.Communicate(texto, voz, rate='+0%')
        partes.append(b''.join([p['data'] async for p in fala.stream() if p['type'] == 'audio']))
    if not partes or not all(partes):
        raise RuntimeError(f'Módulo {numero}: áudio vazio')
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix('.tmp.mp3')
    try:
        temporario.write_bytes(b''.join(partes))
        temporario.replace(destino)
    finally:
        temporario.unlink(missing_ok=True)
    print(f'Módulo {numero}: resumo atualizado', flush=True)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--modulo', type=int, choices=sorted(RESUMOS))
    parser.add_argument('--sobrescrever', action='store_true')
    args = parser.parse_args()
    for numero in ([args.modulo] if args.modulo else sorted(RESUMOS)):
        await gerar(numero, args.sobrescrever)


if __name__ == '__main__':
    asyncio.run(main())
