import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core import progresso
from core.models import Modulo, Tentativa


class BloqueioSequencialModulosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())
        cls.usuario = get_user_model().objects.create_user(username='sequencial')

    def setUp(self):
        self.client.force_login(self.usuario)

    def concluir(self, numero):
        modulo = Modulo.objects.get(numero=numero)
        for comparacao in modulo.comparacoes.order_by('ordem'):
            for palavra in (comparacao.palavra_base, comparacao.palavra_comparada):
                progresso.registrar_acerto(
                    self.usuario, numero, comparacao.pk, palavra.pk, palavra.palavra)
        progresso.concluir_modulo(self.usuario, numero)

    def test_trilha_e_dashboard_exibem_modulos_posteriores_bloqueados(self):
        trilha = self.client.get(reverse('trilha'))
        painel = self.client.get(reverse('modulos'))
        self.assertContains(trilha, 'Conclua o módulo anterior', count=9)
        self.assertContains(painel, 'Bloqueado — conclua o módulo anterior', count=9)
        self.assertFalse(painel.context['modulos_estado'][0]['bloqueado'])
        self.assertTrue(painel.context['modulos_estado'][1]['bloqueado'])

    def test_url_manual_de_modulo_bloqueado_retorna_409(self):
        resposta = self.client.get(reverse('explicacao_modulo_2'))
        self.assertEqual(resposta.status_code, 409)
        self.assertContains(
            resposta, 'Conclua os módulos anteriores para continuar.',
            status_code=409,
        )

    def test_api_nao_permite_gravar_modulo_bloqueado(self):
        comparacao = Modulo.objects.get(numero=2).comparacoes.order_by('ordem').first()
        resposta = self.client.post(
            reverse('registrar_acerto', args=[2]),
            data=json.dumps({
                'comparacao_id': comparacao.pk,
                'palavra_id': comparacao.palavra_base_id,
                'transcricao': comparacao.palavra_base.palavra,
            }),
            content_type='application/json',
        )
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(resposta.json()['erro'], 'modulo_bloqueado')
        self.assertFalse(Tentativa.objects.filter(palavra__modulo__numero=2).exists())

    def test_concluir_anterior_libera_somente_o_modulo_seguinte(self):
        self.concluir(1)
        self.assertEqual(self.client.get(reverse('explicacao_modulo_2')).status_code, 200)
        self.assertEqual(self.client.get(reverse('explicacao_modulo_3')).status_code, 409)
        painel = self.client.get(reverse('modulos'))
        self.assertFalse(painel.context['modulos_estado'][1]['bloqueado'])
        self.assertTrue(painel.context['modulos_estado'][2]['bloqueado'])
