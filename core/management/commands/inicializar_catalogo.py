from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Modulo, Palavra, Comparacao


class Command(BaseCommand):
    help = 'Carrega o catálogo validado somente em um banco sem conteúdo pedagógico.'

    def add_arguments(self, parser):
        parser.add_argument('--se-vazio', action='store_true')

    def handle(self, *args, **options):
        if Modulo.objects.exists() or Palavra.objects.exists() or Comparacao.objects.exists():
            if options['se_vazio']:
                self.stdout.write('Catálogo existente preservado.')
                return
            raise CommandError('O catálogo já contém dados. Nenhum registro foi alterado.')
        with transaction.atomic():
            call_command('loaddata', 'catalogo_producao')
        self.stdout.write(self.style.SUCCESS('Catálogo inicial carregado.'))
