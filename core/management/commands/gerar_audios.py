import asyncio
import json
import os
import re
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.models import Palavra


ENGINE = "edge-tts"
VOICE = "en-US-JennyNeural"
RATE = "-10%"


def valid_audio(path):
    return path.suffix == ".mp3" and path.is_file() and path.stat().st_size > 0


def safe_error_text(value):
    """Redact credentials before displaying diagnostic scalar fields."""
    if not isinstance(value, (str, int, float)):
        return "[detalhe omitido]"
    text = str(value)
    for name, secret in os.environ.items():
        if secret and re.search(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL", name, re.I):
            text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"sk-[\w.*-]+", "[REDACTED]", text)
    text = re.sub(r"(?i)Bearer\s+\S+", "[REDACTED]", text)
    # Do not render request/header dumps, even if embedded in an error message.
    text = re.sub(
        r"(?is)(authorization|headers?|request|api[_-]?key|secret|password|token)"
        r"[\s\"']*[:=].*", "[detalhes sensíveis omitidos]", text
    )
    return " ".join(text.split())[:1500]


def error_details(exc):
    # Select individual fields; never serialize the exception, request or response.
    body = getattr(exc, "body", None)
    error = body.get("error", body) if isinstance(body, dict) else {}
    if not isinstance(error, dict):
        error = {}
    message = error.get("message")
    if not isinstance(message, str):
        message = getattr(exc, "message", None) or str(exc)
    fields = {
        "Tipo da exceção": type(exc).__name__,
        "Mensagem": message,
        "Status code": getattr(exc, "status_code", None) or getattr(exc, "status", None),
        "error.code": error.get("code") or getattr(exc, "code", None),
        "error.type": error.get("type") or getattr(exc, "type", None),
    }
    return [f"{label}: {safe_error_text(value)}" for label, value in fields.items()
            if value is not None]


def save_manifest(path, document):
    """Replace the manifest atomically, avoiding a partially written JSON file."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class Command(BaseCommand):
    help = "Gera um MP3 por palavra distinta, sem alterar o banco de dados."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Simula sem API ou gravações.")
        parser.add_argument("--sobrescrever", action="store_true", help="Substitui áudios existentes.")
        parser.add_argument("--palavra", help="Processa somente a palavra informada.")

    def load_manifest(self, path):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            entries = document["audios"]
            pairs = set(Palavra.objects.order_by().values_list("palavra", "traducao").distinct())
            words = [entry["palavra"] for entry in entries]
            if len(entries) != 58 or len(set(words)) != 58:
                raise ValueError
            if {(e["palavra"], e["traducao"]) for e in entries} != pairs:
                raise ValueError
            for entry in entries:
                word = entry["palavra"]
                if (
                    not re.fullmatch(r"[a-z]+", word)
                    or entry["arquivo"] != f"palavras/audios/{word}.mp3"
                    or entry["texto_falado"] != word
                    or entry["voz"] != VOICE
                    or entry["motor"] != ENGINE
                    or entry["status"] not in {"pendente", "gerado", "erro"}
                ):
                    raise ValueError
            return document
        except (OSError, ValueError, KeyError, TypeError):
            raise CommandError(
                "Manifesto inválido: confira as 58 palavras, traduções, caminhos e parâmetros."
            ) from None

    def generate(self, entry, destination):
        # No network activity in dry-run or when preserving an existing file.
        import edge_tts

        async def synthesize(path):
            # edge-tts produces MP3; only the isolated word is sent as speech text.
            speech = edge_tts.Communicate(entry["texto_falado"], VOICE, rate=RATE)
            await speech.save(str(path))

        temporary = None
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=destination.parent, suffix=".mp3", delete=False
            ) as stream:
                temporary = Path(stream.name)
            asyncio.run(synthesize(temporary))
            if not valid_audio(temporary):
                raise ValueError("Arquivo de áudio vazio ou inválido.")
            temporary.replace(destination)
            if not valid_audio(destination):
                raise ValueError("Arquivo final inválido.")
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def handle(self, *args, **options):
        path = Path(settings.BASE_DIR) / "core/data/audios_manifest.json"
        document = self.load_manifest(path)
        entries = document["audios"]
        if options["palavra"]:
            entries = [e for e in entries if e["palavra"] == options["palavra"]]
            if not entries:
                raise CommandError("Palavra não encontrada no manifesto.")

        totals = {"examinadas": 0, "previstas": 0, "gerados": 0, "preservados": 0, "falhas": 0}
        for entry in entries:
            totals["examinadas"] += 1
            destination = Path(settings.MEDIA_ROOT) / entry["arquivo"]
            try:
                if destination.exists() and not options["sobrescrever"]:
                    totals["preservados"] += 1
                    self.stdout.write(f"Preservado: {entry['arquivo']}")
                    if not valid_audio(destination):
                        raise ValueError("Arquivo existente inválido; use --sobrescrever.")
                    if not options["dry_run"]:
                        entry["status"] = "gerado"
                elif options["dry_run"]:
                    totals["previstas"] += 1
                    self.stdout.write(f"Seria gerado: {entry['arquivo']}")
                else:
                    self.generate(entry, destination)
                    entry["status"] = "gerado"
                    totals["gerados"] += 1
                    self.stdout.write(f"Gerado: {entry['arquivo']}")
            except Exception as exc:
                totals["falhas"] += 1
                if not options["dry_run"]:
                    entry["status"] = "erro"
                self.stderr.write(f"Falha: {entry['palavra']}. Confira a conexão e o arquivo de destino.")
                for detail in error_details(exc):
                    self.stderr.write(detail)

            if not options["dry_run"]:
                try:
                    save_manifest(path, document)
                except OSError:
                    # Stop if generation progress cannot be persisted.
                    raise CommandError("Não foi possível salvar o manifesto; processamento interrompido.") from None

        self.stdout.write(f"Palavras examinadas: {totals['examinadas']}")
        self.stdout.write(f"Áudios que seriam gerados: {totals['previstas']}")
        self.stdout.write(f"Áudios gerados: {totals['gerados']}")
        self.stdout.write(f"Arquivos preservados: {totals['preservados']}")
        self.stdout.write(f"Falhas: {totals['falhas']}")
