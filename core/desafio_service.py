"""Módulo 10: montagem validada no servidor, tentativas e Progresso existente."""
import uuid
from django.core import signing
from django.core.signing import loads as load_ticket
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from . import progresso
from .models import Modulo, Progresso, TentativaDesafio
from .desafio_config import DESAFIOS, NOTA_MINIMA, VERSAO
from .desafio_avaliacao import avaliar, arredondar, estrelas, faixa

SALT = 'sayit-desafio-montagem'


def configuracao(numero):
    desafio = next((d for d in DESAFIOS if d.numero == numero), None)
    if desafio is None:
        raise progresso.ErroProgresso('Desafio indisponível.', 'desafio_inexistente', 404)
    return desafio


def consultar(usuario):
    progresso._validar_usuario(usuario)
    try:
        modulo = Modulo.objects.get(numero=10, ativo=True)
    except Modulo.DoesNotExist:
        raise progresso.ErroProgresso('Módulo indisponível.', 'modulo_inexistente', 404)
    tentativas = list(TentativaDesafio.objects.filter(usuario=usuario, modulo=modulo, versao=VERSAO))
    desafios = []
    for d in DESAFIOS:
        historico = [t for t in tentativas if t.desafio == d.numero]
        melhor = max((t.nota for t in historico), default=0)
        desafios.append({'numero': d.numero, 'frase': d.frase, 'melhor': melhor,
                         'concluido': melhor >= NOTA_MINIMA, 'historico': historico,
                         'conteudos': d.conteudos})
    concluidos = sum(d['concluido'] for d in desafios)
    pendente = next((d['numero'] for d in desafios if not d['concluido']), None)
    registro = Progresso.objects.filter(usuario=usuario, modulo=modulo).first()
    final = arredondar(sum(d['melhor'] for d in desafios) / len(desafios)) if pendente is None else None
    return {
        'modulo': modulo, 'desafios': desafios, 'concluidos': concluidos, 'pendente': pendente,
        'final': final, 'melhor': max((d['melhor'] for d in desafios), default=0),
        'estrelas': estrelas(final) if final is not None else 0,
        'feedback': faixa(final)[1] if final is not None else '',
        'legado': bool(registro and registro.concluido_em and pendente is not None),
        # Conclusões antigas não são apagadas nem recebem notas fictícias.
        'percentual': 100 if registro and registro.concluido_em else concluidos * 100 // len(DESAFIOS),
        'concluido_em': registro.concluido_em if registro else None,
        'conteudos': list(dict.fromkeys(c for d in DESAFIOS for c in d.conteudos)),
    }


def exigir(usuario, numero):
    progresso.exigir_modulo_desbloqueado(usuario, 10)
    desafio = configuracao(numero)
    estado = consultar(usuario)
    if any(not d['concluido'] for d in estado['desafios'] if d['numero'] < numero):
        raise progresso.ErroProgresso('Complete o desafio anterior com pelo menos 70 pontos.', 'etapa_bloqueada', 409)
    return desafio


def montar(usuario, numero, palavras):
    desafio = exigir(usuario, numero)
    if (not isinstance(palavras, list) or len(palavras) != len(desafio.palavras)
            or any(not isinstance(p, str) or len(p) > 50 for p in palavras)
            or [progresso.normalizar_texto(p) for p in palavras] !=
               [progresso.normalizar_texto(p) for p in desafio.palavras]):
        raise progresso.ErroProgresso('Vamos organizar de outro jeito? Confira a ordem das palavras.', 'montagem_incorreta')
    return signing.dumps({'usuario': usuario.pk, 'desafio': numero, 'versao': VERSAO,
                          'requisicao': str(uuid.uuid4())}, salt=SALT)


def _atualizar(usuario, estado):
    registro, _ = Progresso.objects.get_or_create(usuario=usuario, modulo=estado['modulo'])
    registro.percentual = 100 if registro.concluido_em else estado['percentual']
    if estado['pendente'] is None and registro.concluido_em is None:
        registro.concluido_em = timezone.now()
    registro.save(update_fields=['percentual', 'concluido_em', 'atualizado_em'])


def registrar(usuario, numero, token, transcricao):
    if not isinstance(token, str) or len(token) > 2048:
        raise progresso.ErroProgresso('Monte a frase antes de falar.', 'montagem_necessaria', 409)
    if not isinstance(transcricao, str) or len(transcricao) > 255:
        raise progresso.ErroProgresso('A fala reconhecida deve ter até 255 caracteres.')
    try:
        dados = load_ticket(token, salt=SALT, max_age=900)
        if (dados['usuario'], dados['desafio'], dados['versao']) != (usuario.pk, numero, VERSAO):
            raise ValueError()
        requisicao = uuid.UUID(dados['requisicao'])
    except (signing.BadSignature, ValueError, KeyError, TypeError):
        raise progresso.ErroProgresso('Monte a frase novamente para liberar o microfone.', 'montagem_expirada', 409)
    with transaction.atomic():
        # Mesmo mecanismo de serialização SQLite usado no progresso das palavras.
        Modulo.objects.filter(numero=10, ativo=True).update(numero=F('numero'))
        desafio = exigir(usuario, numero)
        antiga = TentativaDesafio.objects.filter(requisicao=requisicao, usuario=usuario).first()
        if antiga:
            if antiga.transcricao != transcricao:
                raise progresso.ErroProgresso('Esta tentativa já foi avaliada. Inicie outra.', 'tentativa_repetida', 409)
            return antiga.avaliacao, consultar(usuario)
        avaliacao = avaliar(desafio.frase, transcricao, desafio.importantes)
        TentativaDesafio.objects.create(usuario=usuario, modulo=Modulo.objects.get(numero=10),
            desafio=numero, versao=VERSAO, requisicao=requisicao, frase=desafio.frase,
            transcricao=transcricao, nota=avaliacao['nota'], avaliacao=avaliacao)
        estado = consultar(usuario)
        _atualizar(usuario, estado)
        return avaliacao, consultar(usuario)


def estado_progresso(usuario):
    estado = consultar(usuario)
    return {
        'modulo': estado['modulo'], 'percentual': estado['percentual'],
        'descobertas_concluidas': estado['concluidos'], 'total_descobertas': len(DESAFIOS),
        'comparacoes_concluidas': [], 'palavras_acertadas': [], 'primeira_pendente': None,
        'estado': 'CONCLUIDO' if estado['concluido_em'] else (
            'EM_ANDAMENTO' if any(d['historico'] for d in estado['desafios']) else 'NAO_INICIADO'),
        'concluido_em': estado['concluido_em'],
    }


def concluir(usuario):
    progresso.exigir_modulo_desbloqueado(usuario, 10)
    estado = consultar(usuario)
    if estado['pendente'] is not None:
        raise progresso.ErroProgresso('Complete os três desafios com pelo menos 70 pontos.', 'modulo_incompleto', 409)
    # A terceira avaliação já persistiu a conclusão. GETs não escrevem.
    return estado_progresso(usuario)
