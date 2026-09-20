from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, SimpleTestCase
from django.urls import reverse

from core import progresso
from core.models import Modulo, Tentativa
from core.pronuncia import VARIANTES, corresponde


class PronunciaTests(SimpleTestCase):
    def test_normalizacao_e_variantes(self):
        for text in ['fin', 'Finn', ' FIN! ', '\t Finn... \n']:
            self.assertTrue(corresponde('fin', progresso.normalizar_texto(text)))
        for text in ['10', 'fine', 'fins', 'fin fine', '']:
            self.assertFalse(corresponde('fin', progresso.normalizar_texto(text)))

    def test_pares_distintos(self):
        for a, b in [('cat', 'cake'), ('cap', 'cape'), ('kit', 'kite'), ('hop', 'hope'), ('cub', 'cube')]:
            self.assertFalse(corresponde(a, b))
            self.assertFalse(corresponde(b, a))


class PronunciaEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())
        cls.usuario = get_user_model().objects.create_user(username='pronuncia')
        cls.modulo = Modulo.objects.get(numero=2)

    def test_alias_backend_idempotente_e_numeral_recusado(self):
        self.client.force_login(self.usuario)
        pares = list(self.modulo.comparacoes.select_related('palavra_base', 'palavra_comparada').order_by('ordem'))
        for par in pares[:2]:
            for p in [par.palavra_base, par.palavra_comparada]:
                progresso.registrar_acerto(self.usuario, 2, par.pk, p.pk, p.palavra)
        par = pares[2]
        payload = dict(comparacao_id=par.pk, palavra_id=par.palavra_base_id, transcricao='10')
        url = reverse('registrar_acerto', args=[2])
        self.assertEqual(self.client.post(url, payload, content_type='application/json').status_code, 400)
        self.assertEqual(Tentativa.objects.count(), 4)
        for text in [' Finn! ', 'fin', 'Finn']:
            payload['transcricao'] = text
            r = self.client.post(url, payload, content_type='application/json')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['percentual'], 66)
        self.assertEqual(Tentativa.objects.count(), 5)
        self.assertEqual(Tentativa.objects.get(palavra=par.palavra_base).resposta_reconhecida, 'finn')

    def test_variantes_servidas_nos_dois_fluxos(self):
        self.client.force_login(self.usuario)
        for url in [reverse('descoberta_modulo', args=[2, 1]), reverse('pratica_modulo_1')]:
            r = self.client.get(url)
            self.assertEqual(r.context['pronuncia_variantes'], VARIANTES)
            self.assertContains(r, 'id="pronuncia-variantes"')
            self.assertContains(r, 'core/pronuncia.js')
