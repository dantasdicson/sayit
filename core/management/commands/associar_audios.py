from collections import defaultdict
from contextlib import nullcontext
from pathlib import Path
import miniaudio

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Palavra


class Command(BaseCommand):
    help = "Associa arquivos MP3 existentes às palavras, sem copiar arquivos."

    def add_arguments(self, parser):
        parser.add_argument('--modulo', type=int, help='Limita a associação ao número do módulo informado.')
        parser.add_argument('--dry-run', action='store_true', help='Simula sem alterar o banco.')
        parser.add_argument('--sobrescrever', action='store_true', help='Permite substituir áudios cadastrados.')

    def handle(self, *args, **options):
        simular = options['dry_run']
        sobrescrever = options['sobrescrever']
        pasta = Path(settings.MEDIA_ROOT) / 'palavras' / 'audios'
        examinados = associados = preservados = quebradas = 0
        ausentes = defaultdict(list)
        invalidos = defaultdict(list)
        validacoes = {}

        with nullcontext() if simular else transaction.atomic():
            registros = Palavra.objects.select_related('modulo').order_by('pk')
            if options['modulo'] is not None:
                registros = registros.filter(modulo__numero=options['modulo'])
            for palavra in registros.iterator():
                examinados += 1
                identificacao = f'{palavra.palavra} (ID {palavra.pk}, módulo {palavra.modulo.numero})'
                if palavra.audio:
                    if not palavra.audio.storage.exists(palavra.audio.name):
                        quebradas += 1
                        self.stdout.write(f'Referência quebrada: {identificacao}: {palavra.audio.name}')
                    if not sobrescrever:
                        preservados += 1
                        continue

                nome = f'{palavra.palavra}.mp3'
                relativo = f'palavras/audios/{nome}'
                arquivo = pasta / nome
                # O texto da palavra não pode escapar da pasta de audios.
                if '/' in nome or '\\' in nome or ':' in nome or arquivo.resolve().parent != pasta.resolve():
                    invalidos[relativo].append(f'{identificacao}: nome de arquivo inseguro')
                    if palavra.audio:
                        preservados += 1
                    continue

                if relativo not in validacoes:
                    validacoes[relativo] = self.validar_mp3(arquivo)
                status, motivo = validacoes[relativo]
                if status != 'valido':
                    if status == 'ausente':
                        ausentes[relativo].append(identificacao)
                    else:
                        invalidos[relativo].append(f'{identificacao}: {motivo}')
                    if palavra.audio:
                        preservados += 1
                    continue

                if palavra.audio.name == relativo:
                    preservados += 1
                    continue

                if not simular:
                    palavra.audio = relativo
                    palavra.save(update_fields=['audio'])
                associados += 1
                acao = 'Seria associado' if simular else 'Associado'
                self.stdout.write(f'{acao}: {identificacao} -> {relativo}')

        for titulo, arquivos in [('Arquivos ausentes', ausentes), ('Arquivos inválidos', invalidos)]:
            if arquivos:
                self.stdout.write(f'{titulo}:')
                for caminho, afetadas in sorted(arquivos.items()):
                    self.stdout.write(f'  {caminho}: {"; ".join(afetadas)}')

        self.stdout.write('Resumo da simulação (nenhuma gravação):' if simular else 'Resumo:')
        self.stdout.write(f'Registros examinados: {examinados}')
        self.stdout.write(f'Registros associados: {0 if simular else associados}')
        self.stdout.write(f'Registros que seriam associados: {associados if simular else 0}')
        self.stdout.write(f'Registros preservados: {preservados}')
        self.stdout.write(f'Arquivos ausentes: {len(ausentes)}')
        self.stdout.write(f'Arquivos inválidos: {len(invalidos)}')
        self.stdout.write(f'Referências quebradas: {quebradas}')

    @staticmethod
    def validar_mp3(arquivo):
        try:
            if not arquivo.exists():
                return 'ausente', 'Arquivo não encontrado'
            if not arquivo.is_file() or arquivo.suffix != '.mp3':
                return 'invalido', 'Não é um arquivo MP3 regular'
            if arquivo.stat().st_size == 0:
                return 'invalido', 'Arquivo vazio'
            miniaudio.mp3_get_file_info(str(arquivo))
            audio = miniaudio.mp3_read_file_f32(str(arquivo))
            if not len(audio.samples):
                return 'invalido', 'MP3 sem amostras decodificáveis'
        except (OSError, ValueError, miniaudio.DecodeError):
            return 'invalido', 'Não foi possível abrir ou decodificar o MP3'
        return 'valido', ''
