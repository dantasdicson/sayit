from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import Modulo, Progresso


class Modulo4Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())
        cls.usuario = get_user_model().objects.create_user(username='modulo4', email='m4@test.com')
        cls.modulo = Modulo.objects.get(numero=4)
        cls.pares = list(cls.modulo.comparacoes.select_related('palavra_base', 'palavra_comparada').order_by('ordem'))

    def setUp(self):
        acesso = patch('core.progresso.modulo_pode_ser_acessado', return_value=True)
        acesso.start()
        self.addCleanup(acesso.stop)
        self.client.force_login(self.usuario)

    def completar(self):
        for par in self.pares:
            for palavra in (par.palavra_base, par.palavra_comparada):
                resposta = self.client.post(reverse('registrar_acerto', args=[4]), {
                    'comparacao_id': par.pk, 'palavra_id': palavra.pk, 'transcricao': palavra.palavra,
                }, content_type='application/json')
                self.assertEqual(resposta.status_code, 200)

    def test_catalogo_explicacao_e_trilha(self):
        self.assertEqual([(p.palavra_base.palavra, p.palavra_comparada.palavra) for p in self.pares],
                         [('cub', 'cube'), ('tub', 'tube'), ('cut', 'cute')])
        resposta = self.client.get(reverse('explicacao_modulo_4'))
        self.assertContains(resposta, 'MAGIC E — SOM DO U')
        self.assertContains(resposta, 'cub')
        self.assertNotContains(self.client.get(reverse('trilha')), reverse('explicacao_modulo_4'))

    def test_descobertas_bloqueiam_e_exigem_as_duas_palavras(self):
        self.assertEqual(self.client.get(reverse('descoberta_modulo', args=[4, 2])).status_code, 409)
        primeiro = self.pares[0]
        self.assertEqual(self.client.post(reverse('registrar_acerto', args=[4]), {
            'comparacao_id': primeiro.pk, 'palavra_id': primeiro.palavra_base_id, 'transcricao': 'wrong',
        }, content_type='application/json').status_code, 400)
        self.assertEqual(self.client.get(reverse('resumo_modulo_4')).status_code, 409)
        self.client.post(reverse('registrar_acerto', args=[4]), {
            'comparacao_id': primeiro.pk, 'palavra_id': primeiro.palavra_base_id, 'transcricao': 'CUB!',
        }, content_type='application/json')
        self.assertEqual(self.client.get(reverse('descoberta_modulo', args=[4, 2])).status_code, 409)
        self.client.post(reverse('registrar_acerto', args=[4]), {
            'comparacao_id': primeiro.pk, 'palavra_id': primeiro.palavra_comparada_id, 'transcricao': 'cube',
        }, content_type='application/json')
        self.assertEqual(self.client.get(reverse('descoberta_modulo', args=[4, 2])).status_code, 200)

    def test_resumo_conclusao_e_progresso(self):
        self.completar()
        self.assertEqual(self.client.get(reverse('resumo_modulo_4')).status_code, 200)
        self.assertContains(self.client.get(reverse('resumo_modulo_4')), 'Magic E — Som do U')
        self.assertEqual(self.client.post(reverse('conclusao_modulo_4')).status_code, 302)
        self.assertEqual(Progresso.objects.get(usuario=self.usuario, modulo=self.modulo).percentual, 100)
        self.assertIsNotNone(Progresso.objects.get(usuario=self.usuario, modulo=self.modulo).concluido_em)

