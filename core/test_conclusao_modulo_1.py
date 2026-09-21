from io import StringIO
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from core.models import Modulo, Palavra, Progresso, Tentativa

class ConclusaoModulo1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_sayit', stdout=StringIO())
        cls.usuario = get_user_model().objects.create_user(username='conclusao_teste')

    def setUp(self):
        self.client.force_login(self.usuario)

    def completar(self):
        Tentativa.objects.bulk_create([
            Tentativa(usuario=self.usuario, palavra=p, resultado='correto')
            for p in Palavra.objects.filter(modulo__numero=1)
        ])

    def test_conclui_redireciona_e_preserva_data_em_reenvio(self):
        self.completar()
        url = reverse('conclusao_modulo_1')
        self.assertRedirects(self.client.post(url), reverse('explicacao_modulo_2'))
        registro = Progresso.objects.get(usuario=self.usuario, modulo__numero=1)
        self.assertEqual(registro.percentual, 100)
        self.assertIsNotNone(registro.concluido_em)
        data = registro.concluido_em
        self.client.post(url)
        registro.refresh_from_db()
        self.assertEqual(registro.concluido_em, data)
        self.assertFalse(Progresso.objects.filter(modulo__numero=2).exists())

    def test_modulo_2_indisponivel_retorna_meus_modulos(self):
        self.completar()
        Modulo.objects.filter(numero=2).update(ativo=False)
        self.assertRedirects(self.client.post(reverse('conclusao_modulo_1')), reverse('modulos'))

    def test_incompleto_nao_conclui(self):
        self.assertEqual(self.client.post(reverse('conclusao_modulo_1')).status_code, 409)
        self.assertFalse(Progresso.objects.exists())

    def test_get_nao_grava_e_post_exige_csrf(self):
        self.completar()
        self.client.get(reverse('conclusao_modulo_1'))
        self.assertFalse(Progresso.objects.exists())
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        self.assertEqual(client.post(reverse('conclusao_modulo_1')).status_code, 403)
        client.get(reverse('resumo_modulo_1'))
        self.assertRedirects(client.post(reverse('conclusao_modulo_1'),
            {'csrfmiddlewaretoken': client.cookies['csrftoken'].value}), reverse('explicacao_modulo_2'))
