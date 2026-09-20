from datetime import timedelta
from io import StringIO

from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.hashers import identify_hasher
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Palavra, Tentativa


User = get_user_model()
PASSWORD = 'Brisa!Laranja-4829'


class AutenticacaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='aluna', email='aluna@example.com',
            password=PASSWORD, first_name='Ana', last_name='Silva', data_nascimento='2014-03-12')
        call_command('popular_sayit', stdout=StringIO())

    def cadastro(self, **changes):
        data = dict(nome_completo='Beatriz de Souza', data_nascimento='2015-06-15',
            username='beatriz', email='beatriz@example.com', password1=PASSWORD, password2=PASSWORD)
        data.update(changes)
        return self.client.post(reverse('cadastro'), data)

    def entrar(self, identifier='aluna', password=PASSWORD, **extra):
        return self.client.post(reverse('login'), {'username': identifier, 'password': password, **extra})

    def assertRejected(self, message, **changes):
        before = User.objects.count()
        response = self.cadastro(**changes)
        self.assertContains(response, message)
        self.assertEqual(User.objects.count(), before)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertNotContains(response, f'value="{PASSWORD}"')
        return response

    def test_cadastro_valido_salva_campos(self):
        self.assertRedirects(self.cadastro(), reverse('home'))
        user = User.objects.get(username='beatriz')
        self.assertEqual(user.get_full_name(), 'Beatriz de Souza')
        self.assertEqual(user.email, 'beatriz@example.com')
        self.assertEqual(user.data_nascimento.isoformat(), '2015-06-15')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_username_duplicado(self):
        self.assertRejected('Este nome de usuário já está em uso.', username='ALUNA')

    def test_email_duplicado(self):
        self.assertRejected('Este e-mail já está cadastrado.', email='ALUNA@EXAMPLE.COM')

    def test_banco_rejeita_email_duplicado_sem_formulario(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username='duplicada', email=self.user.email)
        outra = User.objects.create_user(username='outra', email='outra@example.com')
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=outra.pk).update(email=self.user.email)
        outra.refresh_from_db()
        self.assertEqual(outra.email, 'outra@example.com')
        self.assertEqual(User.objects.filter(email=self.user.email).count(), 1)

    def test_email_invalido(self):
        self.assertRejected('Digite um endereço de e-mail válido.', email='nao-email')

    def test_senhas_diferentes(self):
        self.assertRejected('As senhas não coincidem.', password2='Outra-senha!123')

    def test_data_futura(self):
        self.assertRejected('A data de nascimento não pode estar no futuro.',
            data_nascimento=(timezone.localdate() + timedelta(days=1)).isoformat())

    def test_data_invalida(self):
        self.assertRejected('Digite uma data de nascimento válida.', data_nascimento='2024-02-30')

    def test_data_hoje_sem_limite_de_idade(self):
        self.assertRedirects(self.cadastro(data_nascimento=timezone.localdate().isoformat()), reverse('home'))

    def test_todos_campos_obrigatorios(self):
        for field in ('nome_completo', 'data_nascimento', 'username', 'email', 'password1', 'password2'):
            with self.subTest(field=field):
                self.assertRejected('Preencha este campo.', **{field: ''})

    def test_hash_de_senha(self):
        self.cadastro()
        user = User.objects.get(username='beatriz')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertIsNotNone(identify_hasher(user.password))

    def test_login_automatico_apos_cadastro(self):
        self.cadastro()
        response = self.client.get(reverse('home'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, 'beatriz')

    def test_validadores_de_senha_do_django(self):
        for password, message in (
            ('Ab!2', 'Use uma senha com pelo menos 8 caracteres.'),
            ('password', 'Esta senha é muito comum. Escolha outra.'),
            ('829104738201', 'Misture letras e outros caracteres na senha.'),
            ('beatriz', 'Escolha uma senha diferente dos seus dados pessoais.'),
        ):
            with self.subTest(message=message):
                self.assertRejected(message, password1=password, password2=password)

    def test_login_username(self):
        self.assertRedirects(self.entrar(), reverse('home'))
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_login_email(self):
        self.assertRedirects(self.entrar('ALUNA@EXAMPLE.COM'), reverse('home'))
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_senha_incorreta(self):
        self.assertContains(self.entrar(password='errada'), 'Usuário/e-mail ou senha incorretos.')
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_usuario_inexistente(self):
        self.assertContains(self.entrar('inexistente'), 'Usuário/e-mail ou senha incorretos.')
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_usuario_inativo_mesma_mensagem(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertContains(self.entrar(), 'Usuário/e-mail ou senha incorretos.')
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_autenticado_login_vai_home_mesmo_com_next(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('login'), {'next': reverse('perfil')}), reverse('home'))

    def test_autenticado_cadastro_vai_home(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('cadastro')), reverse('home'))
        self.assertRedirects(self.cadastro(), reverse('home'))
        self.assertFalse(User.objects.filter(username='beatriz').exists())

    def test_sessao_persiste_request_user(self):
        self.entrar()
        key = self.client.session.session_key
        for route in ('home', 'trilha', 'perfil', 'home'):
            response = self.client.get(reverse(route))
            self.assertEqual(response.wsgi_request.user.pk, self.user.pk)
            self.assertTrue(response.wsgi_request.user.is_authenticated)
            self.assertEqual(self.client.session.session_key, key)

    def test_login_rotaciona_sessao(self):
        session = self.client.session
        session['antes'] = True
        session.save()
        old_key = session.session_key
        self.entrar()
        self.assertNotEqual(self.client.session.session_key, old_key)

    def test_logout_encerra_e_redireciona(self):
        self.entrar()
        self.assertRedirects(self.client.post(reverse('logout'), {'next': reverse('home')}), reverse('login'))
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertRedirects(self.client.get(reverse('home')), reverse('login') + '?next=/')

    def test_logout_get_nao_encerra(self):
        self.entrar()
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertIn(SESSION_KEY, self.client.session)

    def test_csrf_exigido_em_todos_formularios(self):
        client = Client(enforce_csrf_checks=True)
        for route in ('cadastro', 'login', 'logout'):
            self.assertEqual(client.post(reverse(route), {}).status_code, 403)
        client.force_login(self.user)
        self.assertContains(client.get(reverse('home')), 'csrfmiddlewaretoken')
        self.assertEqual(client.post(reverse('logout')).status_code, 403)
        token = client.cookies['csrftoken'].value
        self.assertRedirects(client.post(reverse('logout'), {'csrfmiddlewaretoken': token}), reverse('login'))

    def test_next_local_preservado(self):
        path = reverse('descoberta_modulo_1', args=[2])
        self.assertRedirects(self.client.get(path), reverse('login') + '?next=' + path)
        # O login preserva o destino, mas não libera uma Descoberta pendente.
        self.assertRedirects(self.entrar(next=path), path, target_status_code=409)

    def test_next_externo_rejeitado(self):
        for target in ('https://evil.example/', '//evil.example/', 'http://evil.example/', 'javascript:alert(1)'):
            with self.subTest(target=target):
                self.client.logout()
                self.assertRedirects(self.entrar(next=target), reverse('home'))

    def test_identificador_ambiguo_falha_seguro(self):
        User.objects.create_user(username=self.user.email, email='outra@example.com', password=PASSWORD)
        self.assertContains(self.entrar(self.user.email), 'Usuário/e-mail ou senha incorretos.')
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertRedirects(self.entrar(), reverse('home'))

    def test_cadastro_evita_colisao_username_email(self):
        self.assertRejected('Este nome de usuário já está em uso.', username=self.user.email)

    def test_formularios_publicos_e_sem_senha_renderizada(self):
        for route in ('login', 'cadastro'):
            response = self.client.get(reverse(route))
            self.assertContains(response, 'csrfmiddlewaretoken')
            self.assertContains(response, 'type="password"')
            self.assertContains(response, 'autocomplete=')

    def test_perfil_escapa_nome(self):
        User.objects.filter(pk=self.user.pk).update(first_name='<script>alert(1)</script>')
        self.client.force_login(self.user)
        response = self.client.get(reverse('perfil'))
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_cadastro_nao_cria_progresso_ou_sessao_pedagogica(self):
        self.cadastro()
        user = User.objects.get(username='beatriz')
        self.assertFalse(user.progressos.exists())
        self.assertFalse(user.sessoes.exists())
        self.assertFalse(user.tentativas.exists())


class ProtecaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='aluno')
        call_command('popular_sayit', stdout=StringIO())

    def assertProtected(self, path):
        self.assertRedirects(self.client.get(path), reverse('login') + '?next=' + path)

    def test_home_anonimo(self):
        self.assertProtected(reverse('home'))

    def test_trilha_anonimo(self):
        self.assertProtected(reverse('trilha'))

    def test_descoberta_anonimo(self):
        for numero in range(1, 5):
            self.assertProtected(reverse('descoberta_modulo_1', args=[numero]))

    def test_resumo_anonimo(self):
        self.assertProtected(reverse('resumo_modulo_1'))

    def test_demais_areas_anonimo(self):
        for name in ('modulos', 'progresso', 'perfil', 'explicacao_modulo_1', 'conclusao_modulo_1', 'pratica_modulo_1'):
            with self.subTest(name=name):
                self.assertProtected(reverse(name))

    def test_autenticado_acessa_todas_areas(self):
        self.client.force_login(self.user)
        # Satisfazer a sequência pedagógica para testar apenas a autenticação.
        Tentativa.objects.bulk_create([
            Tentativa(usuario=self.user, palavra=palavra, resultado='correto',
                      resposta_reconhecida=palavra.palavra)
            for palavra in Palavra.objects.filter(modulo__numero=1)
        ])
        paths = [reverse(name) for name in ('home', 'trilha', 'modulos', 'progresso', 'perfil',
            'explicacao_modulo_1', 'resumo_modulo_1', 'conclusao_modulo_1', 'pratica_modulo_1')]
        paths += [reverse('descoberta_modulo_1', args=[n]) for n in range(1, 5)]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'action="/logout/"')
