from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from core import progresso
from core.models import Modulo, Progresso, Tentativa


class Modulo7Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())
        cls.usuario = get_user_model().objects.create_user(username='modulo7', email='m7@test.com')
        cls.modulo = Modulo.objects.get(numero=7)
        cls.pares = list(cls.modulo.comparacoes.select_related(
            'palavra_base', 'palavra_comparada').order_by('ordem'))

    def setUp(self):
        self.client.force_login(self.usuario)

    def url(self, ordem):
        return reverse('descoberta_modulo', args=[7, ordem])

    def acertar(self, indice, segunda=False, texto=None):
        par = self.pares[indice]
        palavra = par.palavra_comparada if segunda else par.palavra_base
        return self.client.post(reverse('registrar_acerto', args=[7]), {
            'comparacao_id': par.pk, 'palavra_id': palavra.pk,
            'transcricao': palavra.palavra if texto is None else texto,
        }, content_type='application/json')

    def completar(self):
        for indice in range(3):
            self.assertEqual(self.acertar(indice).status_code, 200)
            self.assertEqual(self.acertar(indice, True).status_code, 200)

    def test_catalogo_explicacao_pares_e_trilha(self):
        self.assertEqual(list(self.modulo.palavras.values_list('palavra', flat=True)),
                         ['think', 'tooth', 'bath', 'this', 'that', 'mother'])
        self.assertEqual([(p.palavra_base.palavra, p.palavra_comparada.palavra) for p in self.pares],
                         [('think', 'this'), ('tooth', 'that'), ('bath', 'mother')])
        resposta = self.client.get(reverse('explicacao_modulo_7'))
        self.assertContains(resposta, 'O SOM TH')
        self.assertContains(resposta, self.modulo.conteudo_teorico)
        self.assertContains(resposta, self.url(1))
        self.assertContains(self.client.get(reverse('trilha')), reverse('explicacao_modulo_7'))

    def test_tres_etapas_dois_acertos_independentes_e_persistencia(self):
        for indice in range(3):
            resposta = self.client.get(self.url(indice + 1))
            self.assertContains(resposta, 'data-modulo="7"')
            self.assertContains(resposta, 'type="button" disabled aria-describedby="speech-status"')
            self.assertEqual(self.acertar(indice).json()['percentual'], indice * 100 // 3)
            parcial = self.client.get(self.url(indice + 1))
            self.assertEqual([card['acertada'] for card in parcial.context['cards']], [True, False])
            self.assertEqual(self.acertar(indice, True).json()['percentual'], (indice + 1) * 100 // 3)
            destino = self.url(indice + 2) if indice < 2 else reverse('resumo_modulo_7')
            self.assertEqual(self.client.get(self.url(indice + 1)).context['proxima_url'], destino)
        self.assertEqual(Tentativa.objects.count(), 6)

    def test_bloqueio_erro_silencio_e_recarregamento(self):
        self.assertEqual(self.client.get(self.url(2)).status_code, 409)
        self.assertEqual(self.client.get(reverse('resumo_modulo_7')).status_code, 409)
        self.assertEqual(self.client.get(reverse('conclusao_modulo_7')).status_code, 409)
        for texto in ('wrong', '', ' ... ', 'this', 'thing'):
            self.assertEqual(self.acertar(0, texto=texto).status_code, 400)
        self.assertFalse(Tentativa.objects.exists())
        self.assertEqual(self.acertar(0, texto=' THINK! ').status_code, 200)
        self.client.logout()
        self.client.force_login(self.usuario)
        self.assertEqual([c['acertada'] for c in self.client.get(self.url(1)).context['cards']], [True, False])
        self.assertIn(7, [item['modulo'].numero for item in progresso.consultar_meu_progresso(self.usuario)])

    def test_resumo_conclusao_e_encaminhamento_ao_modulo_8(self):
        self.completar()
        with patch('core.views.default_storage') as storage:
            storage.exists.return_value = True
            storage.size.return_value = 100
            storage.url.return_value = '/media/modulos/7/resumo.mp3'
            resposta = self.client.get(reverse('resumo_modulo_7'))
        for texto in ('Os dois sons de TH', '/media/modulos/7/resumo.mp3', 'resumo_audio.js'):
            self.assertContains(resposta, texto)
        self.assertRedirects(self.client.post(reverse('conclusao_modulo_7')), reverse('conclusao_modulo_7'))
        conclusao = self.client.get(reverse('conclusao_modulo_7'))
        self.assertContains(conclusao, 'Continuar para o próximo módulo')
        self.assertContains(conclusao, f'href="{reverse("explicacao_modulo_8")}"')
        self.assertEqual(self.client.get(reverse('explicacao_modulo_8')).status_code, 200)
        estado = Progresso.objects.get(usuario=self.usuario, modulo=self.modulo)
        self.assertEqual(estado.percentual, 100)
        self.assertIsNotNone(estado.concluido_em)

    def test_midias_reais_associacao_e_renderizacao(self):
        from core.management.commands.associar_audios import Command as Audios
        from core.management.commands.associar_imagens import Command as Imagens
        call_command('associar_imagens', modulo=7, stdout=StringIO())
        call_command('associar_audios', modulo=7, stdout=StringIO())
        for indice, par in enumerate(self.pares):
            resposta = self.client.get(self.url(indice + 1))
            for palavra in (par.palavra_base, par.palavra_comparada):
                palavra.refresh_from_db()
                self.assertEqual(Imagens.validar_webp(Path(palavra.imagem.path))[0], 'valido')
                self.assertEqual(Audios.validar_mp3(Path(palavra.audio.path))[0], 'valido')
                self.assertContains(resposta, palavra.imagem.url)
                self.assertContains(resposta, palavra.audio.url)
            self.acertar(indice)
            self.acertar(indice, True)
        self.assertEqual(Audios.validar_mp3(Path(settings.MEDIA_ROOT) / 'modulos/7/resumo.mp3')[0], 'valido')

    def test_autenticacao_csrf_e_catalogo_incompleto(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        self.assertEqual(cliente.post(reverse('conclusao_modulo_7')).status_code, 403)
        self.client.logout()
        for url in (self.url(1), reverse('explicacao_modulo_7'),
                    reverse('resumo_modulo_7'), reverse('conclusao_modulo_7')):
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.usuario)
        self.pares[-1].delete()
        self.assertEqual(self.client.post(reverse('conclusao_modulo_7')).status_code, 409)
