from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from core.models import Modulo, Progresso, Tentativa


class Modulo9Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())
        call_command('associar_imagens', modulo=9, stdout=StringIO())
        call_command('associar_audios', modulo=9, stdout=StringIO())
        cls.usuario = get_user_model().objects.create_user(username='modulo9', email='m9@test.com')
        cls.modulo = Modulo.objects.get(numero=9)
        cls.pares = list(cls.modulo.comparacoes.select_related(
            'palavra_base', 'palavra_comparada').order_by('ordem'))

    def setUp(self):
        acesso = patch('core.progresso.modulo_pode_ser_acessado', return_value=True)
        acesso.start()
        self.addCleanup(acesso.stop)
        self.client.force_login(self.usuario)

    def url(self, ordem):
        return reverse('descoberta_modulo', args=[9, ordem])

    def acertar(self, indice, segunda=False, texto=None):
        par = self.pares[indice]
        palavra = par.palavra_comparada if segunda else par.palavra_base
        return self.client.post(reverse('registrar_acerto', args=[9]), {
            'comparacao_id': par.pk,
            'palavra_id': palavra.pk,
            'transcricao': palavra.palavra if texto is None else texto,
        }, content_type='application/json')

    def completar(self):
        for indice in range(4):
            self.assertEqual(self.acertar(indice).status_code, 200)
            self.assertEqual(self.acertar(indice, True).status_code, 200)

    def test_catalogo_explicacao_e_quatro_pares(self):
        self.assertEqual(list(self.modulo.palavras.values_list('palavra', flat=True)), [
            'moon', 'food', 'room', 'school', 'book', 'look', 'good', 'foot'])
        self.assertEqual([
            (par.palavra_base.palavra, par.palavra_comparada.palavra) for par in self.pares
        ], [('moon', 'book'), ('food', 'good'), ('room', 'look'), ('school', 'foot')])
        resposta = self.client.get(reverse('explicacao_modulo_9'))
        self.assertContains(resposta, 'O SOM OO')
        self.assertContains(resposta, self.modulo.conteudo_teorico)
        self.assertContains(resposta, self.url(1))

    def test_etapas_acertos_independentes_bloqueio_e_persistencia(self):
        self.assertEqual(self.client.get(self.url(2)).status_code, 409)
        self.assertEqual(self.client.get(reverse('resumo_modulo_9')).status_code, 409)
        for indice in range(4):
            resposta = self.client.get(self.url(indice + 1))
            self.assertContains(resposta, 'data-modulo="9"')
            self.assertContains(resposta, 'type="button" disabled aria-describedby="speech-status"')
            self.assertEqual(self.acertar(indice).json()['percentual'], indice * 25)
            parcial = self.client.get(self.url(indice + 1))
            self.assertEqual([card['acertada'] for card in parcial.context['cards']], [True, False])
            self.assertEqual(self.acertar(indice, True).json()['percentual'], (indice + 1) * 25)
        self.assertEqual(Tentativa.objects.count(), 8)
        self.client.logout()
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse('resumo_modulo_9')).status_code, 200)

    def test_erro_normalizacao_resumo_conclusao_e_proximo_indisponivel(self):
        for texto in ('wrong', '', ' ... ', 'book', 'wrong moon'):
            self.assertEqual(self.acertar(0, texto=texto).status_code, 400)
        self.assertFalse(Tentativa.objects.exists())
        self.assertEqual(self.acertar(0, texto=' MOON! ').status_code, 200)
        for indice in range(4):
            if indice:
                self.assertEqual(self.acertar(indice).status_code, 200)
            self.assertEqual(self.acertar(indice, True).status_code, 200)
        resposta = self.client.get(reverse('resumo_modulo_9'))
        self.assertContains(resposta, 'Os dois sons de OO')
        self.assertContains(resposta, '/media/modulos/9/resumo.mp3')
        self.assertContains(resposta, 'resumo_audio.js')
        self.assertContains(resposta, 'Concluir módulo')
        self.assertContains(resposta, 'disabled')
        self.assertRedirects(
            self.client.post(reverse('conclusao_modulo_9')),
            reverse('conclusao_modulo_9'))
        conclusao = self.client.get(reverse('conclusao_modulo_9'))
        self.assertContains(conclusao, 'Continuar para o próximo módulo')
        self.assertContains(conclusao, 'O próximo módulo estará disponível em breve.')
        self.assertContains(conclusao, f'href="{reverse("trilha")}"')
        estado = Progresso.objects.get(usuario=self.usuario, modulo=self.modulo)
        self.assertEqual(estado.percentual, 100)
        self.assertIsNotNone(estado.concluido_em)

    def test_imagens_audios_e_renderizacao(self):
        from core.management.commands.associar_audios import Command as Audios
        from core.management.commands.associar_imagens import Command as Imagens

        for indice, par in enumerate(self.pares):
            resposta = self.client.get(self.url(indice + 1))
            for palavra in (par.palavra_base, par.palavra_comparada):
                self.assertEqual(Imagens.validar_webp(Path(palavra.imagem.path))[0], 'valido')
                self.assertEqual(Audios.validar_mp3(Path(palavra.audio.path))[0], 'valido')
                self.assertContains(resposta, palavra.imagem.url)
                self.assertContains(resposta, palavra.audio.url)
            self.acertar(indice)
            self.acertar(indice, True)
        resumo = Path(settings.MEDIA_ROOT) / 'modulos/9/resumo.mp3'
        self.assertEqual(Audios.validar_mp3(resumo)[0], 'valido')

    def test_autenticacao_csrf_e_catalogo_incompleto(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        self.assertEqual(cliente.post(reverse('conclusao_modulo_9')).status_code, 403)
        self.client.logout()
        for url in (self.url(1), reverse('explicacao_modulo_9'),
                    reverse('resumo_modulo_9'), reverse('conclusao_modulo_9')):
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.usuario)
        self.pares[-1].delete()
        self.assertEqual(self.client.post(reverse('conclusao_modulo_9')).status_code, 409)
