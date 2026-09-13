from collections import defaultdict
from contextlib import nullcontext
from pathlib import Path
import warnings

from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Palavra


class Command(BaseCommand):
    help = "Associa arquivos WebP existentes às palavras, sem copiar arquivos."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Simula sem alterar o banco.')
        parser.add_argument('--sobrescrever', action='store_true', help='Permite substituir imagens cadastradas.')

    def handle(self, *args, **options):
        simular = options['dry_run']
        sobrescrever = options['sobrescrever']
        pasta = Path(settings.MEDIA_ROOT) / 'palavras' / 'imagens'
        examinados = associados = preservados = quebradas = 0
        ausentes = defaultdict(list)
        invalidos = defaultdict(list)
        validacoes = {}

        with nullcontext() if simular else transaction.atomic():
            registros = Palavra.objects.select_related('modulo').order_by('pk')
            for palavra in registros.iterator():
                examinados += 1
                identificacao = f'{palavra.palavra} (ID {palavra.pk}, módulo {palavra.modulo.numero})'
                if palavra.imagem:
                    if not palavra.imagem.storage.exists(palavra.imagem.name):
                        quebradas += 1
                        self.stdout.write(f'Referência quebrada: {identificacao}: {palavra.imagem.name}')
                    if not sobrescrever:
                        preservados += 1
                        continue

                nome = f'{palavra.palavra}.webp'
                relativo = f'palavras/imagens/{nome}'
                arquivo = pasta / nome
                # O texto da palavra não pode escapar da pasta de imagens.
                if '/' in nome or '\\' in nome or ':' in nome or arquivo.resolve().parent != pasta.resolve():
                    invalidos[relativo].append(f'{identificacao}: nome de arquivo inseguro')
                    if palavra.imagem:
                        preservados += 1
                    continue

                if relativo not in validacoes:
                    validacoes[relativo] = self.validar_webp(arquivo)
                status, motivo = validacoes[relativo]
                if status != 'valido':
                    if status == 'ausente':
                        ausentes[relativo].append(identificacao)
                    else:
                        invalidos[relativo].append(f'{identificacao}: {motivo}')
                    if palavra.imagem:
                        preservados += 1
                    continue

                if palavra.imagem.name == relativo:
                    preservados += 1
                    continue

                if not simular:
                    palavra.imagem = relativo
                    palavra.save(update_fields=['imagem'])
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
        if simular:
            self.stdout.write(f'Registros que seriam associados: {associados}')
        self.stdout.write(f'Registros preservados: {preservados}')
        self.stdout.write(f'Arquivos ausentes: {len(ausentes)}')
        self.stdout.write(f'Arquivos inválidos: {len(invalidos)}')
        self.stdout.write(f'Referências quebradas: {quebradas}')

    @staticmethod
    def validar_webp(arquivo):
        if not arquivo.is_file():
            return 'ausente', 'Arquivo não encontrado'
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(arquivo) as imagem:
                    if imagem.format != 'WEBP':
                        return 'invalido', 'O conteúdo não é WebP'
                    imagem.verify()
                # Decodifica os pixels e todos os quadros, inclusive em WebP animado.
                with Image.open(arquivo) as imagem:
                    for quadro in range(imagem.n_frames):
                        imagem.seek(quadro)
                        imagem.load()
        except (OSError, ValueError, UnidentifiedImageError,
                Image.DecompressionBombError, Image.DecompressionBombWarning) as erro:
            return 'invalido', str(erro)
        return 'valido', ''
