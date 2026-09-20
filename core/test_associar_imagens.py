from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from core.models import Modulo, Palavra


class AssociarImagensModuloTests(TestCase):
    def test_filtro_preserva_outros_modulos_e_simulacao_nao_grava(self):
        primeiro = Modulo.objects.create(numero=1, ordem=1, titulo='Magic E')
        outro = Modulo.objects.create(numero=2, ordem=2, titulo='Outro')
        cat = Palavra.objects.create(modulo=primeiro, palavra='cat', ordem=1)
        kit = Palavra.objects.create(modulo=outro, palavra='kit', ordem=1)
        with patch('core.management.commands.associar_imagens.Command.validar_webp',
                   return_value=('valido', '')):
            call_command('associar_imagens', modulo=1, dry_run=True, stdout=StringIO())
            cat.refresh_from_db()
            self.assertFalse(cat.imagem)
            call_command('associar_imagens', modulo=1, stdout=StringIO())
        cat.refresh_from_db()
        kit.refresh_from_db()
        self.assertEqual(cat.imagem.name, 'palavras/imagens/cat.webp')
        self.assertFalse(kit.imagem)

