"""Similaridade textual ordenada, não uma análise acústica da pronúncia."""
from decimal import Decimal, ROUND_HALF_UP
from .progresso import normalizar_texto
from .desafio_config import NOTA_MINIMA


def arredondar(valor):
    return int(Decimal(str(valor)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def faixa(nota):
    if nota >= 90:
        return 'Excelente!', 'Você falou a frase muito bem!'
    if nota >= 75:
        return 'Muito bem!', 'Quase perfeito. Algumas palavras podem ser melhoradas.'
    if nota >= 50:
        return 'Continue praticando!', 'Você está no caminho certo. Preste atenção nas palavras destacadas.'
    return 'Vamos tentar novamente!', 'Algumas palavras ainda não foram reconhecidas. Ouça e tente falar novamente.'


def estrelas(nota):
    return 5 if nota >= 90 else 4 if nota >= 80 else 3 if nota >= 70 else 2 if nota >= 50 else 1


def avaliar(frase, transcricao, importantes):
    esperadas = normalizar_texto(frase).split()
    ouvidas = normalizar_texto(transcricao).split()
    if not esperadas or not importantes:
        raise ValueError('Configure frase e palavras importantes.')
    # Maior subsequência comum: respeita ordem, repetições e palavras inteiras.
    # Não aplica os bypasses de palavras isoladas (PEACH/BEACH, por exemplo).
    n, m = len(esperadas), len(ouvidas)
    tabela = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            tabela[i][j] = 1 + tabela[i + 1][j + 1] if esperadas[i] == ouvidas[j] else max(tabela[i + 1][j], tabela[i][j + 1])
    indices, indices_ouvidos = [], []
    i = j = 0
    while i < n and j < m:
        if esperadas[i] == ouvidas[j]:
            indices.append(i)
            indices_ouvidos.append(j)
            i += 1
            j += 1
        elif tabela[i + 1][j] >= tabela[i][j + 1]:
            i += 1
        else:
            j += 1
    chaves = [i for i, p in enumerate(esperadas) if p in importantes]
    if not chaves:
        raise ValueError('Palavras importantes precisam estar na frase.')
    acertos = len(indices)
    pontos_palavras = 60 * acertos / max(n, m)
    pontos_importantes = 30 * sum(i in indices for i in chaves) / len(chaves)
    pontos_completa = 10 if acertos == n and m == n else 0
    nota = arredondar(pontos_palavras + pontos_importantes + pontos_completa)
    titulo, mensagem = faixa(nota)
    return {
        'nota': nota, 'aprovado': nota >= NOTA_MINIMA, 'estrelas': estrelas(nota),
        'titulo': titulo, 'mensagem': mensagem, 'reconhecidas': acertos, 'total': n,
        'corretas': [esperadas[i] for i in indices],
        'faltantes': [p for i, p in enumerate(esperadas) if i not in indices],
        'extras': [p for j, p in enumerate(ouvidas) if j not in indices_ouvidos],
        'importantes': list(importantes),
        'importantes_faltantes': [esperadas[i] for i in chaves if i not in indices],
        'componentes': {'palavras': round(pontos_palavras, 2),
                        'importantes': round(pontos_importantes, 2), 'completa': pontos_completa},
    }
