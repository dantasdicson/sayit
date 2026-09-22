"""Fluxo HTTP real; não substitui navegador, reprodução ou pronúncia humana."""
from http.cookies import SimpleCookie
from io import StringIO
import json
import re
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.management import call_command
from django.test import override_settings
from django.urls import re_path
from django.views.static import serve

from core.models import Modulo, Progresso
from sayit.urls import urlpatterns as project_patterns

urlpatterns = [*project_patterns, re_path(
    r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT})]


@override_settings(ROOT_URLCONF=__name__)
class Modulo5HTTPTests(StaticLiveServerTestCase):
    host = '127.0.0.1'

    def test_fluxo_http_completo_com_assets_e_csrf(self):
        call_command('popular_sayit', stdout=StringIO())
        call_command('associar_imagens', modulo=5, stdout=StringIO())
        call_command('associar_audios', modulo=5, stdout=StringIO())
        usuario = get_user_model().objects.create_user(username='http5', email='http5@test.com')
        self.client.force_login(usuario)
        cookies = {settings.SESSION_COOKIE_NAME: self.client.cookies[settings.SESSION_COOKIE_NAME].value}
        checked_assets = set()

        def request(url, payload=None, form=False):
            headers = {'Cookie': '; '.join(f'{key}={value}' for key, value in cookies.items())}
            data = None
            if payload is not None:
                headers['X-CSRFToken'] = cookies[settings.CSRF_COOKIE_NAME]
                headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
                data = b'' if form else json.dumps(payload).encode()
            with urlopen(Request(self.live_server_url + url, data=data, headers=headers), timeout=10) as response:
                self.assertEqual(response.status, 200, url)
                for header in response.headers.get_all('Set-Cookie', []):
                    cookies.update({key: value.value for key, value in SimpleCookie(header).items()})
                return response.read(), response.headers.get_content_type()

        def page(url):
            content, content_type = request(url)
            self.assertEqual(content_type, 'text/html')
            html = content.decode()
            for asset in set(re.findall(r'(?:src|href)="((?:/static/|/media/)[^"]+)"', html)):
                if asset in checked_assets:
                    continue
                body, kind = request(asset)
                self.assertTrue(body, asset)
                self.assertNotEqual(kind, 'text/html', asset)
                checked_assets.add(asset)
            return html

        self.assertIn('/modulos/5/explicacao/', page('/trilha/'))
        self.assertIn('/modulos/5/descobertas/1/', page('/modulos/5/explicacao/'))
        pares = Modulo.objects.get(numero=5).comparacoes.select_related('palavra_base', 'palavra_comparada')
        for par in pares:
            url = f'/modulos/5/descobertas/{par.ordem}/'
            self.assertIn('type="button" disabled aria-describedby="speech-status"', page(url))
            for index, palavra in enumerate((par.palavra_base, par.palavra_comparada)):
                body, kind = request('/modulos/5/progresso/acertos/', {
                    'comparacao_id': par.pk, 'palavra_id': palavra.pk,
                    'transcricao': palavra.palavra.upper() + '!',
                })
                self.assertEqual(kind, 'application/json')
                estado = json.loads(body)
                self.assertEqual(estado['percentual'], (par.ordem - 1 + index) * 100 // 3)
                html = page(url)
                self.assertEqual('type="button" disabled aria-describedby="speech-status"' in html, index == 0)
        self.assertIn('/media/modulos/5/resumo.mp3', page('/modulos/5/resumo/'))
        content, _ = request('/modulos/5/conclusao/', {}, form=True)
        self.assertIn('Continuar para o próximo módulo', content.decode())
        self.assertIn('/modulos/6/explicacao/', content.decode())
        page('/trilha/')
        estado = Progresso.objects.get(usuario=usuario, modulo__numero=5)
        self.assertEqual(estado.percentual, 100)
        self.assertIsNotNone(estado.concluido_em)
