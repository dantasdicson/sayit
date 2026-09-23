from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core import progresso
from core.models import Modulo


class AreaDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())
        cls.usuario = get_user_model().objects.create_user(username='painel')

    def setUp(self):
        self.client.force_login(self.usuario)

    def concluir_primeiro_modulo(self):
        modulo = Modulo.objects.get(numero=1)
        for comparacao in modulo.comparacoes.all():
            for palavra in (comparacao.palavra_base, comparacao.palavra_comparada):
                progresso.registrar_acerto(
                    self.usuario, 1, comparacao.pk, palavra.pk, palavra.palavra)
        progresso.concluir_modulo(self.usuario, 1)

    def test_trilha_e_dashboard_tem_finalidades_diferentes(self):
        trilha = self.client.get(reverse('trilha'))
        modulos = self.client.get(reverse('modulos'))
        self.assertContains(trilha, 'Sua trilha de aprendizagem', html=False)
        self.assertContains(trilha, 'Siga o caminho na ordem')
        self.assertNotContains(trilha, 'VISÃO GERAL')
        self.assertContains(modulos, 'VISÃO GERAL')
        self.assertContains(modulos, '0% do curso concluído')
        self.assertContains(modulos, 'PRÓXIMO PASSO')
        self.assertNotContains(modulos, 'Sua trilha de aprendizagem', html=False)

    def test_dashboard_calcula_percentual_e_status_persistidos(self):
        self.concluir_primeiro_modulo()
        resposta = self.client.get(reverse('modulos'))
        self.assertEqual(resposta.context['percentual_curso'], 11)
        self.assertEqual(resposta.context['modulos_concluidos'], 1)
        self.assertEqual(resposta.context['total_modulos'], 9)
        self.assertEqual(resposta.context['proximo_modulo']['modulo'].numero, 2)
        self.assertContains(resposta, '11% do curso concluído')
        self.assertContains(resposta, '1 de 9 módulos finalizados')

    def test_meu_progresso_exibe_metricas_reais(self):
        modulo = Modulo.objects.get(numero=1)
        comparacao = modulo.comparacoes.first()
        progresso.registrar_acerto(
            self.usuario, 1, comparacao.pk,
            comparacao.palavra_base_id, comparacao.palavra_base.palavra)
        resposta = self.client.get(reverse('progresso'))
        self.assertContains(resposta, 'Palavras praticadas')
        self.assertContains(resposta, 'Acertos registrados')
        self.assertContains(resposta, 'Conquistas por módulo')
        self.assertEqual(resposta.context['palavras_praticadas'], 1)
        self.assertEqual(resposta.context['total_tentativas'], 1)
        self.assertNotContains(resposta, 'estará disponível em breve')

    def test_consultas_do_painel_nao_criam_progresso(self):
        for nome in ('trilha', 'modulos', 'progresso'):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 200)
        self.assertFalse(self.usuario.progressos.exists())
