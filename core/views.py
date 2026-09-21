from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from core.models import Modulo
from core import progresso
from core.resumos import RESUMOS
from core.pronuncia import VARIANTES

@login_required
def explicacao_modulo_1(request):
    modulo = get_object_or_404(Modulo, numero=1, ativo=True)
    return render(request, 'core/explicacao_modulo_1.html', {'modulo': modulo})


@login_required
@never_cache
def descoberta_modulo_1(request, numero, modulo_numero=1):
    if modulo_numero not in (1, 2):
        raise Http404('Módulo indisponível.')
    modulo = get_object_or_404(Modulo, numero=modulo_numero, ativo=True)
    par = get_object_or_404(
        modulo.comparacoes.select_related('palavra_base', 'palavra_comparada'),
        ordem=numero,
    )
    try:
        if not progresso.descoberta_pode_ser_acessada(request.user, par):
            raise progresso.ErroProgresso(
                'Conclua as Descobertas anteriores.', 'etapa_bloqueada', 409)
        estado = progresso.consultar_progresso(request.user, modulo.numero)
    except progresso.ErroProgresso as erro:
        return HttpResponse(str(erro), status=erro.status, content_type='text/plain; charset=utf-8')
    total = modulo.comparacoes.count()
    cards = []
    for palavra in (par.palavra_base, par.palavra_comparada):
        imagem = palavra.imagem.url if palavra.imagem else (
            palavra.imagem.storage.url(f'palavras/imagens/{palavra.palavra}.webp')
            if modulo_numero == 1 else '')
        cards.append({'palavra': palavra, 'imagem_url': imagem,
                      'acertada': palavra.pk in estado['palavras_acertadas']})
    return render(request, 'core/descoberta_modulo_1.html', {
        'cards': cards, 'numero': numero, 'total': total,
        'pronuncia_variantes': VARIANTES,
        'modulo': modulo, 'comparacao': par, 'percentual': estado['percentual'],
        'descoberta_concluida': par.pk in estado['comparacoes_concluidas'],
        'proxima': numero + 1 if numero < total else None,
        'etapas': range(1, total + 1), 'vogal': 'A' if modulo_numero == 1 else 'I',
        'proxima_url': (reverse('descoberta_modulo_1', args=[numero + 1]) if modulo_numero == 1
                        else reverse('descoberta_modulo', args=[modulo_numero, numero + 1]))
                       if numero < total else reverse(f'resumo_modulo_{modulo_numero}'),
    })


@login_required
def resumo_modulo(request, numero):
    resumo = RESUMOS.get(numero)
    if resumo is None:
        raise Http404('Resumo indisponível.')
    modulo = get_object_or_404(Modulo, numero=numero, ativo=True)
    try:
        if not progresso.resumo_pode_ser_acessado(request.user, numero):
            raise progresso.ErroProgresso(
                'Conclua todas as Descobertas antes de acessar o Resumo.', 'etapa_bloqueada', 409)
    except progresso.ErroProgresso as erro:
        return HttpResponse(str(erro), status=erro.status, content_type='text/plain; charset=utf-8')
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
@require_http_methods(['GET', 'POST'])
def conclusao_modulo_1(request):
    modulo = get_object_or_404(Modulo, numero=1, ativo=True)
    if request.method == 'POST':
        try:
            progresso.concluir_modulo(request.user, 1)
        except progresso.ErroProgresso as erro:
            return HttpResponse(str(erro), status=erro.status)
        destino = 'explicacao_modulo_2' if Modulo.objects.filter(
            numero=2, ativo=True, comparacoes__isnull=False).exists() else 'modulos'
        return redirect(destino)
    return render(request, 'core/conclusao_modulo_1.html', {'modulo': modulo})


@login_required
def explicacao_modulo_2(request):
    modulo = get_object_or_404(Modulo, numero=2, ativo=True)
    comparacoes = list(modulo.comparacoes.select_related('palavra_base', 'palavra_comparada').order_by('ordem'))
    if not comparacoes:
        raise Http404('Descobertas indisponíveis.')
    return render(request, 'core/explicacao_modulo.html', {
        'modulo': modulo, 'vogal': 'I', 'primeira': comparacoes[0], 'total': len(comparacoes),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def conclusao_modulo_2(request):
    modulo = get_object_or_404(Modulo, numero=2, ativo=True)
    try:
        if request.method == 'POST':
            progresso.concluir_modulo(request.user, 2)
            return redirect('conclusao_modulo_2')
        estado = progresso.consultar_progresso(request.user, 2)
        if estado['concluido_em'] is None or estado['primeira_pendente'] is not None:
            return HttpResponse('Conclua as Descobertas e finalize pelo Resumo.', status=409)
    except progresso.ErroProgresso as erro:
        return HttpResponse(str(erro), status=erro.status)
    return render(request, 'core/conclusao_modulo.html', {'modulo': modulo, 'total': estado['total_descobertas']})


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
        'pronuncia_variantes': VARIANTES,
    })
