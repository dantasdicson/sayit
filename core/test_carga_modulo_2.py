from io import StringIO
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from core.models import Modulo, Palavra, Comparacao, Tentativa


class CargaModulo2Tests(TestCase):
    def test_reordenacao_idempotente_preserva_historico_e_outros_modulos(self):
        modulo = Modulo.objects.create(numero=2, ordem=2, titulo='Antigo')
        palavras = [Palavra.objects.create(modulo=modulo, palavra=w, ordem=i)
                    for i, w in enumerate(['kit', 'kite', 'bit', 'bite', 'fin', 'fine'], 1)]
        usuario = get_user_model().objects.create_user(username='historico')
        tentativa = Tentativa.objects.create(usuario=usuario, palavra=palavras[0], resultado='correto')
        par = Comparacao.objects.create(modulo=modulo, palavra_base=palavras[2], palavra_comparada=palavras[3], ordem=2)
        outro = Modulo.objects.create(numero=1, ordem=1, titulo='Preservado')
        for _ in range(2):
            call_command('popular_sayit', modulo=2, stdout=StringIO())
            self.assertEqual(list(modulo.palavras.filter(ativa=True).values_list('palavra', 'ordem')),
                             list(zip(['bit', 'bite', 'can', 'cane', 'pin', 'pine', 'sit', 'site'], range(1, 9))))
            self.assertEqual(modulo.comparacoes.count(), 4)
            self.assertTrue(Tentativa.objects.filter(pk=tentativa.pk, palavra=palavras[0]).exists())
            par.refresh_from_db()
            self.assertEqual(par.ordem, 1)
            outro.refresh_from_db()
            self.assertEqual(outro.titulo, 'Preservado')
