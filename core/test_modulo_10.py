from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.management import call_command
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from core import progresso, desafio_service as service
from core.desafio_avaliacao import avaliar, faixa, estrelas, arredondar
from core.desafio_config import DESAFIOS
from core.models import Modulo, Progresso, Tentativa, TentativaDesafio


class AvaliacaoFrasesTests(SimpleTestCase):
    def test_perfeita_e_normalizacao(self):
        for texto in ['I like cake.', ' I  LIKE CAKE! ', '\tI like cake\n']:
            r = avaliar(DESAFIOS[0].frase, texto, ('cake',))
            self.assertEqual(r['nota'], 100)
            self.assertEqual(r['reconhecidas'], 3)
            self.assertEqual(r['faltantes'], [])
            self.assertEqual(r['estrelas'], 5)

    def test_parcial_palavra_faltando(self):
        r = avaliar('The ship is on the moon.', 'The ship is on moon.', ('ship', 'moon'))
        self.assertEqual(r['nota'], 80)
        self.assertEqual(r['faltantes'], ['the'])
        self.assertEqual(r['reconhecidas'], 5)
        self.assertEqual(r['componentes']['completa'], 0)

    def test_palavra_importante_diferente(self):
        r = avaliar('The ship is big.', 'The sheep is big.', ('ship',))
        self.assertEqual(r['nota'], 45)
        self.assertEqual(r['importantes_faltantes'], ['ship'])
        self.assertEqual(r['extras'], ['sheep'])

    def test_ordem_repeticoes_e_extras(self):
        self.assertLess(avaliar('I like cake.', 'cake like I', ('cake',))['nota'], 70)
        r = avaliar(DESAFIOS[2].frase, 'The cute cat is on ship', DESAFIOS[2].importantes)
        self.assertEqual(r['faltantes'], ['the'])
        self.assertEqual(r['reconhecidas'], 6)
        self.assertLess(avaliar('I like cake', 'I like cake cake cake', ('cake',))['nota'], 100)

    def test_abaixo_igual_acima_de_70(self):
        for texto, nota in [('cake', 50), ('I cake', 70), ('I like cake', 100)]:
            r = avaliar('I like cake', texto, ('cake',))
            self.assertEqual(r['nota'], nota)
            self.assertEqual(r['aprovado'], nota >= 70)

    def test_silencio_e_diferentes(self):
        for texto in ['', '...', 'dog house tree']:
            self.assertEqual(avaliar('I like cake', texto, ('cake',))['nota'], 0)

    def test_sem_bypass_de_palavras_isoladas(self):
        self.assertEqual(avaliar('peach', 'beach', ('peach',))['nota'], 0)
        self.assertEqual(avaliar('cat', 'cats', ('cat',))['nota'], 0)

    def test_faixas_estrelas_media(self):
        for nota, titulo in [(0, 'Vamos tentar novamente!'), (49, 'Vamos tentar novamente!'),
                             (50, 'Continue praticando!'), (74, 'Continue praticando!'),
                             (75, 'Muito bem!'), (89, 'Muito bem!'), (90, 'Excelente!'), (100, 'Excelente!')]:
            self.assertEqual(faixa(nota)[0], titulo)
        for nota, n in [(0, 1), (49, 1), (50, 2), (69, 2), (70, 3), (79, 3), (80, 4), (89, 4), (90, 5), (100, 5)]:
            self.assertEqual(estrelas(nota), n)
        self.assertEqual(arredondar((90 + 80 + 95) / 3), 88)
        self.assertEqual(arredondar(88.5), 89)


class DesafioFinalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())
        call_command('associar_audios', stdout=StringIO())
        cls.usuario = get_user_model().objects.create_user(username='desafio', email='desafio@example.invalid')

    def setUp(self):
        self.client.force_login(self.usuario)

    def desbloquear(self):
        for modulo in Modulo.objects.filter(numero__lt=10):
            Progresso.objects.create(usuario=self.usuario, modulo=modulo,
                                     percentual=100, concluido_em=timezone.now())
            Tentativa.objects.bulk_create([
                Tentativa(usuario=self.usuario, palavra=p, resultado='correto')
                for p in modulo.palavras.filter(ativa=True)])

    def montar(self, numero=1, palavras=None):
        return self.client.post(reverse('montar_desafio_10', args=[numero]),
            {'palavras': palavras if palavras is not None else DESAFIOS[numero - 1].palavras},
            content_type='application/json')

    def falar(self, numero, texto):
        montagem = self.montar(numero)
        self.assertEqual(montagem.status_code, 200)
        return self.client.post(reverse('avaliar_desafio_10', args=[numero]),
            {'token': montagem.json()['token'], 'transcricao': texto}, content_type='application/json')

    def completar(self):
        for d in DESAFIOS:
            self.assertEqual(self.falar(d.numero, d.frase).status_code, 200)

    def test_autenticacao_e_bloqueio_ate_nove(self):
        self.assertEqual(self.client.get(reverse('explicacao_modulo_10')).status_code, 409)
        self.assertEqual(self.montar().status_code, 409)
        self.client.logout()
        for rota, args in [('explicacao_modulo_10', []), ('desafio_modulo_10', [1]), ('resumo_modulo_10', [])]:
            self.assertEqual(self.client.get(reverse(rota, args=args)).status_code, 302)
        self.assertEqual(self.montar().status_code, 302)

    def test_montagem_correta_e_errada(self):
        self.desbloquear()
        self.assertEqual(self.montar(palavras=['cake', 'I', 'like']).status_code, 400)
        self.assertEqual(self.montar(palavras=['I', 'like']).status_code, 400)
        self.assertEqual(self.montar().status_code, 200)
        self.assertFalse(TentativaDesafio.objects.exists())
        self.assertFalse(Progresso.objects.filter(modulo__numero=10).exists())

    def test_microfone_bloqueado_e_audio_reutilizado(self):
        self.desbloquear()
        r = self.client.get(reverse('desafio_modulo_10', args=[1]))
        self.assertContains(r, 'id="challenge-speak" class="sayit-button" type="button" disabled')
        self.assertContains(r, '/media/palavras/audios/cake.mp3')
        self.assertContains(r, 'Sua frase montada')
        self.assertContains(r, 'desafio_final.css')
        self.assertNotEqual([p for _, p in r.context['palavras']], DESAFIOS[0].palavras)

    def test_parcial_e_silencio_persistidos(self):
        self.desbloquear()
        for texto, nota in [('', 0), ('cake', 50)]:
            r = self.falar(1, texto)
            self.assertEqual(r.json()['avaliacao']['nota'], nota)
            self.assertFalse(r.json()['liberado'])
        self.assertEqual(TentativaDesafio.objects.count(), 2)
        self.assertEqual(self.client.get(reverse('desafio_modulo_10', args=[2])).status_code, 409)
        pagina = self.client.get(reverse('desafio_modulo_10', args=[1]))
        self.assertContains(pagina, 'Nenhuma fala reconhecida')
        self.assertContains(pagina, '50/100')

    def test_70_libera_so_proximo(self):
        self.desbloquear()
        self.assertEqual(self.falar(1, 'I cake').json()['avaliacao']['nota'], 70)
        self.assertEqual(self.client.get(reverse('desafio_modulo_10', args=[2])).status_code, 200)
        self.assertEqual(self.client.get(reverse('desafio_modulo_10', args=[3])).status_code, 409)
        self.assertEqual(Progresso.objects.get(usuario=self.usuario, modulo__numero=10).percentual, 33)

    def test_tres_desafios_melhor_media_e_progresso(self):
        self.desbloquear()
        anteriores = list(Progresso.objects.filter(modulo__numero__lt=10).values())
        for texto in ['I cake', 'I like cake.', 'cake']:
            self.falar(1, texto)
        self.falar(2, 'The ship is')
        self.assertEqual(self.falar(3, 'The cute cat is on ship').json()['final'], 85)
        estado = service.consultar(self.usuario)
        self.assertEqual([d['melhor'] for d in estado['desafios']], [100, 75, 81])
        self.assertEqual(estado['concluidos'], 3)
        registro = Progresso.objects.get(usuario=self.usuario, modulo__numero=10)
        self.assertEqual(registro.percentual, 100)
        self.assertIsNotNone(registro.concluido_em)
        self.assertEqual(anteriores, list(Progresso.objects.filter(modulo__numero__lt=10).values()))
        self.assertEqual(Tentativa.objects.count(), 72)
        painel = self.client.get(reverse('modulos'))
        self.assertEqual(painel.context['percentual_curso'], 100)
        self.assertEqual(painel.context['modulos_concluidos'], 10)
        self.assertIsNone(painel.context['proximo_modulo'])
        r = self.client.get(reverse('conclusao_modulo_10'))
        for texto in ['Parabéns! Você concluiu sua jornada no SayIt!', '85 / 100',
                      '10 de 10 módulos concluídos', 'Meu Progresso', 'Voltar à Home']:
            self.assertContains(r, texto)
        self.assertNotContains(r, 'revisão geral')
        self.falar(3, DESAFIOS[2].frase)
        registro.refresh_from_db()
        self.assertEqual(service.consultar(self.usuario)['final'], 92)
        self.assertEqual(registro.concluido_em, estado['concluido_em'])

    def test_sem_pular_montagem_ou_enviar_nota(self):
        self.desbloquear()
        url = reverse('avaliar_desafio_10', args=[1])
        self.assertEqual(self.client.post(url, {'token': '', 'transcricao': 'I like cake'}, content_type='application/json').status_code, 409)
        self.assertEqual(self.client.post(url, {'token': '', 'transcricao': 'I like cake', 'nota': 100}, content_type='application/json').status_code, 400)
        self.assertEqual(self.montar(2).status_code, 409)
        self.assertEqual(self.client.get(reverse('resumo_modulo_10')).status_code, 409)
        self.assertEqual(self.client.post(reverse('conclusao_modulo_10')).status_code, 409)

    def test_reenvio_idempotente_e_isolamento(self):
        self.desbloquear()
        dados = {'token': self.montar().json()['token'], 'transcricao': 'I like cake'}
        url = reverse('avaliar_desafio_10', args=[1])
        for _ in range(2):
            self.assertEqual(self.client.post(url, dados, content_type='application/json').status_code, 200)
        self.assertEqual(TentativaDesafio.objects.count(), 1)
        dados['transcricao'] = 'cake'
        self.assertEqual(self.client.post(url, dados, content_type='application/json').status_code, 409)
        outro = get_user_model().objects.create_user(username='outro', email='outro@example.invalid')
        self.client.force_login(outro)
        self.assertEqual(self.client.post(url, dados, content_type='application/json').status_code, 409)
        self.assertFalse(TentativaDesafio.objects.filter(usuario=outro).exists())

    def test_expiracao_e_limite_transcricao(self):
        self.desbloquear()
        token = self.montar().json()['token']
        url = reverse('avaliar_desafio_10', args=[1])
        with patch('core.desafio_service.load_ticket', side_effect=signing.SignatureExpired):
            self.assertEqual(self.client.post(url, {'token': token, 'transcricao': 'I like cake'}, content_type='application/json').status_code, 409)
        self.assertEqual(self.client.post(url, {'token': token, 'transcricao': 'x' * 256}, content_type='application/json').status_code, 400)

    def test_csrf_metodos_e_payload(self):
        self.desbloquear()
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.usuario)
        url = reverse('montar_desafio_10', args=[1])
        self.assertEqual(protegido.post(url, {'palavras': []}, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {'palavras': []}).status_code, 415)
        self.assertEqual(self.client.post(url, 'null', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.get(reverse('desafio_modulo_10', args=[4])).status_code, 404)

    def test_legado_preservado_sem_nota_inventada(self):
        self.desbloquear()
        registro = Progresso.objects.create(usuario=self.usuario, modulo=Modulo.objects.get(numero=10),
                                           percentual=100, concluido_em=timezone.now())
        data = registro.concluido_em
        self.assertIsNone(service.consultar(self.usuario)['final'])
        self.assertContains(self.client.get(reverse('explicacao_modulo_10')), 'versão anterior foi preservada')
        self.assertEqual(self.client.get(reverse('resumo_modulo_10')).status_code, 409)
        self.falar(1, 'cake')
        registro.refresh_from_db()
        self.assertEqual(registro.percentual, 100)
        self.assertEqual(registro.concluido_em, data)

    def test_rotas_antigas_nao_concluem(self):
        self.desbloquear()
        par = Modulo.objects.get(numero=10).comparacoes.first()
        self.assertEqual(self.client.post(reverse('registrar_acerto', args=[10]), {
            'comparacao_id': par.pk, 'palavra_id': par.palavra_base_id, 'transcricao': par.palavra_base.palavra,
        }, content_type='application/json').status_code, 409)
        self.assertEqual(self.client.post(reverse('concluir_modulo', args=[10]), {}, content_type='application/json').status_code, 409)
        self.assertRedirects(self.client.get(reverse('descoberta_modulo', args=[10, 1])), reverse('desafio_modulo_10', args=[1]))
        self.assertEqual(Tentativa.objects.count(), 72)

    def test_carga_preserva_historico_legado(self):
        modulo = Modulo.objects.get(numero=10)
        legado = modulo.palavras.get(palavra='kit')
        tentativa = Tentativa.objects.create(usuario=self.usuario, palavra=legado, resultado='correto')
        palavras, pares = list(modulo.palavras.values()), list(modulo.comparacoes.values())
        call_command('popular_sayit', modulo=10, stdout=StringIO())
        modulo.refresh_from_db()
        self.assertEqual(modulo.titulo, 'Desafio Final')
        self.assertEqual(list(modulo.palavras.values()), palavras)
        self.assertEqual(list(modulo.comparacoes.values()), pares)
        self.assertTrue(Tentativa.objects.filter(pk=tentativa.pk).exists())

    def test_fluxo_anterior_libera_desafio(self):
        for numero in range(1, 10):
            for par in Modulo.objects.get(numero=numero).comparacoes.order_by('ordem'):
                for palavra in (par.palavra_base, par.palavra_comparada):
                    progresso.registrar_acerto(self.usuario, numero, par.pk, palavra.pk, palavra.palavra)
            progresso.concluir_modulo(self.usuario, numero)
        self.assertEqual(self.client.get(reverse('explicacao_modulo_10')).status_code, 200)
        self.completar()
        self.assertEqual(self.client.get(reverse('modulos')).context['percentual_curso'], 100)
