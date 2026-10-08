# Resumos dos módulos

Os módulos 1 a 9 têm um resumo com texto, exemplos e narração em MP3. O módulo 10 contém os desafios finais.

## Narração

O gerador atual é `docs/gerar_resumos_naturais.py`. Ele usa a voz neural Francisca em português brasileiro e Jenny em inglês americano. As explicações são falas completas, e os exemplos em inglês são agrupados para evitar mudanças de voz a cada palavra. O roteiro mantém as regras e os pares praticados nos módulos.

O áudio tem pausas curtas entre os blocos, ritmo um pouco mais lento nos exemplos e volume normalizado. A montagem decodifica os trechos para PCM e cria um único MP3; não concatena arquivos MP3 diretamente. A geração ocorre na manutenção do projeto, sem chamadas ao serviço de voz durante o uso do app ou o deploy.

Com edge-tts instalado no ambiente e FFmpeg no PATH:

```powershell
python docs/gerar_resumos_naturais.py --modulo 1 --sobrescrever
python docs/gerar_resumos_naturais.py --sobrescrever
```

Sem `--sobrescrever`, os arquivos existentes são preservados. O gerador valida a decodificação antes de substituir cada arquivo. Os roteiros e as vozes estão no próprio script. Os geradores anteriores são históricos; use o gerador atual para novas versões.

Os arquivos ficam em `media/modulos/<numero>/resumo.mp3`, com os caminhos definidos em `core/resumos.py`. Não é necessário cadastrá-los no banco. Os MP3s são versionados no repositório e servidos pelo Render.

## Reprodução

A view verifica a existência e o tamanho do arquivo antes de exibir o player. Sem JavaScript, os controles nativos continuam disponíveis. O botão permite pausar e ouvir novamente. O resumo dispensa o microfone; para a primeira conclusão do módulo, a reprodução deve chegar ao final. Falhas de reprodução são informadas na tela.

A atualização das narrações não altera os acertos, tentativas ou progressos existentes.

## Validação

Cada arquivo gerado passa pela decodificação completa do FFmpeg. Os testes em `core/static/core/tests/resumo_audio.test.cjs` verificam os estados de reprodução e de conclusão.
