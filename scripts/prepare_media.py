"""Copia recursos públicos distribuídos no Git para o disco persistente."""
import os
import shutil
from pathlib import Path

source = Path(__file__).resolve().parents[1] / 'media'
target = Path(os.environ.get('MEDIA_ROOT', str(source)))
if source.resolve() != target.resolve():
    for file in source.rglob('*'):
        if file.is_file() and file.suffix.lower() in {'.webp', '.mp3'}:
            destination = target / file.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copy2(file, destination)
