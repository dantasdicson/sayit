import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import sleep
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import OperationalError, close_old_connections, connection
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from . import progresso as servico
from .models import Comparacao, Modulo, Palavra, Progresso, Sessao, Tentativa


def criar_catalogo():
    modulo = Modulo.objects.create(numero=1, ordem=1, titulo='Magic E', descricao='Teste')
    pares = []
    for ordem, textos in enumerate((('cat', 'cake'), ('cap', 'cape'), ('tap', 'tape'), ('mad', 'made')), 1):
        palavras = [Palavra.objects.create(modulo=modulo, palavra=texto, traducao=texto,
                    ordem=(ordem - 1) * 2 + pos) for pos, texto in enumerate(textos, 1)]
        pares.append(Comparacao.objects.create(modulo=modulo, ordem=ordem,
            palavra_base=palavras[0], palavra_comparada=palavras[1], explicacao='Teste'))
    return modulo, pares


class ProgressoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username='progresso_a', email='a@teste.com')
        cls.outro = get_user_model().objects.create_user(username='progresso_b', email='b@teste.com')
        cls.modulo, cls.pares = criar_catalogo()
        cls.outro_modulo = Modulo.objects.create(numero=2, ordem=2, titulo='Outro', descricao='Teste')
        cls.outra_palavra = Palavra.objects.create(modulo=cls.outro_modulo, palavra='kit', traducao='kit', ordem=1)

    def setUp(self):
        self.client.force_login(self.usuario)

    def acertar(self, etapa=0, pos=0, usuario=None, texto=None):
        par = self.pares[etapa]
        palavra = par.palavra_base if pos == 0 else par.palavra_comparada
        return servico.registrar_acerto(usuario or self.usuario, 1, par.pk, palavra.pk,
                                       palavra.palavra if texto is None else texto)

    def completar(self, total=4, usuario=None):
        for etapa in range(total):
            for pos in (0, 1):
                self.acertar(etapa, pos, usuario)

    def post_acerto(self, **campos):
        dados = {'comparacao_id': self.pares[0].pk, 'palavra_id': self.pares[0].palavra_base_id,
                 'transcricao': 'cat'}
        dados.update(campos)
        return self.client.post(reverse('registrar_acerto', args=[1]), dados, content_type='application/json')

    def post_conclusao(self):
        return self.client.post(reverse('concluir_modulo', args=[1]), {}, content_type='application/json')

    def test_primeiro_acerto_persiste_campos_minimos(self):
        resposta = self.post_acerto(transcricao=' CAT! ')
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()['acerto_criado'])
        tentativa = Tentativa.objects.get()
        self.assertEqual(tentativa.usuario, self.usuario)
        self.assertEqual(tentativa.resposta_reconhecida, 'cat')
        self.assertEqual(tentativa.resultado, 'correto')
        self.assertIsNone(tentativa.sessao)
        self.assertEqual(tentativa.pontuacao, 0)
        self.assertEqual(tentativa.feedback, '')
        self.assertIsNotNone(tentativa.data_hora)
        self.assertFalse(Sessao.objects.exists())

    def test_reenvio_nao_cria_nova_tentativa(self):
        self.post_acerto()
        resposta = self.post_acerto()
        self.assertFalse(resposta.json()['acerto_criado'])
        self.assertEqual(Tentativa.objects.count(), 1)
        self.assertEqual(resposta.json()['percentual'], 0)

    def test_cat_sozinho_nao_conclui(self):
        self.acertar()
        self.assertFalse(servico.descoberta_concluida(self.usuario, self.pares[0]))
        self.assertEqual(Progresso.objects.get().percentual, 0)

    def test_cat_e_cake_concluem(self):
        self.completar(1)
        self.assertTrue(servico.descoberta_concluida(self.usuario, self.pares[0]))

    def test_uma_descoberta_25(self):
        self.completar(1)
        self.assertEqual(Progresso.objects.get().percentual, 25)

    def test_duas_descobertas_50(self):
        self.completar(2)
        self.assertEqual(Progresso.objects.get().percentual, 50)

    def test_tres_descobertas_75(self):
        self.completar(3)
        self.assertEqual(Progresso.objects.get().percentual, 75)

    def test_quatro_descobertas_100(self):
        self.completar()
        self.assertEqual(Progresso.objects.get().percentual, 100)

    def test_100_nao_conclui_formalmente(self):
        self.completar()
        self.assertIsNone(Progresso.objects.get().concluido_em)
        self.assertEqual(servico.consultar_progresso(self.usuario)['estado'], 'EM_ANDAMENTO')

    def test_post_conclusao_preenche_data(self):
        self.completar()
        resposta = self.post_conclusao()
        self.assertEqual(resposta.status_code, 200)
        self.assertIsNotNone(Progresso.objects.get().concluido_em)
        self.assertEqual(resposta.json()['percentual'], 100)

    def test_conclusao_antecipada_recusada_sem_criar_progresso(self):
        self.assertEqual(self.post_conclusao().status_code, 409)
        self.assertFalse(Progresso.objects.exists())

    def test_anonimo_nao_registra_nem_conclui(self):
        self.client.logout()
        self.assertEqual(self.post_acerto().status_code, 302)
        self.assertEqual(self.post_conclusao().status_code, 302)
        self.assertFalse(Tentativa.objects.exists())
        self.assertFalse(Progresso.objects.exists())

    def test_servico_rejeita_anonimo(self):
        with self.assertRaises(servico.ErroProgresso):
            servico.obter_ou_criar_progresso(AnonymousUser())

    def test_palavra_de_outro_modulo_recusada(self):
        self.assertEqual(self.post_acerto(palavra_id=self.outra_palavra.pk).status_code, 404)
        self.assertFalse(Tentativa.objects.exists())

    def test_palavra_fora_comparacao_recusada(self):
        self.assertEqual(self.post_acerto(palavra_id=self.pares[1].palavra_base_id).status_code, 400)
        self.assertFalse(Tentativa.objects.exists())

    def test_etapa_fora_sequencia_recusada(self):
        resposta = self.post_acerto(comparacao_id=self.pares[3].pk,
            palavra_id=self.pares[3].palavra_base_id, transcricao='mad')
        self.assertEqual(resposta.status_code, 409)
        self.assertFalse(Tentativa.objects.exists())
        self.assertFalse(Progresso.objects.exists())

    def test_transcricao_incorreta_nao_grava(self):
        self.assertEqual(self.post_acerto(transcricao='dog').status_code, 400)
        self.assertFalse(Tentativa.objects.exists())
        self.assertFalse(Progresso.objects.exists())

    def test_conclusao_repetida_preserva_data(self):
        self.completar()
        self.post_conclusao()
        original = Progresso.objects.get().concluido_em
        self.post_conclusao()
        self.assertEqual(Progresso.objects.get().concluido_em, original)

    def test_registros_duplicados_nao_distorcem_percentual(self):
        self.completar(1)
        for _ in range(3):
            Tentativa.objects.create(usuario=self.usuario, palavra=self.pares[0].palavra_base,
                                     resultado='correto', resposta_reconhecida='cat')
        self.assertEqual(servico.recalcular_progresso(self.usuario).percentual, 25)
        self.assertEqual(servico.contar_descobertas_concluidas(self.usuario), 1)

    def test_outro_usuario_nao_recebe_acertos(self):
        self.completar(1)
        self.assertEqual(servico.consultar_acertos(self.outro, self.modulo), set())
        self.assertEqual(servico.consultar_progresso(self.outro)['percentual'], 0)
        self.assertFalse(servico.descoberta_pode_ser_acessada(self.outro, self.pares[1]))

    def test_usuario_id_injetado_recusado(self):
        self.assertEqual(self.post_acerto(usuario_id=self.outro.pk).status_code, 400)
        self.assertFalse(Tentativa.objects.exists())

    def test_endpoint_retorna_e_altera_somente_request_user(self):
        self.completar(1, self.outro)
        antes = Progresso.objects.get(usuario=self.outro).atualizado_em
        resposta = self.post_acerto()
        self.assertEqual(resposta.json()['percentual'], 0)
        self.assertEqual(resposta.json()['palavras_acertadas'], [self.pares[0].palavra_base_id])
        outro = Progresso.objects.get(usuario=self.outro)
        self.assertEqual(outro.percentual, 25)
        self.assertEqual(outro.atualizado_em, antes)

    def test_concluir_usuario_a_nao_conclui_usuario_b(self):
        self.completar()
        servico.obter_ou_criar_progresso(self.outro)
        self.post_conclusao()
        self.assertIsNone(Progresso.objects.get(usuario=self.outro).concluido_em)

    def test_nao_iniciado_consulta_sem_escrita(self):
        estado = servico.consultar_meu_progresso(self.usuario)[0]
        self.assertEqual(estado['estado'], 'NAO_INICIADO')
        self.assertEqual(estado['total_descobertas'], 4)
        self.assertEqual(estado['percentual'], 0)
        self.assertFalse(Progresso.objects.exists())

    def test_inicio_explicito_em_andamento(self):
        primeiro = servico.obter_ou_criar_progresso(self.usuario)
        segundo = servico.obter_ou_criar_progresso(self.usuario)
        self.assertEqual(primeiro.pk, segundo.pk)
        self.assertEqual(servico.consultar_progresso(self.usuario)['estado'], 'EM_ANDAMENTO')
        self.assertFalse(Tentativa.objects.exists())

    def test_estado_concluido(self):
        self.completar()
        servico.concluir_modulo(self.usuario)
        self.assertEqual(servico.consultar_meu_progresso(self.usuario)[0]['estado'], 'CONCLUIDO')

    def test_primeira_pendente_e_acessos(self):
        for etapa in range(4):
            self.assertEqual(servico.primeira_descoberta_pendente(self.usuario), self.pares[etapa])
            for indice, par in enumerate(self.pares):
                self.assertEqual(servico.descoberta_pode_ser_acessada(self.usuario, par), indice <= etapa)
            self.acertar(etapa, 0)
            self.assertEqual(servico.primeira_descoberta_pendente(self.usuario), self.pares[etapa])
            self.acertar(etapa, 1)
        self.assertIsNone(servico.primeira_descoberta_pendente(self.usuario))

    def test_resumo_bloqueado_antes_das_quatro(self):
        self.completar(3)
        self.assertFalse(servico.resumo_pode_ser_acessado(self.usuario))
        self.assertFalse(servico.modulo_pode_ser_concluido(self.usuario))

    def test_resumo_liberado_depois_das_quatro(self):
        self.completar()
        self.assertTrue(servico.resumo_pode_ser_acessado(self.usuario))
        self.assertTrue(servico.modulo_pode_ser_concluido(self.usuario))

    def test_normalizacao_casos_validos_javascript(self):
        for texto in ('cat', ' CAT! ', '“Cat.”', '[CAT]', '(cat)...', '\ufeffCAT\u00a0', 'C-A-T', '{cat}', 'cat\n\t'):
            with self.subTest(texto=texto):
                self.assertEqual(servico.normalizar_texto(texto), 'cat')
                self.assertEqual(self.post_acerto(transcricao=texto).status_code, 200)
        self.assertEqual(Tentativa.objects.count(), 1)

    def test_normalizacao_nao_aceita_outra_palavra(self):
        for texto in ('dog', 'cat cake', 'c at', '', '   ', '...', 'cat/', None, 12, []):
            with self.subTest(texto=texto):
                self.assertEqual(self.post_acerto(transcricao=texto).status_code, 400)
        self.assertFalse(Tentativa.objects.exists())

    def test_percentual_armazenado_nao_libera_conclusao(self):
        Progresso.objects.create(usuario=self.usuario, modulo=self.modulo, percentual=100)
        self.assertFalse(servico.resumo_pode_ser_acessado(self.usuario))
        self.assertEqual(self.post_conclusao().status_code, 409)
        self.assertIsNone(Progresso.objects.get().concluido_em)
        self.assertEqual(servico.recalcular_progresso(self.usuario).percentual, 0)

    def test_recalculo_nao_confia_no_percentual_armazenado(self):
        self.completar(2)
        Progresso.objects.update(percentual=0)
        self.assertEqual(servico.consultar_progresso(self.usuario)['percentual'], 50)
        self.assertEqual(servico.recalcular_progresso(self.usuario).percentual, 50)

    def test_csrf_obrigatorio_nos_dois_endpoints(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        for nome in ('registrar_acerto', 'concluir_modulo'):
            self.assertEqual(cliente.post(reverse(nome, args=[1]), {}, content_type='application/json').status_code, 403)
        cliente.get(reverse('home'))
        token = cliente.cookies['csrftoken'].value
        resposta = cliente.post(reverse('registrar_acerto', args=[1]), {
            'comparacao_id': self.pares[0].pk, 'palavra_id': self.pares[0].palavra_base_id,
            'transcricao': 'cat'}, content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(resposta.status_code, 200)

    def test_endpoints_recusam_get(self):
        for nome in ('registrar_acerto', 'concluir_modulo'):
            self.assertEqual(self.client.get(reverse(nome, args=[1])).status_code, 405)
        self.assertFalse(Progresso.objects.exists())

    def test_paginas_get_nao_gravam_e_preservam_fluxo_etapa_1(self):
        for nome, args in [('explicacao_modulo_1', []), ('descoberta_modulo_1', [4]),
                           ('resumo_modulo_1', []), ('conclusao_modulo_1', [])]:
            self.assertEqual(self.client.get(reverse(nome, args=args)).status_code, 200)
        self.assertFalse(Progresso.objects.exists())
        self.assertFalse(Tentativa.objects.exists())

    def test_modulo_inativo_ou_inexistente(self):
        self.modulo.ativo = False
        self.modulo.save(update_fields=['ativo'])
        self.assertEqual(self.post_acerto().status_code, 404)
        self.assertEqual(self.post_conclusao().status_code, 404)
        self.assertEqual(self.client.post(reverse('concluir_modulo', args=[999]), {}, content_type='application/json').status_code, 404)

    def test_comparacao_e_palavra_inexistentes(self):
        self.assertEqual(self.post_acerto(comparacao_id=999999).status_code, 404)
        self.assertEqual(self.post_acerto(palavra_id=999999).status_code, 404)

    def test_comparacao_de_outro_modulo(self):
        outra = Palavra.objects.create(modulo=self.outro_modulo, palavra='kite', traducao='kite', ordem=2)
        par = Comparacao.objects.create(modulo=self.outro_modulo, palavra_base=self.outra_palavra,
            palavra_comparada=outra, ordem=1)
        self.assertEqual(self.post_acerto(comparacao_id=par.pk).status_code, 404)

    def test_catalogo_inconsistente_nao_depende_de_clean(self):
        Comparacao.objects.filter(pk=self.pares[0].pk).update(palavra_base=self.outra_palavra)
        self.assertEqual(self.post_acerto().status_code, 409)
        self.assertFalse(Tentativa.objects.exists())

    def test_catalogo_incompleto_nao_conclui_com_menos_etapas(self):
        self.completar(3)
        self.pares[3].delete()
        self.assertEqual(self.post_conclusao().status_code, 409)
        self.assertIsNone(Progresso.objects.get().concluido_em)

    def test_palavra_inativa_recusada(self):
        Palavra.objects.filter(pk=self.pares[0].palavra_base_id).update(ativa=False)
        self.assertEqual(self.post_acerto().status_code, 409)

    def test_payloads_invalidos_e_resultados_fabricados(self):
        for dados in ({}, [], None, {'usuario_id': self.outro.pk}):
            resposta = self.client.post(reverse('registrar_acerto', args=[1]), json.dumps(dados), content_type='application/json')
            self.assertEqual(resposta.status_code, 400)
        for campo in ('correto', 'percentual', 'descoberta_concluida'):
            self.assertEqual(self.post_acerto(**{campo: True}).status_code, 400)
        for valor in (True, 1.5, '1', -1, None):
            self.assertEqual(self.post_acerto(palavra_id=valor).status_code, 400)
        self.assertEqual(self.post_acerto(transcricao='x' * 256).status_code, 400)
        self.assertFalse(Progresso.objects.exists())

    def test_json_malformado_ou_content_type_errado(self):
        url = reverse('registrar_acerto', args=[1])
        self.assertEqual(self.client.post(url, '{', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post(url, {}).status_code, 415)

    def test_conclusao_nao_aceita_usuario_ou_percentual(self):
        self.completar()
        resposta = self.client.post(reverse('concluir_modulo', args=[1]),
            {'usuario_id': self.outro.pk, 'percentual': 100}, content_type='application/json')
        self.assertEqual(resposta.status_code, 400)
        self.assertIsNone(Progresso.objects.get().concluido_em)

    def test_falha_no_progresso_desfaz_tentativa(self):
        with patch.object(Progresso, 'save', side_effect=RuntimeError('falha simulada')):
            with self.assertRaises(RuntimeError):
                self.acertar()
        self.assertFalse(Tentativa.objects.exists())
        self.assertFalse(Progresso.objects.exists())

    def test_bloqueio_sqlite_resposta_repetivel(self):
        with patch.object(servico, 'registrar_acerto', side_effect=OperationalError('database is locked')):
            resposta = self.post_acerto()
        self.assertEqual(resposta.status_code, 503)
        self.assertEqual(resposta['Retry-After'], '1')

    def test_resposta_repetida_apos_conclusao_nao_regride(self):
        self.completar()
        self.post_conclusao()
        data = Progresso.objects.get().concluido_em
        resposta = self.post_acerto()
        self.assertEqual(resposta.json()['percentual'], 100)
        self.assertFalse(resposta.json()['acerto_criado'])
        self.assertEqual(Progresso.objects.get().concluido_em, data)

    def test_acerto_consultado_e_isolado_por_palavra(self):
        self.acertar()
        self.assertTrue(servico.palavra_ja_acertada(self.usuario, self.pares[0].palavra_base))
        self.assertFalse(servico.palavra_ja_acertada(self.usuario, self.pares[0].palavra_comparada))

    def test_tentativas_incorretas_legadas_nao_contam(self):
        for resultado in ('incorreto', 'nao_reconhecido'):
            Tentativa.objects.create(usuario=self.usuario, palavra=self.pares[0].palavra_base, resultado=resultado)
        self.assertEqual(servico.consultar_acertos(self.usuario, self.modulo), set())
        self.assertFalse(servico.descoberta_concluida(self.usuario, self.pares[0]))


class ConcorrenciaProgressoTests(TransactionTestCase):
    def test_reenvios_simultaneos_sqlite_nao_duplicam(self):
        if connection.vendor != 'sqlite':
            self.skipTest('Verificação específica do banco SQLite utilizado pelo projeto.')
        usuario = get_user_model().objects.create_user(username='concorrente', email='concorrente@teste.com')
        _, pares = criar_catalogo()
        barreira = Barrier(2)

        def enviar():
            close_old_connections()
            try:
                aluno = get_user_model().objects.get(pk=usuario.pk)
                barreira.wait(timeout=10)
                for _ in range(40):
                    try:
                        return servico.registrar_acerto(aluno, 1, pares[0].pk, pares[0].palavra_base_id, 'cat')
                    except OperationalError as erro:
                        if 'locked' not in str(erro).lower():
                            raise
                        # Mesmo contrato de reenvio usado por um cliente após HTTP 503.
                        sleep(.025)
                raise AssertionError('Banco permaneceu bloqueado')
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(lambda _: enviar(), range(2)))
        self.assertEqual(sorted(r['acerto_criado'] for r in resultados), [False, True])
        self.assertEqual(Tentativa.objects.count(), 1)
        self.assertEqual(Progresso.objects.get().percentual, 0)
