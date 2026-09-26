"""Verifica todo o catálogo, inclusive referências e conteúdo dos arquivos."""
import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from core.models import Palavra
from .associar_audios import Command as Audios
from .associar_imagens import Command as Imagens


class Command(BaseCommand):
    help = 'Audita imagens, áudios e manifestos de todas as palavras.'

    def handle(self, *args, **options):
        erros, cache = [], {}
        palavras = list(Palavra.objects.select_related('modulo'))
        pares = {(p.palavra, p.traducao) for p in palavras}
        for tipo, campo, validar in [('audios', 'audio', Audios.validar_mp3), ('imagens', 'imagem', Imagens.validar_webp)]:
            documento = json.loads((Path(settings.BASE_DIR) / f'core/data/{tipo}_manifest.json').read_text(encoding='utf-8'))
            entradas = documento[tipo]
            if {(e['palavra'], e['traducao']) for e in entradas} != pares or len(entradas) != len(pares):
                erros.append(f'Manifesto {tipo} não corresponde ao banco')
            for p in palavras:
                arquivo = getattr(p, campo).name
                if not arquivo:
                    erros.append(f'Módulo {p.modulo.numero}: {p.palavra} sem {campo}')
                    continue
                chave = (tipo, arquivo)
                if chave not in cache:
                    cache[chave] = validar(Path(settings.MEDIA_ROOT) / arquivo)
                if cache[chave][0] != 'valido':
                    erros.append(f'{p.palavra}: {arquivo}: {cache[chave]}')
                entrada = next((e for e in entradas if e['palavra'] == p.palavra), None)
                if entrada and (entrada['arquivo'] != arquivo or entrada['status'] != ('gerado' if tipo == 'audios' else 'gerada')):
                    erros.append(f'{p.palavra}: manifesto {tipo} desatualizado')
        for erro in erros:
            self.stderr.write(erro)
        if erros:
            raise CommandError(f'{len(erros)} problemas de mídia encontrados')
        self.stdout.write(self.style.SUCCESS(f'{len(palavras)} palavras, {len(pares)} distintas: nenhuma mídia ausente, inválida ou referência quebrada.'))
