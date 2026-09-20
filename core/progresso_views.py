"""API de progresso da Etapa 1; as páginas GET continuam independentes."""
import json

from django.contrib.auth.decorators import login_required
from django.db import OperationalError, connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from . import progresso


def _payload(request, campos):
    if request.content_type != 'application/json':
        raise progresso.ErroProgresso('Envie os dados no formato JSON.', 'formato_invalido', 415)
    try:
        dados = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        raise progresso.ErroProgresso('Os dados enviados são inválidos.')
    if not isinstance(dados, dict) or set(dados) != set(campos):
        raise progresso.ErroProgresso('Envie somente os campos necessários para esta ação.')
    for campo in ('comparacao_id', 'palavra_id'):
        if campo in dados and (type(dados[campo]) is not int or dados[campo] <= 0):
            raise progresso.ErroProgresso('Informe identificadores válidos.')
    return dados


def _responder(operacao):
    try:
        estado = operacao()
    except progresso.ErroProgresso as erro:
        return JsonResponse({'erro': erro.codigo, 'mensagem': str(erro)}, status=erro.status)
    except OperationalError as erro:
        # Não esconder outros erros do banco. Um bloqueio é recuperável pelo cliente.
        if connection.vendor != 'sqlite' or 'locked' not in str(erro).lower():
            raise
        resposta = JsonResponse({'erro': 'tente_novamente',
            'mensagem': 'Não foi possível salvar agora. Tente novamente.'}, status=503)
        resposta['Retry-After'] = '1'
        return resposta
    estado['modulo'] = estado['modulo'].numero
    pendente = estado.pop('primeira_pendente')
    estado['primeira_descoberta_pendente'] = pendente.ordem if pendente else None
    return JsonResponse(estado)


@login_required
@require_POST
@csrf_protect
def registrar_acerto(request, numero):
    def operacao():
        dados = _payload(request, ('comparacao_id', 'palavra_id', 'transcricao'))
        return progresso.registrar_acerto(request.user, numero, **dados)
    return _responder(operacao)


@login_required
@require_POST
@csrf_protect
def concluir_modulo(request, numero):
    def operacao():
        _payload(request, ())
        return progresso.concluir_modulo(request.user, numero)
    return _responder(operacao)
