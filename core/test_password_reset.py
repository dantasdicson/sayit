import re
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import urlsplit

from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', PUBLIC_BASE_URL='', SECURE_PROXY_SSL_HEADER=None)
class RecuperacaoSenhaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username='recuperacao', email='aluna@example.com', password='Antiga!Brisa-4829')

    def request_link(self, email='aluna@example.com', **kwargs):
        return self.client.post(reverse('password_reset'), {'email': email}, **kwargs)

    def link(self):
        self.request_link()
        return urlsplit(re.search(r'https?://\S+', mail.outbox[-1].body).group()).path

    def test_login_exibe_link_e_formulario_acessivel(self):
        self.assertContains(self.client.get(reverse('login')), reverse('password_reset'))
        response = self.client.get(reverse('password_reset'))
        self.assertContains(response, 'E-mail cadastrado')
        self.assertContains(response, 'autocomplete="email"')
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_email_case_insensitive_com_link_sem_senha(self):
        self.assertRedirects(self.request_link('ALUNA@EXAMPLE.COM'), reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['aluna@example.com'])
        self.assertIn('http://testserver/redefinir-senha/', mail.outbox[0].body)
        self.assertNotIn('Antiga!Brisa-4829', mail.outbox[0].body)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Antiga!Brisa-4829'))

    def test_email_desconhecido_inativo_ou_senha_inutilizavel_mesma_confirmacao(self):
        User = get_user_model()
        User.objects.create_user(username='inativa', email='inativa@example.com',
                                 password='Senha!Forte-4829', is_active=False)
        User.objects.create_user(username='sem-senha', email='sem@example.com', password=None)
        expected = self.client.get(reverse('password_reset_done')).content
        for email in ['nao-existe@example.com', 'inativa@example.com', 'sem@example.com']:
            with self.subTest(email=email):
                response = self.request_link(email)
                self.assertEqual(response.url, reverse('password_reset_done'))
                self.assertEqual(self.client.get(response.url).content, expected)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_invalido(self):
        self.assertContains(self.request_link('invalido'), 'Digite um endereço de e-mail válido.')
        self.assertEqual(len(mail.outbox), 0)

    def test_header_arbitrario_nao_altera_link(self):
        self.request_link(HTTP_X_FORWARDED_PROTO='https')
        self.assertIn('http://testserver/redefinir-senha/', mail.outbox[-1].body)

    @override_settings(PUBLIC_BASE_URL='https://sayit-demo.vercel.app')
    def test_proxy_usa_dominio_publico_configurado(self):
        self.request_link(HTTP_HOST='testserver', HTTP_X_FORWARDED_HOST='evil.example')
        self.assertIn('https://sayit-demo.vercel.app/redefinir-senha/', mail.outbox[-1].body)
        self.assertNotIn('evil.example', mail.outbox[-1].body)

    def test_https_direto(self):
        self.request_link(secure=True)
        self.assertIn('https://testserver/redefinir-senha/', mail.outbox[-1].body)

    def test_fluxo_completo_invalida_link_e_sessoes(self):
        other_session = Client()
        other_session.force_login(self.user)
        original = self.link()
        response = self.client.get(original)
        self.assertEqual(response.status_code, 302)
        form_url = response.url
        self.assertTrue(form_url.endswith('/set-password/'))
        self.assertContains(self.client.get(form_url), 'Nova senha')
        response = self.client.post(form_url, {
            'new_password1': 'Nova!Orquidea-9723', 'new_password2': 'Nova!Orquidea-9723'})
        self.assertRedirects(response, reverse('password_reset_complete'))
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Nova!Orquidea-9723'))
        self.assertFalse(self.user.check_password('Antiga!Brisa-4829'))
        self.assertContains(Client().get(original), 'Este link não está disponível')
        self.assertContains(self.client.get(form_url), 'Este link não está disponível')
        self.assertRedirects(other_session.get(reverse('home')), reverse('login') + '?next=/')
        self.assertFalse(self.client.login(username='recuperacao', password='Antiga!Brisa-4829'))
        self.assertTrue(self.client.login(username='recuperacao', password='Nova!Orquidea-9723'))

    def test_senhas_fracas_ou_diferentes_nao_alteram_conta(self):
        form_url = self.client.get(self.link()).url
        for first, second in [('abc', 'abc'), ('123456789', '123456789'),
                              ('Nova!Orquidea-9723', 'Outra!Rosa-3819')]:
            with self.subTest(password=first):
                response = self.client.post(form_url, {'new_password1': first, 'new_password2': second})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
                self.user.refresh_from_db()
                self.assertTrue(self.user.check_password('Antiga!Brisa-4829'))

    def test_token_adulterado_e_usuario_invalido(self):
        self.assertContains(self.client.get(self.link().rstrip('/') + 'adulterado/'), 'Este link não está disponível')
        url = reverse('password_reset_confirm', args=['invalido', 'invalido'])
        self.assertContains(self.client.get(url), 'Este link não está disponível')
        self.assertContains(Client().get(reverse('password_reset_confirm',
            args=[urlsafe_base64_encode(force_bytes(self.user.pk)), 'set-password'])), 'Este link não está disponível')

    def test_token_expira_apos_uma_hora(self):
        now = datetime(2026, 10, 6, 12)
        with patch.object(default_token_generator, '_now', return_value=now):
            url = self.link()
        with patch.object(default_token_generator, '_now', return_value=now + timedelta(seconds=3601)):
            self.assertContains(self.client.get(url), 'Este link não está disponível')

    def test_csrf_obrigatorio_na_solicitacao_e_troca(self):
        protected = Client(enforce_csrf_checks=True)
        self.assertEqual(protected.post(reverse('password_reset'), {'email': self.user.email}).status_code, 403)
        form_url = protected.get(self.link()).url
        self.assertEqual(protected.post(form_url, {
            'new_password1': 'Nova!Orquidea-9723', 'new_password2': 'Nova!Orquidea-9723'}).status_code, 403)
