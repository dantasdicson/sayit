from html.parser import HTMLParser

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.models import Comparacao, Modulo, Palavra


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class DescobertasPronunciaTests(TestCase):
    pairs = (('cat', 'cake'), ('cap', 'cape'), ('tap', 'tape'), ('mad', 'made'))

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user(username='aluno_descobertas'))

    @classmethod
    def setUpTestData(cls):
        modulo = Modulo.objects.create(numero=1, ordem=1, titulo='Magic E', descricao='Teste')
        for number, pair in enumerate(cls.pairs, 1):
            words = [Palavra.objects.create(
                modulo=modulo, palavra=text, traducao=text, ordem=(number - 1) * 2 + offset,
                imagem=f'palavras/imagens/{text}.webp', audio=f'palavras/audios/{text}.mp3',
            ) for offset, text in enumerate(pair, 1)]
            Comparacao.objects.create(modulo=modulo, palavra_base=words[0], palavra_comparada=words[1], ordem=number)

    def test_four_discoveries_require_both_words_and_preserve_media_and_destinations(self):
        for number, pair in enumerate(self.pairs, 1):
            with self.subTest(discovery=number):
                response = self.client.get(reverse('descoberta_modulo_1', args=[number]))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'core/descoberta_modulo_1.html')
                elements = Elements(response.content.decode()).elements
                practices = [attrs for _, attrs in elements if 'data-practice-word' in attrs]
                self.assertEqual([attrs['data-practice-word'] for attrs in practices], list(pair))
                microphones = [attrs for tag, attrs in elements if tag == 'button' and attrs.get('class') == 'speak']
                self.assertEqual(len(microphones), 2)
                self.assertTrue(all('disabled' in attrs for attrs in microphones))
                next_button = [attrs for tag, attrs in elements if tag == 'button' and attrs.get('id') == 'discovery-next']
                self.assertEqual(len(next_button), 1)
                self.assertIn('disabled', next_button[0])
                self.assertEqual(next_button[0]['type'], 'button')
                destination = reverse('descoberta_modulo_1', args=[number + 1]) if number < 4 else reverse('resumo_modulo_1')
                self.assertEqual(next_button[0]['data-next-url'], destination)
                self.assertFalse(any(tag == 'a' and attrs.get('href') == destination for tag, attrs in elements))
                self.assertContains(response, 'core/descobertas_microfone.js', count=1)
                self.assertNotContains(response, 'core/descoberta_1_microfone.js')
                self.assertContains(response, f'Fale {pair[0].upper()} e {pair[1].upper()} corretamente')
                for word in pair:
                    self.assertContains(response, f'/media/palavras/audios/{word}.mp3')
                    self.assertContains(response, f'/media/palavras/imagens/{word}.webp')

    def test_invalid_discoveries_still_return_404(self):
        for number in (0, 5):
            self.assertEqual(self.client.get(reverse('descoberta_modulo_1', args=[number])).status_code, 404)
