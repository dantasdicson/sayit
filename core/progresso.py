"""Persistência das Descobertas; não registra áudio nem eventos da Prática.

Tentativa não possui origem/comparação: nesta etapa somente este serviço deve
registrar acertos pedagógicos. Os catálogos habilitados são os Módulos 1 e 2.
"""
import re
from contextlib import contextmanager

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Modulo, Palavra, Progresso, Tentativa
from .pronuncia import corresponde

DESCOBERTAS_POR_MODULO = {1: 4, 2: 3}


class ErroProgresso(Exception):
    def __init__(self, mensagem, codigo='dados_invalidos', status=400):
        super().__init__(mensagem)
        self.codigo = codigo
        self.status = status


def normalizar_texto(texto):
    """Mesma pontuação e whitespace do normalize em descobertas_microfone.js."""
    if not isinstance(texto, str):
        raise ErroProgresso('Informe uma transcrição em texto.')
    texto = re.sub(r'''[.,!?;:"'“”‘’…()\[\]{}-]''', '', texto.lower())
    return re.sub(r'[\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+', ' ', texto).strip(' ')


def _validar_usuario(usuario):
    if not usuario.is_authenticated or not usuario.pk or not usuario.is_active:
        raise ErroProgresso('Entre na sua conta para continuar.', 'autenticacao', 403)


def _catalogo(numero):
    # Não habilitar progresso de módulos cuja experiência ainda não existe.
    if numero not in DESCOBERTAS_POR_MODULO:
        raise ErroProgresso('Módulo indisponível.', 'modulo_inexistente', 404)
    try:
        modulo = Modulo.objects.get(numero=numero, ativo=True)
    except Modulo.DoesNotExist:
        raise ErroProgresso('Módulo indisponível.', 'modulo_inexistente', 404)
    comparacoes = list(modulo.comparacoes.select_related(
        'palavra_base', 'palavra_comparada').order_by('ordem', 'pk'))
    if [c.ordem for c in comparacoes] != list(range(1, DESCOBERTAS_POR_MODULO[numero] + 1)) or any(
        c.palavra_base_id == c.palavra_comparada_id
        or c.palavra_base.modulo_id != modulo.pk
        or c.palavra_comparada.modulo_id != modulo.pk
        or not c.palavra_base.ativa or not c.palavra_comparada.ativa
        for c in comparacoes
    ):
        raise ErroProgresso('As Descobertas estão indisponíveis no momento.', 'catalogo_invalido', 409)
    return modulo, comparacoes


@contextmanager
def _escrita(usuario, numero):
    _validar_usuario(usuario)
    if numero not in DESCOBERTAS_POR_MODULO:
        raise ErroProgresso('Módulo indisponível.', 'modulo_inexistente', 404)
    with transaction.atomic():
        # PRIMEIRA consulta da transação é uma escrita sem mudança de valor.
        # SQLite adquire o bloqueio de escrita antes de lermos tentativas; duas
        # requisições não podem ler "ainda não existe" e inserir simultaneamente.
        # Também serializa pelo módulo em bancos com bloqueio de linha.
        if not Modulo.objects.filter(numero=numero, ativo=True).update(numero=F('numero')):
            raise ErroProgresso('Módulo indisponível.', 'modulo_inexistente', 404)
        yield _catalogo(numero)


def consultar_acertos(usuario, modulo):
    _validar_usuario(usuario)
    return set(Tentativa.objects.filter(
        usuario=usuario, palavra__modulo=modulo,
        resultado=Tentativa.Resultado.CORRETO,
    ).order_by().values_list('palavra_id', flat=True).distinct())


def palavra_ja_acertada(usuario, palavra):
    return palavra.pk in consultar_acertos(usuario, palavra.modulo)


def _completa(comparacao, acertos):
    return {comparacao.palavra_base_id, comparacao.palavra_comparada_id} <= acertos


def descoberta_concluida(usuario, comparacao):
    _, comparacoes = _catalogo(comparacao.modulo.numero)
    atual = next((c for c in comparacoes if c.pk == comparacao.pk), None)
    return bool(atual and _completa(atual, consultar_acertos(usuario, atual.modulo)))


def calcular_percentual(concluidas, total):
    if total <= 0:
        return 0
    return min(100, max(0, concluidas * 100 // total))


def _estado(usuario, modulo, comparacoes):
    acertos = consultar_acertos(usuario, modulo)
    concluidas = [c for c in comparacoes if _completa(c, acertos)]
    pendente = next((c for c in comparacoes if not _completa(c, acertos)), None)
    progresso = Progresso.objects.filter(usuario=usuario, modulo=modulo).first()
    return {
        'modulo': modulo, 'percentual': calcular_percentual(len(concluidas), len(comparacoes)),
        'descobertas_concluidas': len(concluidas), 'total_descobertas': len(comparacoes),
        'comparacoes_concluidas': [c.pk for c in concluidas], 'palavras_acertadas': sorted(acertos),
        'primeira_pendente': pendente,
        'estado': 'NAO_INICIADO' if progresso is None else (
            'CONCLUIDO' if progresso.concluido_em else 'EM_ANDAMENTO'),
        'concluido_em': progresso.concluido_em if progresso else None,
    }


def consultar_progresso(usuario, numero=1):
    _validar_usuario(usuario)
    return _estado(usuario, *_catalogo(numero))


def consultar_meu_progresso(usuario):
    """Somente módulos implementados; consulta nunca cria registros."""
    _validar_usuario(usuario)
    return [consultar_progresso(usuario, m.numero)
            for m in Modulo.objects.filter(numero__in=DESCOBERTAS_POR_MODULO, ativo=True)]


def contar_descobertas_concluidas(usuario, numero=1):
    return consultar_progresso(usuario, numero)['descobertas_concluidas']


def primeira_descoberta_pendente(usuario, numero=1):
    return consultar_progresso(usuario, numero)['primeira_pendente']


def _permitida(comparacao, comparacoes, acertos):
    return all(_completa(c, acertos) for c in comparacoes if c.ordem < comparacao.ordem)


def descoberta_pode_ser_acessada(usuario, comparacao):
    modulo, comparacoes = _catalogo(comparacao.modulo.numero)
    atual = next((c for c in comparacoes if c.pk == comparacao.pk), None)
    return bool(atual and _permitida(atual, comparacoes, consultar_acertos(usuario, modulo)))


def resumo_pode_ser_acessado(usuario, numero=1):
    estado = consultar_progresso(usuario, numero)
    return estado['total_descobertas'] > 0 and estado['primeira_pendente'] is None


def modulo_pode_ser_concluido(usuario, numero=1):
    return resumo_pode_ser_acessado(usuario, numero)


def _recalcular(usuario, modulo, comparacoes):
    estado = _estado(usuario, modulo, comparacoes)
    progresso, _ = Progresso.objects.get_or_create(usuario=usuario, modulo=modulo)
    progresso.percentual = estado['percentual']
    progresso.save(update_fields=['percentual', 'atualizado_em'])
    return progresso


def obter_ou_criar_progresso(usuario, numero=1):
    """Ação explícita de início, reservada ao futuro botão da Etapa 2."""
    with _escrita(usuario, numero) as (modulo, comparacoes):
        return _recalcular(usuario, modulo, comparacoes)


def recalcular_progresso(usuario, numero=1):
    with _escrita(usuario, numero) as (modulo, comparacoes):
        return _recalcular(usuario, modulo, comparacoes)


def registrar_acerto(usuario, numero, comparacao_id, palavra_id, transcricao):
    if not isinstance(transcricao, str) or len(transcricao) > 255:
        raise ErroProgresso('Informe uma transcrição de até 255 caracteres.')
    texto = normalizar_texto(transcricao)
    with _escrita(usuario, numero) as (modulo, comparacoes):
        comparacao = next((c for c in comparacoes if c.pk == comparacao_id), None)
        if comparacao is None:
            raise ErroProgresso('Descoberta não encontrada neste módulo.', 'comparacao_invalida', 404)
        palavra = Palavra.objects.filter(pk=palavra_id, modulo=modulo, ativa=True).first()
        if palavra is None:
            raise ErroProgresso('Palavra não encontrada neste módulo.', 'palavra_invalida', 404)
        if palavra.pk not in (comparacao.palavra_base_id, comparacao.palavra_comparada_id):
            raise ErroProgresso('Esta palavra não pertence à Descoberta.', 'palavra_fora_comparacao')
        acertos = consultar_acertos(usuario, modulo)
        if not _permitida(comparacao, comparacoes, acertos):
            raise ErroProgresso('Conclua as Descobertas anteriores.', 'etapa_bloqueada', 409)
        if not corresponde(normalizar_texto(palavra.palavra), texto):
            raise ErroProgresso('A palavra reconhecida não corresponde à esperada.', 'transcricao_incorreta')
        criado = palavra.pk not in acertos
        if criado:
            Tentativa.objects.create(usuario=usuario, palavra=palavra,
                resultado=Tentativa.Resultado.CORRETO, resposta_reconhecida=texto,
                sessao=None, pontuacao=0, feedback='')
        _recalcular(usuario, modulo, comparacoes)
        return {**_estado(usuario, modulo, comparacoes), 'acerto_criado': criado}


def concluir_modulo(usuario, numero=1):
    with _escrita(usuario, numero) as (modulo, comparacoes):
        estado = _estado(usuario, modulo, comparacoes)
        if estado['primeira_pendente'] is not None:
            raise ErroProgresso('Conclua todas as Descobertas antes de finalizar o módulo.', 'modulo_incompleto', 409)
        progresso = _recalcular(usuario, modulo, comparacoes)
        if progresso.concluido_em is None:
            progresso.concluido_em = timezone.now()
            progresso.save(update_fields=['concluido_em', 'atualizado_em'])
        return _estado(usuario, modulo, comparacoes)
