from html.parser import HTMLParser
from io import StringIO

from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from core.models import Comparacao, Modulo, Palavra, Progresso, Tentativa


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
        usuario = get_user_model().objects.create_user(username='aluno_descobertas')
        self.client.force_login(usuario)
        # Estes testes inspecionam a interface de etapas já liberadas.
        Tentativa.objects.bulk_create([
            Tentativa(usuario=usuario, palavra=palavra, resultado='correto',
                      resposta_reconhecida=palavra.palavra)
            for palavra in Palavra.objects.filter(modulo__numero=1)
        ])

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
                self.assertNotIn('disabled', next_button[0])
                self.assertEqual(next_button[0]['type'], 'button')
                destination = reverse('descoberta_modulo_1', args=[number + 1]) if number < 4 else reverse('resumo_modulo_1')
                self.assertEqual(next_button[0]['data-next-url'], destination)
                self.assertFalse(any(tag == 'a' and attrs.get('href') == destination for tag, attrs in elements))
                self.assertContains(response, 'core/descobertas_microfone.js', count=1)
                self.assertNotContains(response, 'core/descoberta_1_microfone.js')
                self.assertContains(response, f'Você concluiu {pair[0].upper()} e {pair[1].upper()}! Pode continuar.')
                for word in pair:
                    self.assertContains(response, f'/media/palavras/audios/{word}.mp3')
                    self.assertContains(response, f'/media/palavras/imagens/{word}.webp')

    def test_invalid_discoveries_still_return_404(self):
        for number in (0, 5):
            self.assertEqual(self.client.get(reverse('descoberta_modulo_1', args=[number])).status_code, 404)


class EstadoPersistidoDescobertasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username='estado_aluno', email='estado@example.com', password='SenhaTeste-294!')
        cls.outro = get_user_model().objects.create_user(username='estado_outro', email='outro@example.com')
        call_command('popular_sayit', stdout=StringIO())
        cls.pares = list(Comparacao.objects.filter(modulo__numero=1).order_by('ordem'))

    def setUp(self):
        self.client.force_login(self.usuario)

    def abrir(self, numero=1):
        resposta = self.client.get(reverse('descoberta_modulo_1', args=[numero]))
        self.assertEqual(resposta.status_code, 200)
        return resposta

    def acertar(self, indice=0, segunda=False):
        par = self.pares[indice]
        palavra = par.palavra_comparada if segunda else par.palavra_base
        resposta = self.client.post(reverse('registrar_acerto', args=[1]), {
            'comparacao_id': par.pk, 'palavra_id': palavra.pk, 'transcricao': palavra.palavra,
        }, content_type='application/json')
        self.assertEqual(resposta.status_code, 200)
        return resposta

    def test_sem_acertos_renderiza_ambas_pendentes_sem_gravar(self):
        resposta = self.abrir()
        self.assertEqual([c['acertada'] for c in resposta.context['cards']], [False, False])
        self.assertFalse(resposta.context['descoberta_concluida'])
        self.assertEqual(resposta.context['percentual'], 0)
        self.assertContains(resposta, 'data-acertada="false"', count=2)
        self.assertContains(resposta, 'class="word-complete" hidden', count=2)
        self.assertFalse(Tentativa.objects.exists())
        self.assertFalse(Progresso.objects.exists())

    def test_uma_palavra_persistida_chega_ao_contexto_e_html(self):
        self.acertar()
        resposta = self.abrir()
        self.assertEqual([c['acertada'] for c in resposta.context['cards']], [True, False])
        self.assertFalse(resposta.context['descoberta_concluida'])
        self.assertEqual(resposta.context['percentual'], 0)
        self.assertContains(resposta, 'data-acertada="true"', count=1)
        self.assertContains(resposta, 'Você já acertou esta palavra.', count=1)

    def test_duas_palavras_restauram_conclusao_e_percentual_25(self):
        self.acertar(); self.acertar(segunda=True)
        resposta = self.abrir()
        self.assertEqual([c['acertada'] for c in resposta.context['cards']], [True, True])
        self.assertTrue(resposta.context['descoberta_concluida'])
        self.assertEqual(resposta.context['percentual'], 25)
        self.assertContains(resposta, 'data-percentual="25"')
        self.assertContains(resposta, 'data-concluida="true"')
        botao = next(attrs for _, attrs in Elements(resposta.content.decode()).elements
                     if attrs.get('id') == 'discovery-next')
        self.assertNotIn('disabled', botao)
        self.assertIsNone(Progresso.objects.get().concluido_em)

    def test_ids_reais_e_url_chegam_ao_html(self):
        # IDs deliberadamente diferentes dos exemplos 1/2 do contrato.
        par = self.pares[0]
        Comparacao.objects.filter(pk=par.pk).update(id=317)
        Palavra.objects.filter(pk=par.palavra_base_id).update(palavra='custom')
        resposta = self.abrir()
        self.assertEqual(resposta.context['comparacao'].pk, 317)
        self.assertContains(resposta, 'data-comparacao-id="317"')
        self.assertContains(resposta, f'data-palavra-id="{par.palavra_base_id}"')
        self.assertContains(resposta, f'data-palavra-id="{par.palavra_comparada_id}"')
        self.assertContains(resposta, 'data-modulo="1"')
        self.assertContains(resposta, f'data-acertos-url="{reverse("registrar_acerto", args=[1])}"')

    def test_estado_visual_isolado_por_usuario(self):
        self.acertar(); self.acertar(segunda=True)
        self.client.force_login(self.outro)
        resposta = self.abrir()
        self.assertEqual([c['acertada'] for c in resposta.context['cards']], [False, False])
        self.assertEqual(resposta.context['percentual'], 0)
        self.assertFalse(resposta.context['descoberta_concluida'])
        self.assertFalse(Progresso.objects.filter(usuario=self.outro).exists())

    def test_reload_preserva_banco_e_acerto_parcial(self):
        self.acertar()
        antes = (list(Tentativa.objects.values()), list(Progresso.objects.values()))
        for _ in range(2):
            self.assertEqual([c['acertada'] for c in self.abrir().context['cards']], [True, False])
        self.assertEqual((list(Tentativa.objects.values()), list(Progresso.objects.values())), antes)

    def test_logout_login_restaura_as_duas_palavras(self):
        self.acertar(); self.acertar(segunda=True)
        self.client.post(reverse('logout'))
        self.assertEqual(self.client.get(reverse('descoberta_modulo_1', args=[1])).status_code, 302)
        resposta = self.client.post(reverse('login'), {'username': 'estado_aluno', 'password': 'SenhaTeste-294!'})
        self.assertEqual(resposta.status_code, 302)
        resposta = self.abrir()
        self.assertEqual([c['acertada'] for c in resposta.context['cards']], [True, True])
        self.assertTrue(resposta.context['descoberta_concluida'])
        self.assertEqual(resposta.context['percentual'], 25)
        self.assertEqual(Tentativa.objects.count(), 2)

    def test_fluxo_cat_reload_cake_libera_descoberta_2(self):
        self.abrir()
        self.acertar()
        self.assertEqual([c['acertada'] for c in self.abrir().context['cards']], [True, False])
        self.assertEqual(self.client.get(reverse('descoberta_modulo_1', args=[2])).status_code, 409)
        self.assertEqual(self.acertar(segunda=True).json()['percentual'], 25)
        self.assertTrue(self.abrir().context['descoberta_concluida'])
        self.assertEqual([c['acertada'] for c in self.abrir(2).context['cards']], [False, False])

    def test_quatro_descobertas_100_sem_conclusao_formal(self):
        for indice in range(4):
            self.acertar(indice); self.acertar(indice, segunda=True)
            self.assertEqual(self.abrir(indice + 1).context['percentual'], (indice + 1) * 25)
        self.assertEqual(self.client.get(reverse('resumo_modulo_1')).status_code, 200)
        self.assertIsNone(Progresso.objects.get().concluido_em)

    def test_token_do_template_permite_post_com_csrf_real(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        resposta = cliente.get(reverse('descoberta_modulo_1', args=[1]))
        token = next(attrs['value'] for _, attrs in Elements(resposta.content.decode()).elements
                     if attrs.get('name') == 'csrfmiddlewaretoken')
        resposta = cliente.post(reverse('registrar_acerto', args=[1]), {
            'comparacao_id': self.pares[0].pk, 'palavra_id': self.pares[0].palavra_base_id,
            'transcricao': 'cat',
        }, content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Tentativa.objects.count(), 1)

    def test_estado_personalizado_nao_deve_ser_armazenado_em_cache(self):
        resposta = self.abrir()
        self.assertIn('no-store', resposta['Cache-Control'])
        self.assertIn('private', resposta['Cache-Control'])
