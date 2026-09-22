from io import StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.models import Modulo, Palavra, Tentativa


class ResumoModuloTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())

    def setUp(self):
        usuario = get_user_model().objects.create_user(username='aluno_resumo')
        self.client.force_login(usuario)
        # O Resumo exige acertos persistidos; a mídia continua sendo testada à parte.
        Tentativa.objects.bulk_create([
            Tentativa(usuario=usuario, palavra=palavra, resultado='correto',
                      resposta_reconhecida=palavra.palavra)
            for palavra in Palavra.objects.filter(modulo__numero=1)
        ])
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        override = override_settings(MEDIA_ROOT=self.media.name)
        override.enable()
        self.addCleanup(override.disable)

    def test_resumo_identifica_modulo_e_mostra_quatro_pares_na_ordem(self):
        response = self.client.get(reverse('resumo_modulo_1'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/resumo_modulo.html')
        self.assertContains(response, 'MÓDULO 1 · RESUMO')
        self.assertContains(response, 'O que você aprendeu?')
        self.assertContains(response, 'Magic E — Som do A')
        self.assertContains(response, 'Muito bem! Você terminou a revisão do Magic E.')
        self.assertNotContains(response, 'Agora você já sabe:')
        expected = [('cat', 'cake'), ('cap', 'cape'), ('tap', 'tape'), ('mad', 'made')]
        self.assertEqual([
            tuple(card['palavra'].palavra for card in pair)
            for pair in response.context['pares']
        ], expected)
        for pair in expected:
            for word in pair:
                self.assertContains(response, f'<h3 lang="en">{word.upper()}</h3>', html=True)
        self.assertNotContains(response, 'descobertas_microfone.js')
        self.assertNotContains(response, 'data-practice-word')

    def test_ausencia_de_audio_nao_renderiza_player_ou_caminho_inexistente(self):
        response = self.client.get(reverse('resumo_modulo_1'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'A explicação em áudio ainda não está disponível')
        self.assertNotContains(response, 'Ouvir explicação')
        self.assertContains(response, 'id="audio-status"')
        self.assertContains(response, 'A narração deste resumo não está disponível')
        self.assertNotContains(response, '<audio')
        self.assertNotContains(response, 'resumo.mp3')
        self.assertNotContains(response, 'resumo_audio.js')
        self.assertContains(response, f'action="{reverse("conclusao_modulo_1")}"')
        self.assertContains(response, 'id="summary-complete" class="practice-link" type="submit" disabled')

    @patch('core.views.default_storage')
    def test_audio_disponivel_renderiza_controle_acessivel(self, storage):
        storage.exists.return_value = True
        storage.size.return_value = 1024
        storage.url.return_value = '/media/modulos/1/resumo.mp3'
        response = self.client.get(reverse('resumo_modulo_1'))
        storage.exists.assert_called_once_with('modulos/1/resumo.mp3')
        storage.url.assert_called_once_with('modulos/1/resumo.mp3')
        self.assertContains(response, 'src="/media/modulos/1/resumo.mp3"')
        self.assertContains(response, 'controls preload="auto"')
        self.assertContains(response, 'aria-controls="summary-audio"')
        self.assertContains(response, 'id="summary-listen"')
        self.assertContains(response, 'id="summary-audio"')
        self.assertContains(response, 'id="audio-status"')
        self.assertContains(response, 'Ouvir explicação novamente')
        self.assertContains(response, 'core/resumo_audio.js')
        self.assertContains(response, 'id="summary-complete" class="practice-link" type="submit" disabled')

    @patch('core.views.default_storage')
    def test_audio_vazio_ou_inacessivel_nao_impede_resumo(self, storage):
        storage.exists.return_value = True
        storage.size.return_value = 0
        response = self.client.get(reverse('resumo_modulo_1'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<audio')
        storage.exists.side_effect = OSError('indisponível')
        response = self.client.get(reverse('resumo_modulo_1'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<audio')
        storage.url.assert_not_called()

    def test_modulo_inativo_e_resumos_nao_implementados_retornam_404(self):
        Modulo.objects.filter(numero=1).update(ativo=False)
        self.assertEqual(self.client.get(reverse('resumo_modulo_1')).status_code, 404)
        # Os Módulos 1–8 têm resumo; os demais ainda não foram implementados.
        for number in range(9, 11):
            self.assertEqual(self.client.get(f'/modulos/{number}/resumo/').status_code, 404)

    def test_fluxo_completo_preserva_descobertas_e_conclusao(self):
        intro = self.client.get(reverse('explicacao_modulo_1'))
        self.assertContains(intro, f'href="{reverse("descoberta_modulo_1", args=[1])}"')
        for number in range(1, 5):
            response = self.client.get(reverse('descoberta_modulo_1', args=[number]))
            destination = reverse('descoberta_modulo_1', args=[number + 1]) if number < 4 else reverse('resumo_modulo_1')
            self.assertContains(response, f'data-next-url="{destination}"')
            self.assertContains(response, 'type="button" aria-describedby="speech-status"')
            self.assertContains(response, 'data-practice-word=', count=2)
            self.assertNotContains(response, reverse('conclusao_modulo_1'))
        summary = self.client.get(reverse('resumo_modulo_1'))
        self.assertContains(summary, f'action="{reverse("conclusao_modulo_1")}"')
        conclusion = self.client.get(reverse('conclusao_modulo_1'))
        self.assertTemplateUsed(conclusion, 'core/conclusao_modulo_1.html')
        self.assertContains(conclusion, f'action="{reverse("conclusao_modulo_1")}"')
        self.assertRedirects(self.client.post(reverse("conclusao_modulo_1")), reverse("explicacao_modulo_2"))

    @patch('django.core.files.storage.FileSystemStorage.exists', return_value=True)
    def test_reutiliza_imagem_cadastrada_com_alt(self, exists):
        word = Modulo.objects.get(numero=1).palavras.get(palavra='cat')
        word.imagem = 'palavras/imagens/cat.webp'
        word.save(update_fields=['imagem'])
        response = self.client.get(reverse('resumo_modulo_1'))
        self.assertContains(response, 'src="/media/palavras/imagens/cat.webp" alt="gato"')
