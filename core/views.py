from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from core.models import Modulo
from core.resumos import RESUMOS

@login_required
def explicacao_modulo_1(request):
    modulo = get_object_or_404(Modulo, numero=1, ativo=True)
    return render(request, 'core/explicacao_modulo_1.html', {'modulo': modulo})


@login_required
def descoberta_modulo_1(request, numero):
    pares = (('cat', 'cake'), ('cap', 'cape'), ('tap', 'tape'), ('mad', 'made'))
    if not 1 <= numero <= len(pares):
        raise Http404('Descoberta inexistente.')
    modulo = get_object_or_404(Modulo, numero=1, ativo=True)
    base, comparada = pares[numero - 1]
    par = get_object_or_404(
        modulo.comparacoes.select_related('palavra_base', 'palavra_comparada'),
        palavra_base__palavra=base, palavra_comparada__palavra=comparada,
    )
    cards = []
    for palavra in (par.palavra_base, par.palavra_comparada):
        imagem = palavra.imagem.url if palavra.imagem else palavra.imagem.storage.url(
            f'palavras/imagens/{palavra.palavra}.webp'
        )
        cards.append({'palavra': palavra, 'imagem_url': imagem})
    return render(request, 'core/descoberta_modulo_1.html', {
        'cards': cards, 'numero': numero, 'total': len(pares),
        'proxima': numero + 1 if numero < len(pares) else None,
    })


@login_required
def resumo_modulo(request, numero):
    resumo = RESUMOS.get(numero)
    if resumo is None:
        raise Http404('Resumo indisponível.')
    modulo = get_object_or_404(Modulo, numero=numero, ativo=True)
    pares = []
    for comparacao in modulo.comparacoes.select_related(
        'palavra_base', 'palavra_comparada'
    ).order_by('ordem', 'pk'):
        cards = []
        for palavra in (comparacao.palavra_base, comparacao.palavra_comparada):
            imagem = palavra.imagem
            cards.append({
                'palavra': palavra,
                'imagem_url': imagem.url if imagem and imagem.storage.exists(imagem.name) else '',
            })
        pares.append(cards)
    audio_url = ''
    try:
        if default_storage.exists(resumo['audio']) and default_storage.size(resumo['audio']) > 0:
            audio_url = default_storage.url(resumo['audio'])
    except OSError:
        # Falha de acesso à mídia não impede a leitura nem a conclusão.
        pass
    return render(request, 'core/resumo_modulo.html', {
        'modulo': modulo, 'resumo': resumo, 'pares': pares,
        'audio_url': audio_url, 'conclusao_url': reverse(resumo['conclusao']),
    })


@login_required
def conclusao_modulo_1(request):
    modulo = get_object_or_404(Modulo, numero=1, ativo=True)
    return render(request, 'core/conclusao_modulo_1.html', {'modulo': modulo})


@login_required
def pratica_modulo_1(request):
    modulo = get_object_or_404(Modulo, numero=1, ativo=True)
    sequencia = ('cat', 'cake', 'cap', 'cape', 'tap', 'tape', 'mad', 'made')
    palavras = {p.palavra: p for p in modulo.palavras.filter(ativa=True, palavra__in=sequencia)}
    cards = []
    for texto in sequencia:
        palavra = palavras.get(texto)
        if palavra is None:
            continue
        cards.append({
            'palavra': palavra.palavra,
            'traducao': palavra.traducao,
            'imagem': palavra.imagem.url if palavra.imagem else palavra.imagem.storage.url(
                f'palavras/imagens/{palavra.palavra}.webp'
            ),
            'audio': palavra.audio.url if palavra.audio else '',
        })
    return render(request, 'core/pratica_modulo_1.html', {
        'palavras': cards if len(cards) == len(sequencia) else [],
    })
