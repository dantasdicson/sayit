import random
from django.contrib.auth.decorators import login_required
from django.db import OperationalError, connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods
from . import desafio_service as service
from . import progresso
from .desafio_config import DESAFIOS, NOTA_MINIMA
from .models import Palavra, Progresso
from .progresso_views import _payload


def _erro(erro):
    return HttpResponse(str(erro), status=erro.status, content_type='text/plain; charset=utf-8')


@login_required
@never_cache
def introducao(request):
    try:
        progresso.exigir_modulo_desbloqueado(request.user, 10)
        estado = service.consultar(request.user)
    except progresso.ErroProgresso as erro:
        return _erro(erro)
    return render(request, 'core/desafio/introducao.html', {
        'estado': estado, 'desafios': DESAFIOS, 'inicio': estado['pendente'] or 1})


@login_required
@never_cache
def desafio(request, numero):
    try:
        config = service.exigir(request.user, numero)
        estado = service.consultar(request.user)
    except progresso.ErroProgresso as erro:
        return _erro(erro)
    palavras = list(enumerate(config.palavras))
    random.SystemRandom().shuffle(palavras)
    if [p for _, p in palavras] == config.palavras:
        palavras = palavras[1:] + palavras[:1]
    audios = []
    for palavra in config.importantes:
        candidatos = Palavra.objects.filter(palavra=palavra, ativa=True).exclude(audio='').order_by('modulo__numero')
        for registro in candidatos:
            if registro.audio.storage.exists(registro.audio.name):
                audios.append({'palavra': palavra, 'url': registro.audio.url})
                break
    atual = estado['desafios'][numero - 1]
    proxima_url = reverse('desafio_modulo_10', args=[numero + 1]) if numero < len(DESAFIOS) else reverse('resumo_modulo_10')
    return render(request, 'core/desafio/atividade.html', {
        'config': config, 'atual': atual, 'audios': audios, 'palavras': palavras,
        'total': len(DESAFIOS), 'proxima_url': proxima_url,
        'dados': {'numero': numero, 'palavras': config.palavras,
                  'montagemUrl': reverse('montar_desafio_10', args=[numero]),
                  'avaliacaoUrl': reverse('avaliar_desafio_10', args=[numero]),
                  'proximaUrl': proxima_url, 'aprovado': atual['concluido'],
                  'minimo': NOTA_MINIMA, 'melhor': atual['melhor']},
    })


def _api(operacao):
    try:
        return JsonResponse(operacao())
    except progresso.ErroProgresso as erro:
        return JsonResponse({'mensagem': str(erro), 'erro': erro.codigo}, status=erro.status)
    except OperationalError as erro:
        if connection.vendor != 'sqlite' or 'locked' not in str(erro).lower():
            raise
        return JsonResponse({'mensagem': 'Não foi possível salvar agora. Tente novamente.'}, status=503)


@login_required
@require_POST
def montar(request, numero):
    def operacao():
        dados = _payload(request, ('palavras',))
        return {'token': service.montar(request.user, numero, dados['palavras'])}
    return _api(operacao)


@login_required
@require_POST
def avaliar(request, numero):
    def operacao():
        dados = _payload(request, ('token', 'transcricao'))
        avaliacao, estado = service.registrar(request.user, numero, **dados)
        return {'avaliacao': avaliacao, 'melhor': estado['desafios'][numero - 1]['melhor'],
                'liberado': estado['desafios'][numero - 1]['concluido'],
                'concluidos': estado['concluidos'], 'final': estado['final']}
    return _api(operacao)


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def resultado(request, encerramento=False):
    try:
        service.concluir(request.user)
        estado = service.consultar(request.user)
    except progresso.ErroProgresso as erro:
        return _erro(erro)
    return render(request, 'core/desafio/resultado.html', {
        'estado': estado, 'encerramento': encerramento,
        'estrelas': '★' * estado['estrelas'] + '☆' * (5 - estado['estrelas']),
        'modulos_concluidos': Progresso.objects.filter(usuario=request.user,
            modulo__numero__range=(1, 10), concluido_em__isnull=False).count(),
    })
