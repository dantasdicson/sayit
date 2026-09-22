from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core import progresso
from core.models import Modulo


class ContinuacaoModulosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())
        cls.usuario = get_user_model().objects.create_user(username='continuacao')

    def setUp(self):
        self.client.force_login(self.usuario)

    def concluir(self, numero):
        for par in Modulo.objects.get(numero=numero).comparacoes.all():
            for palavra in (par.palavra_base, par.palavra_comparada):
                progresso.registrar_acerto(self.usuario, numero, par.pk, palavra.pk, palavra.palavra)
        return self.client.post(reverse(f'conclusao_modulo_{numero}'), follow=True)

    def test_conclusao_oferece_proximo_modulo_e_destino_abre(self):
        for numero in (2, 3, 4, 5, 6, 7):
            with self.subTest(numero=numero):
                resposta = self.concluir(numero)
                destino = reverse(f'explicacao_modulo_{numero + 1}')
                self.assertContains(resposta, f'href="{destino}"')
                self.assertContains(resposta, 'Continuar para o próximo módulo')
                self.assertEqual(self.client.get(destino).status_code, 200)

    def test_ultimo_modulo_implementado_volta_a_trilha(self):
        resposta = self.concluir(8)
        self.assertContains(resposta, f'href="{reverse("trilha")}"')
        self.assertContains(resposta, 'Continuar para o próximo módulo')
        self.assertContains(resposta, 'O próximo módulo estará disponível em breve.')

    def test_modulo_seguinte_inativo_ou_incompleto_nao_oferece_link(self):
        Modulo.objects.filter(numero=4).update(ativo=False)
        self.assertNotContains(self.concluir(3), 'Continuar para o próximo módulo')
        Modulo.objects.filter(numero=4).update(ativo=True)
        Modulo.objects.get(numero=4).comparacoes.first().delete()
        self.assertNotContains(self.client.get(reverse('conclusao_modulo_3')), 'Continuar para o próximo módulo')

    def test_incompleto_nao_acessa_conclusao(self):
        self.assertEqual(self.client.get(reverse('conclusao_modulo_3')).status_code, 409)
        self.assertEqual(self.client.post(reverse('conclusao_modulo_3')).status_code, 409)
