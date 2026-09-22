import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import Modulo, Tentativa


class RegistroErrosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())
        cls.usuario = get_user_model().objects.create_user(username='erros')

    def setUp(self):
        self.client.force_login(self.usuario)
        self.modulo = Modulo.objects.get(numero=1)
        self.comparacao = self.modulo.comparacoes.order_by('ordem').first()
        self.palavra = self.comparacao.palavra_base

    def enviar(self, transcricao, resultado):
        return self.client.post(
            reverse('registrar_erro', args=[1]),
            data=json.dumps({
                'comparacao_id': self.comparacao.pk,
                'palavra_id': self.palavra.pk,
                'transcricao': transcricao,
                'resultado': resultado,
            }),
            content_type='application/json',
        )

    def test_registra_fala_incorreta_sem_liberar_progresso(self):
        resposta = self.enviar('  WRONG!  ', 'incorreto')
        self.assertEqual(resposta.status_code, 201)
        tentativa = Tentativa.objects.get(usuario=self.usuario)
        self.assertEqual(tentativa.resultado, Tentativa.Resultado.INCORRETO)
        self.assertEqual(tentativa.resposta_reconhecida, 'wrong')
        self.assertFalse(self.usuario.progressos.filter(modulo=self.modulo).exists())

    def test_registra_silencio_como_nao_reconhecido(self):
        resposta = self.enviar('', 'nao_reconhecido')
        self.assertEqual(resposta.status_code, 201)
        self.assertTrue(Tentativa.objects.filter(
            usuario=self.usuario, resultado=Tentativa.Resultado.NAO_RECONHECIDO).exists())

    def test_endpoint_de_erro_nao_aceita_resultado_correto(self):
        resposta = self.enviar(self.palavra.palavra, 'correto')
        self.assertEqual(resposta.status_code, 400)
        self.assertFalse(Tentativa.objects.exists())

    def test_painel_separa_acertos_e_erros(self):
        self.enviar('wrong', 'incorreto')
        resposta = self.client.get(reverse('progresso'))
        self.assertEqual(resposta.context['total_acertos'], 0)
        self.assertEqual(resposta.context['total_erros'], 1)
        self.assertContains(resposta, 'Erros registrados')
