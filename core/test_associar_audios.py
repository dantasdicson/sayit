from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from core.models import Modulo, Palavra


class AssociarAudiosModuloTests(TestCase):
    def test_filtro_preserva_outros_modulos_e_simulacao_nao_grava(self):
        primeiro = Modulo.objects.create(numero=1, ordem=1, titulo='Magic E')
        outro = Modulo.objects.create(numero=2, ordem=2, titulo='Outro')
        cat = Palavra.objects.create(modulo=primeiro, palavra='cat', ordem=1)
        kit = Palavra.objects.create(modulo=outro, palavra='kit', ordem=1)
        with patch('core.management.commands.associar_audios.Command.validar_mp3',
                   return_value=('valido', '')):
            call_command('associar_audios', modulo=1, dry_run=True, stdout=StringIO())
            cat.refresh_from_db()
            self.assertFalse(cat.audio)
            call_command('associar_audios', modulo=1, stdout=StringIO())
        cat.refresh_from_db()
        kit.refresh_from_db()
        self.assertEqual(cat.audio.name, 'palavras/audios/cat.mp3')
        self.assertFalse(kit.audio)
