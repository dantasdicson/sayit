from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from core import progresso
from core.models import Comparacao, Modulo, Palavra, Progresso, Tentativa


class Modulo2Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())
        cls.usuario = get_user_model().objects.create_user(username='modulo2', email='m2@test.com')
        cls.outro = get_user_model().objects.create_user(username='outro2', email='other@test.com')
        cls.modulo = Modulo.objects.get(numero=2)
        cls.pares = list(cls.modulo.comparacoes.select_related('palavra_base', 'palavra_comparada').order_by('ordem'))

    def setUp(self):
        acesso = patch('core.progresso.modulo_pode_ser_acessado', return_value=True)
        acesso.start()
        self.addCleanup(acesso.stop)
        self.client.force_login(self.usuario)

    def url(self, ordem):
        return reverse('descoberta_modulo', args=[2, ordem])

    def acertar(self, indice, segunda=False):
        par = self.pares[indice]
        palavra = par.palavra_comparada if segunda else par.palavra_base
        return self.client.post(reverse('registrar_acerto', args=[2]), {
            'comparacao_id': par.pk, 'palavra_id': palavra.pk, 'transcricao': palavra.palavra,
        }, content_type='application/json')

    def completar(self):
        for i in range(4):
            self.assertEqual(self.acertar(i).status_code, 200)
            self.assertEqual(self.acertar(i, True).status_code, 200)

    def test_catalogo_e_explicacao(self):
        self.assertEqual([(p.palavra_base.palavra, p.palavra_comparada.palavra) for p in self.pares],
                         [('bit', 'bite'), ('fin', 'pin'), ('pin', 'pine'), ('sit', 'site')])
        r = self.client.get(reverse('explicacao_modulo_2'))
        self.assertContains(r, 'MAGIC E — SOM DO I')
        self.assertContains(r, self.modulo.conteudo_teorico)
        self.assertContains(r, self.url(1))
        self.assertNotContains(self.client.get(reverse('trilha')), reverse('explicacao_modulo_2'))

    def test_substituicao_pin_pine_preserva_ids_e_associa_midias(self):
        par = self.pares[2]
        ids = (par.pk, par.palavra_base_id, par.palavra_comparada_id)
        Palavra.objects.filter(pk=ids[1]).update(palavra='fin', traducao='barbatana')
        Palavra.objects.filter(pk=ids[2]).update(palavra='fine', traducao='bem')
        call_command('popular_sayit', modulo=2, stdout=StringIO())
        call_command('popular_sayit', modulo=2, stdout=StringIO())
        par.refresh_from_db()
        self.assertEqual((par.pk, par.palavra_base_id, par.palavra_comparada_id), ids)
        self.assertEqual((par.palavra_base.palavra, par.palavra_comparada.palavra), ('pin', 'pine'))
        self.assertEqual(self.modulo.palavras.count(), 7)
        call_command('associar_imagens', modulo=2, stdout=StringIO())
        call_command('associar_audios', modulo=2, stdout=StringIO())
        for word in self.modulo.palavras.filter(palavra__in=['pin', 'pine']):
            self.assertTrue(word.imagem.storage.exists(word.imagem.name))
            self.assertTrue(word.audio.storage.exists(word.audio.name))

    def test_primeira_descoberta_reutiliza_template_e_estado(self):
        r = self.client.get(self.url(1))
        self.assertTemplateUsed(r, 'core/descoberta_modulo_1.html')
        self.assertContains(r, 'Descoberta 1 de 4')
        self.assertContains(r, 'data-modulo="2"')
        self.assertContains(r, f'data-comparacao-id="{self.pares[0].pk}"')
        self.assertContains(r, '/modulos/2/progresso/acertos/')
        self.assertContains(r, 'Áudio indisponível', count=2)
        self.assertContains(r, 'Imagem indisponível', count=2)
        self.assertEqual(r.context['proxima_url'], self.url(2))
        self.assertFalse(Tentativa.objects.exists())
        self.assertFalse(Progresso.objects.exists())

    def test_todas_descobertas_midias_e_dois_acertos(self):
        for i, par in enumerate(self.pares):
            for palavra in (par.palavra_base, par.palavra_comparada):
                palavra.audio = f'palavras/audios/{palavra.palavra}.mp3'
                palavra.imagem = f'palavras/imagens/{palavra.palavra}.webp'
                palavra.save(update_fields=['audio', 'imagem'])
            r = self.client.get(self.url(i + 1))
            for palavra in (par.palavra_base, par.palavra_comparada):
                self.assertContains(r, palavra.audio.url)
                self.assertContains(r, palavra.imagem.url)
                self.assertContains(r, f'aria-label="Ouvir {palavra.palavra}"')
            self.assertFalse(r.context['descoberta_concluida'])
            self.assertEqual(self.acertar(i).json()['percentual'], i * 100 // 4)
            parcial = self.client.get(self.url(i + 1))
            self.assertEqual([c['acertada'] for c in parcial.context['cards']], [True, False])
            self.assertFalse(parcial.context['descoberta_concluida'])
            self.assertEqual(self.acertar(i, True).json()['percentual'], (i + 1) * 100 // 4)
            antes = Tentativa.objects.count()
            final = self.client.get(self.url(i + 1))
            self.assertTrue(final.context['descoberta_concluida'])
            self.assertEqual(Tentativa.objects.count(), antes)
        self.assertEqual(final.context['proxima_url'], reverse('resumo_modulo_2'))
        self.assertIsNone(Progresso.objects.get().concluido_em)

    def test_sequencia_e_resumo_bloqueados(self):
        for ordem in (2, 3, 4):
            self.assertEqual(self.client.get(self.url(ordem)).status_code, 409)
        self.assertEqual(self.acertar(1).status_code, 409)
        self.assertEqual(self.client.get(reverse('resumo_modulo_2')).status_code, 409)
        self.assertEqual(self.client.post(reverse('conclusao_modulo_2')).status_code, 409)
        self.assertFalse(Progresso.objects.exists())

    def test_transcricao_incorreta_e_reenvio(self):
        par = self.pares[0]
        r = self.client.post(reverse('registrar_acerto', args=[2]), {
            'comparacao_id': par.pk, 'palavra_id': par.palavra_base_id, 'transcricao': 'cat',
        }, content_type='application/json')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Tentativa.objects.exists())
        self.acertar(0); self.acertar(0)
        self.assertEqual(Tentativa.objects.count(), 1)
        self.assertEqual(Progresso.objects.get().percentual, 0)

    def test_isolamento_modulos_e_usuarios(self):
        p1 = Progresso.objects.create(usuario=self.usuario, modulo=Modulo.objects.get(numero=1), percentual=25)
        antes = (p1.percentual, p1.atualizado_em, p1.concluido_em)
        self.completar()
        p1.refresh_from_db()
        self.assertEqual((p1.percentual, p1.atualizado_em, p1.concluido_em), antes)
        self.assertEqual(progresso.consultar_progresso(self.outro, 2)['percentual'], 0)
        self.assertEqual([e['modulo'].numero for e in progresso.consultar_meu_progresso(self.usuario)], [1, 2, 3])
        self.client.force_login(self.outro)
        self.assertFalse(self.client.get(self.url(1)).context['descoberta_concluida'])

    def test_resumo_sem_audio_e_conclusao_post_idempotente(self):
        self.completar()
        with patch('core.views.default_storage.exists', return_value=False):
            r = self.client.get(reverse('resumo_modulo_2'))
        self.assertContains(r, 'Magic E — Som do I')
        self.assertContains(r, 'method="post"')
        self.assertNotContains(r, '<audio')
        self.assertEqual(self.client.get(reverse('conclusao_modulo_2')).status_code, 409)
        self.assertIsNone(Progresso.objects.get().concluido_em)
        self.assertRedirects(self.client.post(reverse('conclusao_modulo_2')), reverse('conclusao_modulo_2'))
        data = Progresso.objects.get().concluido_em
        self.assertIsNotNone(data)
        self.client.post(reverse('conclusao_modulo_2'))
        self.client.get(reverse('conclusao_modulo_2'))
        self.assertEqual(Progresso.objects.get().concluido_em, data)

    def test_csrf_e_autenticacao(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        self.assertEqual(client.post(reverse('conclusao_modulo_2')).status_code, 403)
        self.completar()
        client.get(reverse('resumo_modulo_2'))
        self.assertEqual(client.post(reverse('conclusao_modulo_2'), {'csrfmiddlewaretoken': client.cookies['csrftoken'].value}).status_code, 302)
        self.client.logout()
        for url in (self.url(1), reverse('explicacao_modulo_2'), reverse('resumo_modulo_2'), reverse('conclusao_modulo_2')):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_ordem_invalida_e_modulo_inativo(self):
        self.assertEqual(self.client.get(self.url(4)).status_code, 404)
        self.modulo.ativo = False
        self.modulo.save(update_fields=['ativo'])
        self.assertEqual(self.client.get(self.url(1)).status_code, 404)

    def test_catalogo_incompleto_nao_conclui(self):
        self.pares[-1].delete()
        self.assertEqual(self.client.post(reverse('conclusao_modulo_2')).status_code, 409)
        self.assertFalse(Progresso.objects.exists())
