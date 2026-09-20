"""Variantes homófonas revisadas; nunca usar similaridade entre pares pedagógicos."""
import json
from pathlib import Path

VARIANTES = json.loads((Path(__file__).parent / 'data' / 'pronuncia_variantes.json').read_text(encoding='utf-8'))


def corresponde(esperada_normalizada, transcricao_normalizada):
    return bool(transcricao_normalizada) and (
        transcricao_normalizada == esperada_normalizada
        or transcricao_normalizada in VARIANTES.get(esperada_normalizada, [])
    )
