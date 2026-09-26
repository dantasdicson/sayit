from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core import progresso
from core.models import Modulo, Tentativa


class QuatroDescobertasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())

    def test_todos_os_modulos_habilitados_tem_quatro_pares(self):
        for numero, total in progresso.DESCOBERTAS_POR_MODULO.items():
            if numero == 10:
                self.assertEqual(total, 3)
                continue
            with self.subTest(modulo=numero):
                modulo = Modulo.objects.get(numero=numero)
                self.assertEqual(total, 4)
                self.assertEqual(list(modulo.comparacoes.values_list('ordem', flat=True)), [1, 2, 3, 4])
                self.assertEqual(modulo.palavras.filter(ativa=True).count(), 8)

    @patch('core.progresso.modulo_pode_ser_acessado', return_value=True)
    def test_quarto_par_obrigatorio_preserva_acertos_anteriores(self, acesso):
        for numero in range(4, 9):
            with self.subTest(modulo=numero):
                usuario = get_user_model().objects.create_user(username=f'quatro-{numero}', email=f'quatro-{numero}@example.invalid')
                self.client.force_login(usuario)
                modulo = Modulo.objects.get(numero=numero)
                pares = list(modulo.comparacoes.order_by('ordem'))
                for par in pares[:3]:
                    for palavra in (par.palavra_base, par.palavra_comparada):
                        progresso.registrar_acerto(usuario, numero, par.pk, palavra.pk, palavra.palavra)
                ids = list(Tentativa.objects.filter(usuario=usuario).values_list('pk', flat=True))
                call_command('popular_sayit', modulo=numero, stdout=StringIO())
                self.assertEqual(list(Tentativa.objects.filter(usuario=usuario).values_list('pk', flat=True)), ids)
                self.assertEqual(list(modulo.comparacoes.order_by('ordem').values_list('pk', flat=True)), [p.pk for p in pares])
                self.assertEqual(progresso.consultar_progresso(usuario, numero)['percentual'], 75)
                self.assertEqual(self.client.get(reverse(f'resumo_modulo_{numero}')).status_code, 409)
                self.assertEqual(self.client.post(reverse(f'conclusao_modulo_{numero}')).status_code, 409)
                self.assertContains(self.client.get(reverse('descoberta_modulo', args=[numero, 4])), 'Descoberta 4 de 4')
                for palavra in (pares[3].palavra_base, pares[3].palavra_comparada):
                    resposta = self.client.post(reverse('registrar_acerto', args=[numero]), {
                        'comparacao_id': pares[3].pk, 'palavra_id': palavra.pk,
                        'transcricao': palavra.palavra,
                    }, content_type='application/json')
                    self.assertEqual(resposta.status_code, 200)
                self.assertEqual(resposta.json()['percentual'], 100)
                self.assertEqual(self.client.get(reverse(f'resumo_modulo_{numero}')).status_code, 200)
                self.assertEqual(self.client.post(reverse(f'conclusao_modulo_{numero}')).status_code, 302)
