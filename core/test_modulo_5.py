from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from core import progresso
from core.models import Modulo, Progresso, Tentativa


class Modulo5Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())
        cls.usuario = get_user_model().objects.create_user(username='modulo5', email='m5@test.com')
        cls.modulo = Modulo.objects.get(numero=5)
        cls.pares = list(cls.modulo.comparacoes.select_related(
            'palavra_base', 'palavra_comparada').order_by('ordem'))

    def setUp(self):
        acesso = patch('core.progresso.modulo_pode_ser_acessado', return_value=True)
        acesso.start()
        self.addCleanup(acesso.stop)
        self.client.force_login(self.usuario)

    def url(self, ordem):
        return reverse('descoberta_modulo', args=[5, ordem])

    def acertar(self, indice, segunda=False, texto=None):
        par = self.pares[indice]
        palavra = par.palavra_comparada if segunda else par.palavra_base
        return self.client.post(reverse('registrar_acerto', args=[5]), {
            'comparacao_id': par.pk, 'palavra_id': palavra.pk,
            'transcricao': palavra.palavra if texto is None else texto,
        }, content_type='application/json')

    def completar(self):
        for i in range(3):
            self.assertEqual(self.acertar(i).status_code, 200)
            self.assertEqual(self.acertar(i, True).status_code, 200)

    def test_catalogo_explicacao_e_trilha(self):
        self.assertEqual(list(self.modulo.palavras.values_list('palavra', flat=True)),
                         ['ship', 'fish', 'shark', 'sheep', 'shop', 'shovel'])
        self.assertEqual([(p.palavra_base.palavra, p.palavra_comparada.palavra) for p in self.pares],
                         [('ship', 'fish'), ('shark', 'sheep'), ('shop', 'shovel')])
        r = self.client.get(reverse('explicacao_modulo_5'))
        self.assertTemplateUsed(r, 'core/explicacao_modulo.html')
        self.assertContains(r, 'O SOM SH')
        self.assertContains(r, self.modulo.conteudo_teorico)
        self.assertNotContains(r, 'Magic E')
        self.assertContains(r, self.url(1))
        self.assertNotContains(self.client.get(reverse('trilha')), reverse('explicacao_modulo_5'))

    def test_carga_idempotente_preserva_acertos_e_midias(self):
        self.acertar(0)
        palavra = self.pares[0].palavra_base
        palavra.imagem = 'palavras/imagens/ship.webp'
        palavra.save(update_fields=['imagem'])
        ids = list(self.modulo.comparacoes.values_list('pk', flat=True))
        call_command('popular_sayit', stdout=StringIO())
        palavra.refresh_from_db()
        self.assertEqual(palavra.imagem.name, 'palavras/imagens/ship.webp')
        self.assertEqual(list(self.modulo.comparacoes.values_list('pk', flat=True)), ids)
        self.assertEqual(Tentativa.objects.count(), 1)
        self.assertTrue(all('E final' not in p.explicacao for p in self.modulo.comparacoes.all()))

    def test_carga_limitada_nao_modifica_modulos_anteriores(self):
        Modulo.objects.filter(numero=4).update(ativo=False, conteudo_teorico='Conteúdo preservado')
        antes = list(Modulo.objects.filter(numero__lt=5).values())
        call_command('popular_sayit', modulo=5, stdout=StringIO())
        self.assertEqual(list(Modulo.objects.filter(numero__lt=5).values()), antes)

    def test_tres_etapas_dois_acertos_e_percentuais(self):
        for i in range(3):
            r = self.client.get(self.url(i + 1))
            self.assertTemplateUsed(r, 'core/descoberta_modulo_1.html')
            self.assertContains(r, 'data-modulo="5"')
            self.assertContains(r, 'descobertas_microfone.js')
            self.assertContains(r, 'pronuncia.js')
            self.assertContains(r, 'type="button" disabled aria-describedby="speech-status"')
            self.assertEqual(self.acertar(i).json()['percentual'], i * 100 // 3)
            parcial = self.client.get(self.url(i + 1))
            self.assertEqual([c['acertada'] for c in parcial.context['cards']], [True, False])
            self.assertFalse(parcial.context['descoberta_concluida'])
            self.assertEqual(self.acertar(i, True).json()['percentual'], (i + 1) * 100 // 3)
            final = self.client.get(self.url(i + 1))
            self.assertTrue(final.context['descoberta_concluida'])
            self.assertEqual(final.context['proxima_url'], self.url(i + 2) if i < 2 else reverse('resumo_modulo_5'))
        self.assertEqual(Tentativa.objects.count(), 6)
        self.assertIsNone(Progresso.objects.get().concluido_em)

    def test_bloqueio_de_salto_resumo_e_conclusao(self):
        for ordem in (2, 3):
            self.assertEqual(self.client.get(self.url(ordem)).status_code, 409)
        self.assertEqual(self.acertar(1).status_code, 409)
        self.assertEqual(self.client.get(reverse('resumo_modulo_5')).status_code, 409)
        self.assertEqual(self.client.get(reverse('conclusao_modulo_5')).status_code, 409)
        self.assertEqual(self.client.post(reverse('conclusao_modulo_5')).status_code, 409)
        self.assertFalse(Progresso.objects.exists())

    def test_erro_silencio_palavras_distintas_e_reenvio(self):
        for texto in ('wrong', '', ' ... ', 'fish', 'sheep'):
            self.assertEqual(self.acertar(0, texto=texto).status_code, 400)
        self.assertFalse(Tentativa.objects.exists())
        self.assertEqual(self.acertar(0, texto='  SHIP!...  ').status_code, 200)
        self.acertar(0)
        self.assertEqual(Tentativa.objects.count(), 1)
        self.assertEqual(Progresso.objects.get().percentual, 0)

    def test_persistencia_logout_login_e_isolamento(self):
        self.acertar(0)
        self.client.logout()
        self.client.force_login(self.usuario)
        r = self.client.get(self.url(1))
        self.assertEqual([c['acertada'] for c in r.context['cards']], [True, False])
        self.assertFalse(r.context['descoberta_concluida'])
        self.assertEqual(self.client.get(self.url(2)).status_code, 409)
        self.assertEqual([e['modulo'].numero for e in progresso.consultar_meu_progresso(self.usuario)], [1, 2, 3, 5])
        self.assertFalse(Progresso.objects.exclude(modulo=self.modulo).exists())
        outro = get_user_model().objects.create_user(username='outro5', email='outro5@test.com')
        self.client.force_login(outro)
        self.assertEqual([c['acertada'] for c in self.client.get(self.url(1)).context['cards']], [False, False])

    def test_resumo_reutiliza_player_e_so_post_conclui(self):
        self.completar()
        with patch('core.views.default_storage') as storage:
            storage.exists.return_value = True
            storage.size.return_value = 100
            storage.url.return_value = '/media/modulos/5/resumo.mp3'
            r = self.client.get(reverse('resumo_modulo_5'))
        storage.exists.assert_called_once_with('modulos/5/resumo.mp3')
        self.assertTemplateUsed(r, 'core/resumo_modulo.html')
        for texto in ('O som SH', '/media/modulos/5/resumo.mp3', 'resumo_audio.js', 'Ouvir explicação novamente'):
            self.assertContains(r, texto)
        self.assertEqual(len(r.context['pares']), 3)
        self.assertEqual(self.client.get(reverse('conclusao_modulo_5')).status_code, 409)
        self.assertRedirects(self.client.post(reverse('conclusao_modulo_5')), reverse('conclusao_modulo_5'))
        data = Progresso.objects.get().concluido_em
        self.client.post(reverse('conclusao_modulo_5'))
        self.assertEqual(Progresso.objects.get().concluido_em, data)
        self.assertEqual(Progresso.objects.get().percentual, 100)

    def test_resumo_sem_audio_vazio_ou_storage_indisponivel(self):
        self.completar()
        for existe, tamanho, erro in ((False, 0, None), (True, 0, None), (True, 100, OSError)):
            with self.subTest(existe=existe, tamanho=tamanho, erro=erro), patch('core.views.default_storage') as storage:
                storage.exists.return_value = existe
                storage.size.return_value = tamanho
                storage.exists.side_effect = erro
                r = self.client.get(reverse('resumo_modulo_5'))
            self.assertNotContains(r, '<audio')
            self.assertContains(r, 'Concluir módulo')

    def test_continuar_para_modulo_6_implementado_e_fallback_se_inativo(self):
        self.completar()
        self.client.post(reverse('conclusao_modulo_5'))
        r = self.client.get(reverse('conclusao_modulo_5'))
        destino = reverse('explicacao_modulo_6')
        self.assertContains(r, f'href="{destino}"')
        self.assertEqual(r.context['proximo_url'], destino)
        self.assertEqual(self.client.get(destino).status_code, 200)
        Modulo.objects.filter(numero=6).update(ativo=False)
        r = self.client.get(reverse('conclusao_modulo_5'))
        self.assertContains(r, 'O próximo módulo estará disponível em breve.')
        self.assertContains(r, f'class="practice-link" href="{reverse("trilha")}"')

    def test_midias_reais_associacao_e_renderizacao(self):
        from core.management.commands.associar_audios import Command as Audios
        from core.management.commands.associar_imagens import Command as Imagens
        saida = StringIO()
        call_command('associar_imagens', modulo=5, dry_run=True, stdout=saida)
        self.assertIn('Registros que seriam associados: 6', saida.getvalue())
        self.assertFalse(self.modulo.palavras.exclude(imagem='').exists())
        call_command('associar_imagens', modulo=5, stdout=StringIO())
        call_command('associar_audios', modulo=5, stdout=StringIO())
        for i, par in enumerate(self.pares):
            r = self.client.get(self.url(i + 1))
            for palavra in (par.palavra_base, par.palavra_comparada):
                palavra.refresh_from_db()
                self.assertEqual(palavra.imagem.name, f'palavras/imagens/{palavra.palavra}.webp')
                self.assertEqual(palavra.audio.name, f'palavras/audios/{palavra.palavra}.mp3')
                self.assertEqual(Imagens.validar_webp(Path(palavra.imagem.path))[0], 'valido')
                self.assertEqual(Audios.validar_mp3(Path(palavra.audio.path))[0], 'valido')
                self.assertContains(r, palavra.imagem.url)
                self.assertContains(r, palavra.audio.url)
            self.acertar(i)
            self.acertar(i, True)
        self.assertEqual(Audios.validar_mp3(Path(settings.MEDIA_ROOT) / 'modulos/5/resumo.mp3')[0], 'valido')

    def test_autenticacao_csrf_e_catalogo_incompleto(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        self.assertEqual(client.post(reverse('conclusao_modulo_5')).status_code, 403)
        self.client.logout()
        for url in (self.url(1), reverse('explicacao_modulo_5'), reverse('resumo_modulo_5'), reverse('conclusao_modulo_5')):
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.usuario)
        self.pares[-1].delete()
        self.assertEqual(self.client.post(reverse('conclusao_modulo_5')).status_code, 409)
