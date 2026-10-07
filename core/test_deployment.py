import io
import json
from unittest.mock import patch
from urllib.error import HTTPError
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.core.management import call_command
from django.test import Client, TestCase, SimpleTestCase, override_settings
from .email_backend import ResendEmailBackend
from .models import Modulo, Palavra, Comparacao


class DeploymentTests(TestCase):
    def test_health_confirma_postgres(self):
        from django.db import connection
        self.assertEqual(connection.vendor, 'postgresql')
        self.assertEqual(self.client.get('/health/').json(), {'status': 'ok'})

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['sayit.onrender.com', 'sayit.vercel.app'],
        PUBLIC_BASE_URL='https://sayit.vercel.app', CSRF_TRUSTED_ORIGINS=['https://sayit.vercel.app'],
        SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'), SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
    def test_login_proxy_csrf_cookies_e_cache(self):
        user = get_user_model().objects.create_user(username='proxy', email='proxy@example.invalid', password='Rosa!Montanha4829')
        client = Client(enforce_csrf_checks=True)
        headers = {'HTTP_HOST': 'sayit.onrender.com', 'HTTP_X_FORWARDED_PROTO': 'https'}
        page = client.get('/login/', **headers)
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page['Vercel-CDN-Cache-Control'], 'no-store')
        self.assertTrue(client.cookies['csrftoken']['secure'])
        data = {'username': user.username, 'password': 'Rosa!Montanha4829',
                'csrfmiddlewaretoken': client.cookies['csrftoken'].value}
        self.assertEqual(client.post('/login/', data, HTTP_ORIGIN='https://evil.example', **headers).status_code, 403)
        response = client.post('/login/', data, HTTP_ORIGIN='https://sayit.vercel.app', **headers)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(client.cookies['sessionid']['secure'])
        self.assertEqual(client.get('/', **headers).status_code, 200)

    def test_media_publica_e_caminho_privado(self):
        response = self.client.get('/media/palavras/imagens/cake.webp')
        self.assertEqual(response.status_code, 200)
        response.close()
        self.assertEqual(self.client.get('/media/../.env').status_code, 404)

    def test_catalogo_inicial_nao_sobrescreve_conteudo(self):
        call_command('inicializar_catalogo', stdout=io.StringIO())
        self.assertEqual((Modulo.objects.count(), Palavra.objects.count(), Comparacao.objects.count()), (10, 74, 30))
        modulo = Modulo.objects.get(numero=1)
        modulo.titulo = 'Título personalizado'
        modulo.save()
        call_command('inicializar_catalogo', se_vazio=True, stdout=io.StringIO())
        modulo.refresh_from_db()
        self.assertEqual(modulo.titulo, 'Título personalizado')

    def test_admin_inicial_preserva_senha_existente(self):
        with patch.dict('os.environ', {'ADMIN_USERNAME': 'admin-teste', 'ADMIN_EMAIL': 'admin@example.invalid', 'ADMIN_PASSWORD': 'Lago!Nuvem-4928'}):
            call_command('configurar_admin', stdout=io.StringIO())
            call_command('configurar_admin', stdout=io.StringIO())
        user = get_user_model().objects.get(username='admin-teste')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password('Lago!Nuvem-4928'))
        self.assertEqual(get_user_model().objects.count(), 1)


@override_settings(RESEND_API_KEY='chave-ficticia-para-teste', EMAIL_TIMEOUT=15)
class EmailApiTests(SimpleTestCase):
    def test_envio_por_https_com_texto_da_recuperacao(self):
        mock_response = io.BytesIO(b'{"id":"mensagem-teste"}')
        with patch('core.email_backend.urlopen', return_value=mock_response) as request:
            sent = ResendEmailBackend().send_messages([EmailMessage('Recuperar senha', 'Link de teste', 'SayIt <sayit@example.invalid>', ['aluna@example.invalid'])])
        self.assertEqual(sent, 1)
        args = request.call_args[0][0]
        self.assertEqual(args.full_url, 'https://api.resend.com/emails')
        self.assertEqual(json.loads(args.data)['text'], 'Link de teste')

    def test_erro_do_provedor_nao_expoe_conteudo(self):
        error = HTTPError('https://api.resend.com/emails', 403, 'recusado', {}, io.BytesIO(b'dados privados'))
        with patch('core.email_backend.urlopen', side_effect=error):
            with self.assertRaisesRegex(RuntimeError, 'HTTP 403'):
                ResendEmailBackend().send_messages([EmailMessage('Senha', 'privado', 'sayit@example.invalid', ['aluna@example.invalid'])])

    @override_settings(RESEND_API_KEY='')
    def test_sem_chave_envio_silencioso_retorna_zero(self):
        self.assertEqual(ResendEmailBackend(fail_silently=True).send_messages([EmailMessage('Senha', 'privado', 'sayit@example.invalid', ['aluna@example.invalid'])]), 0)
