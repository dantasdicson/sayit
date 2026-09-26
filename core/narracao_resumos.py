"""Roteiro de voz: blocos completos, sem conectivos sintetizados isoladamente."""
import re
from .resumos import RESUMOS

VOZ_PT = 'pt-BR-FranciscaNeural'
VOZ_EN = 'en-US-JennyNeural'
VERSAO_AUDIO = 'narracao-v2'
NUMEROS = ('zero', 'um', 'dois', 'três', 'quatro', 'cinco', 'seis', 'sete', 'oito', 'nove', 'dez')


def texto_falado(texto):
    letras = {'A': 'á', 'E': 'ê', 'I': 'i', 'O': 'ó', 'U': 'u',
              'S': 'esse', 'H': 'agá', 'C': 'cê', 'P': 'pê', 'F': 'éfe',
              'TH': 'tê agá', 'PH': 'pê agá', 'CH': 'cê agá', 'SH': 'esse agá'}
    texto = re.sub(r'\b(letra|vogal|do|da|o|a|e|som) ([AO])\b',
                   lambda m: m[1] + ' ' + letras[m[2]], texto)
    texto = re.sub(r'\b(?:TH|PH|CH|SH|[EIUSHCPF])\b',
                   lambda m: letras[m.group()], texto)
    return re.sub(r'\b(10|[0-9])\b', lambda m: NUMEROS[int(m.group())], texto)


def roteiro(numero, pares):
    resumo = RESUMOS[numero]
    if len(pares) != 4:
        raise ValueError('A narração requer os quatro pares do catálogo.')
    if numero == 1:
        abertura = ' '.join(resumo['paragrafos']) + ' Veja novamente as palavras que você aprendeu.'
        encerramento = resumo['reforco']
    else:
        esperados = [palavra.upper() for par in pares for palavra in par]
        encontrados = re.findall(r'\b[A-Z]{2,}\b', resumo['paragrafos'][0])
        if encontrados != esperados:
            raise ValueError('Texto exibido e pares do catálogo divergem.')
        abertura = 'Você ouviu e falou os seguintes pares de palavras.'
        encerramento = ' '.join((*resumo['paragrafos'][1:], resumo['reforco']))
    return [
        {'texto': texto_falado(abertura), 'voz': VOZ_PT, 'rate': '-5%', 'pausa_ms': 450},
        *[{'texto': f'{a}, {b}.', 'voz': VOZ_EN, 'rate': '-12%', 'pausa_ms': 550}
          for a, b in pares],
        {'texto': texto_falado(encerramento), 'voz': VOZ_PT, 'rate': '-5%', 'pausa_ms': 0},
    ]
