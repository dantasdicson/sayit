from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from datetime import date, timedelta
from io import StringIO
from unittest.mock import patch
from django.core.management import call_command

from .models import Modulo, Palavra, Progresso, Sessao, Tentativa


class PopularSayitTests(TestCase):
    def test_popula_e_atualiza_sem_duplicar(self):
        call_command("popular_sayit", stdout=StringIO())
        self.assertEqual(Modulo.objects.count(), 10)
        self.assertEqual(Palavra.objects.count(), 71)
        modulo = Modulo.objects.get(ordem=1)
        palavra = modulo.palavras.get(texto="cat")
        ids = list(Palavra.objects.order_by("pk").values_list("pk", flat=True))
        palavra.traducao = "alterada"
        palavra.ativa = False
        palavra.dica = "Dica personalizada"
        palavra.save()
        call_command("popular_sayit", stdout=StringIO())
        palavra.refresh_from_db()
        self.assertEqual(Modulo.objects.count(), 10)
        self.assertEqual(list(Palavra.objects.order_by("pk").values_list("pk", flat=True)), ids)
        self.assertEqual(palavra.traducao, "gato")
        self.assertTrue(palavra.ativa)
        self.assertEqual(palavra.dica, "Dica personalizada")
        self.assertEqual(Palavra.objects.filter(texto="cat").count(), 2)
        self.assertEqual(Modulo.objects.get(ordem=10).palavras.count(), 14)

    def test_falha_desfaz_populacao(self):
        with patch.object(Palavra.objects, "update_or_create", side_effect=RuntimeError("Falha simulada")):
            with self.assertRaises(RuntimeError):
                call_command("popular_sayit", stdout=StringIO())
        self.assertFalse(Modulo.objects.exists())
        self.assertFalse(Palavra.objects.exists())


class ModelosTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="ana", password="senha-teste", data_nascimento=date(2000, 1, 1)
        )
        self.modulo = Modulo.objects.create(nome="Básico")
        self.palavra = Palavra.objects.create(modulo=self.modulo, texto="Olá")

    def test_fluxo_com_usuario_personalizado(self):
        self.assertTrue(self.usuario.check_password("senha-teste"))
        self.assertEqual(self.usuario.data_nascimento, date(2000, 1, 1))
        sessao = Sessao.objects.create(usuario=self.usuario)
        tentativa = Tentativa.objects.create(usuario=self.usuario, sessao=sessao, palavra=self.palavra, resposta_reconhecida="Olá", resultado=Tentativa.Resultado.CORRETO, pontuacao=10, feedback="Muito bem!")
        Progresso.objects.create(usuario=self.usuario, modulo=self.modulo, percentual=100)
        self.assertEqual(tentativa.sessao.usuario, self.usuario)
        with self.assertRaises(ProtectedError):
            self.palavra.delete()
        self.usuario.delete()
        self.assertFalse(Tentativa.objects.exists())
        self.assertFalse(Progresso.objects.exists())

    def test_resultados_e_tentativa_sem_sessao(self):
        for resultado in Tentativa.Resultado.values:
            tentativa = Tentativa(usuario=self.usuario, palavra=self.palavra, resultado=resultado)
            tentativa.full_clean()
            tentativa.save()
            tentativa.refresh_from_db()
            self.assertEqual(tentativa.resultado, resultado)
            self.assertIsNotNone(tentativa.data_hora)
        self.assertEqual(self.usuario.tentativas.count(), 3)

    def test_sessao_de_outro_usuario_rejeitada_na_validacao(self):
        outro = get_user_model().objects.create_user(username="outro")
        sessao = Sessao.objects.create(usuario=outro)
        tentativa = Tentativa(usuario=self.usuario, sessao=sessao, palavra=self.palavra)
        with self.assertRaises(ValidationError):
            tentativa.full_clean()

    def test_restricoes_no_banco(self):
        Progresso.objects.create(usuario=self.usuario, modulo=self.modulo)
        invalidos = [
            lambda: Tentativa.objects.create(usuario=self.usuario, palavra=self.palavra, resultado="invalido"),
            lambda: Tentativa.objects.create(usuario=self.usuario, palavra=self.palavra, pontuacao=-1),
            lambda: Progresso.objects.create(usuario=self.usuario, modulo=self.modulo),
            lambda: Progresso.objects.filter(usuario=self.usuario).update(percentual=101),
            lambda: Palavra.objects.create(modulo=self.modulo, texto="Olá"),
            lambda: Sessao.objects.create(usuario=self.usuario, finalizada_em=timezone.now() - timedelta(days=1)),
        ]
        for criar in invalidos:
            with self.subTest(criar=criar):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    criar()
