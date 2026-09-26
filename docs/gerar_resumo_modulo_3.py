"""Compatibilidade: usa o gerador validado e salva em staging antes da publicação."""
import asyncio
import sys
from gerar_narracoes import main

if __name__ == '__main__':
    if '--modulo' not in sys.argv:
        sys.argv.extend(['--modulo', '3'])
    asyncio.run(main())
