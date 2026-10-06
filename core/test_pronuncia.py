from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, SimpleTestCase
from django.urls import reverse

from core import progresso
from core.models import Modulo, Tentativa
from core.pronuncia import VARIANTES, corresponde


class PronunciaTests(SimpleTestCase):
    def test_excecao_bitch_para_beach(self):
        for text in ['bitch', 'Bitch', ' BITCH! ', 'b****', ' B****! ']:
            self.assertTrue(corresponde('beach', progresso.normalizar_texto(text)))
            self.assertFalse(corresponde('beach', 'bite'))
        for text in ['bitches', 'beach bitch', 'b***', 'b*****', '']:
            self.assertFalse(corresponde('beach', text))

    def test_excecao_kane_restrita_a_cane(self):
        for text in ['kane', 'Kane', ' KANE! ']:
            self.assertTrue(corresponde('cane', progresso.normalizar_texto(text)))
            self.assertFalse(corresponde('can', progresso.normalizar_texto(text)))
        for text in ['can', 'kanes', 'kane cane', '']:
            self.assertFalse(corresponde('cane', text))

    def test_excecao_bitch_restrita_a_bit(self):
        for text in ['bitch', 'Bitch', ' BITCH! ']:
            self.assertTrue(corresponde('bit', progresso.normalizar_texto(text)))
            self.assertFalse(corresponde('bite', progresso.normalizar_texto(text)))
        for text in ['bite', 'bitches', 'bit bitch', '']:
            self.assertFalse(corresponde('bit', text))

    def test_normalizacao_e_variantes(self):
        for text in ['fine', 'ten', '10', 'fin', 'Finn', ' FIN! ', '\t Finn... \n']:
            self.assertTrue(corresponde('fin', progresso.normalizar_texto(text)))
        for text in ['fins', 'fin fine', '']:
            self.assertFalse(corresponde('fin', progresso.normalizar_texto(text)))

    def test_excecao_cats_apenas_para_cat(self):
        for text in ['cats', 'Cats', ' CATS! ']:
            self.assertTrue(corresponde('cat', progresso.normalizar_texto(text)))
            self.assertFalse(corresponde('cake', progresso.normalizar_texto(text)))
        for text in ['caps', 'cat cake', 'catfish']:
            self.assertFalse(corresponde('cat', text))

    def test_excecao_matt_apenas_para_mad(self):
        for text in ['matt', 'Matt', ' MATT! ']:
            self.assertTrue(corresponde('mad', progresso.normalizar_texto(text)))
            self.assertFalse(corresponde('made', progresso.normalizar_texto(text)))
        for text in ['made', 'mat', 'matt made']:
            self.assertFalse(corresponde('mad', text))

    def test_pares_distintos(self):
        for a, b in [('cat', 'cake'), ('cap', 'cape'), ('sit', 'site'), ('hop', 'hope'), ('cub', 'cube')]:
            self.assertFalse(corresponde(a, b))
            self.assertFalse(corresponde(b, a))


class PronunciaEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())
        cls.usuario = get_user_model().objects.create_user(username='pronuncia')
        cls.modulo = Modulo.objects.get(numero=2)

    def setUp(self):
        acesso = patch('core.progresso.modulo_pode_ser_acessado', return_value=True)
        acesso.start()
        self.addCleanup(acesso.stop)

    def test_pin_backend_idempotente_e_distinto_de_pine(self):
        self.client.force_login(self.usuario)
        pares = list(self.modulo.comparacoes.select_related('palavra_base', 'palavra_comparada').order_by('ordem'))
        for par in pares[:2]:
            for p in [par.palavra_base, par.palavra_comparada]:
                progresso.registrar_acerto(self.usuario, 2, par.pk, p.pk, p.palavra)
        par = pares[2]
        payload = dict(comparacao_id=par.pk, palavra_id=par.palavra_base_id, transcricao='eleven')
        url = reverse('registrar_acerto', args=[2])
        self.assertEqual(self.client.post(url, payload, content_type='application/json').status_code, 400)
        self.assertEqual(Tentativa.objects.count(), 4)
        for text in ['pine', 'fin', 'fine', 'ten', '10']:
            payload['transcricao'] = text
            self.assertEqual(self.client.post(url, payload, content_type='application/json').status_code, 400)
        for text in [' PIN! ', 'pin', 'Pin']:
            payload['transcricao'] = text
            r = self.client.post(url, payload, content_type='application/json')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['percentual'], 50)
        self.assertEqual(Tentativa.objects.count(), 5)
        self.assertEqual(Tentativa.objects.get(palavra=par.palavra_base).resposta_reconhecida, 'pin')

    def test_cats_registra_acerto_de_cat(self):
        self.client.force_login(self.usuario)
        par = Modulo.objects.get(numero=1).comparacoes.get(ordem=1)
        response = self.client.post(reverse('registrar_acerto', args=[1]),
            dict(comparacao_id=par.pk, palavra_id=par.palavra_base_id, transcricao='Cats!'),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn(par.palavra_base_id, response.json()['palavras_acertadas'])
        self.assertEqual(Tentativa.objects.get(usuario=self.usuario).resposta_reconhecida, 'cats')

    def test_excecao_bit_registra_acerto_mas_nao_aceita_para_bite(self):
        self.client.force_login(self.usuario)
        par = self.modulo.comparacoes.get(ordem=1)
        url = reverse('registrar_acerto', args=[2])
        payload = dict(comparacao_id=par.pk, palavra_id=par.palavra_base_id, transcricao='Bitch!')
        self.assertEqual(self.client.post(url, payload, content_type='application/json').status_code, 200)
        self.assertEqual(Tentativa.objects.get(usuario=self.usuario).resposta_reconhecida, 'bitch')
        payload['palavra_id'] = par.palavra_comparada_id
        self.assertEqual(self.client.post(url, payload, content_type='application/json').status_code, 400)
        self.assertEqual(Tentativa.objects.filter(usuario=self.usuario).count(), 1)

    def test_variantes_servidas_nos_dois_fluxos(self):
        self.client.force_login(self.usuario)
        for url in [reverse('descoberta_modulo', args=[2, 1]), reverse('pratica_modulo_1')]:
            r = self.client.get(url)
            self.assertEqual(r.context['pronuncia_variantes'], VARIANTES)
            self.assertContains(r, 'id="pronuncia-variantes"')
            self.assertContains(r, 'core/pronuncia.js')

    def test_beach_censurada_registra_acerto_no_modulo_6(self):
        self.client.force_login(self.usuario)
        modulo = Modulo.objects.get(numero=6)
        par = modulo.comparacoes.get(palavra_comparada__palavra='beach')
        for anterior in modulo.comparacoes.filter(ordem__lt=par.ordem).order_by('ordem'):
            for palavra in [anterior.palavra_base, anterior.palavra_comparada]:
                progresso.registrar_acerto(self.usuario, 6, anterior.pk, palavra.pk, palavra.palavra)
        progresso.registrar_acerto(self.usuario, 6, par.pk, par.palavra_base_id, par.palavra_base.palavra)
        response = self.client.post(reverse('registrar_acerto', args=[6]),
            dict(comparacao_id=par.pk, palavra_id=par.palavra_comparada_id, transcricao='b****'),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn(par.palavra_comparada_id, response.json()['palavras_acertadas'])
        self.assertEqual(Tentativa.objects.get(usuario=self.usuario, palavra=par.palavra_comparada).resposta_reconhecida, 'b****')
