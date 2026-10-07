from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class ApresentacaoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='primeira-visita', email='visita@example.invalid')
        self.client.force_login(self.user)

    def test_primeira_entrada_mostra_intro_sem_marcar_como_vista(self):
        self.assertContains(self.client.get('/'), 'id="welcome-dialog"')
        self.user.refresh_from_db()
        self.assertIsNone(self.user.apresentacao_vista_em)

    def test_conclusao_persiste_por_conta_e_encaminha_trilha(self):
        response = self.client.post(reverse('concluir_apresentacao'), {'destino': 'trilha'})
        self.assertEqual(response.url, reverse('trilha'))
        self.user.refresh_from_db()
        first = self.user.apresentacao_vista_em
        self.assertIsNotNone(first)
        self.assertNotContains(self.client.get('/'), 'id="welcome-dialog"')
        other_session = Client()
        other_session.force_login(self.user)
        self.assertNotContains(other_session.get('/'), 'id="welcome-dialog"')
        self.client.post(reverse('concluir_apresentacao'), {'destino': 'home'})
        self.user.refresh_from_db()
        self.assertEqual(first, self.user.apresentacao_vista_em)

    def test_reabrir_e_outro_usuario(self):
        self.client.post(reverse('concluir_apresentacao'), {'destino': 'home'})
        self.assertContains(self.client.get('/?apresentacao=1'), 'id="welcome-dialog"')
        other = get_user_model().objects.create_user(username='outra-visita', email='outra@example.invalid')
        self.client.force_login(other)
        self.assertContains(self.client.get('/'), 'id="welcome-dialog"')

    def test_post_exige_csrf_e_get_nao_modifica(self):
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.user)
        url = reverse('concluir_apresentacao')
        self.assertEqual(secure.post(url).status_code, 403)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.apresentacao_vista_em)

    def test_destino_externo_nao_redireciona_fora_do_app(self):
        response = self.client.post(reverse('concluir_apresentacao'), {'destino': 'https://evil.example'})
        self.assertEqual(response.url, '/')
