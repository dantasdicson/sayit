# Módulo 3 — Magic E com O

Conteúdo do catálogo existente: HOP/HOPE (pular/esperança), NOT/NOTE (não/nota), ROB/ROBE (roubar/roupão).

Fluxo: Trilha → /modulos/3/explicacao/ → /modulos/3/descobertas/1–3/ → /modulos/3/resumo/ → POST /modulos/3/conclusao/ → GET conclusão.

Reutiliza as views do Módulo 2 com parâmetro de módulo, templates, CSS, microfone,
normalização, aliases, API e serviço de progresso existentes. Não há nova migration.
Cada par requer os dois acertos confirmados pelo servidor; percentuais 0/33/66/100.
A conclusão formal grava a data apenas no POST, de forma idempotente.
Como no Módulo 2, a entrada pela Trilha não exige conclusão do módulo anterior.
O início da página não cria progresso; o primeiro acerto cria o registro.
A tela Meu Progresso continua sendo o espaço reservado existente; o serviço de consulta
inclui os três módulos. Não foi criada uma interface de progresso diferente.

## Mídias

Imagens: media/palavras/imagens/{hop,hope,not,note,rob,robe}.webp.
Geradas conforme as descrições existentes em core/data/imagens_manifest.json.
Áudios das palavras: media/palavras/audios/{hop,hope,not,note,rob,robe}.mp3,
reutilizados sem sobrescrita.

Associe os arquivos em outra instalação com:

```powershell
python manage.py associar_imagens --modulo 3
python manage.py associar_audios --modulo 3
```

Resumo: media/modulos/3/resumo.mp3, detectado automaticamente pela view.
26,724083 segundos; 428972 bytes; MP3 mono, 24000 Hz, 128 kbps.
Português: pt-BR-FranciscaNeural; exemplos: en-US-JennyNeural.
Velocidade +0%; pausa 0,35 s dentro dos pares e 0,65 s entre pares.
O script docs/gerar_resumo_modulo_3.py reproduz o padrão anterior com edge-tts
 e FFmpeg já instalados e não sobrescreve um arquivo existente.
Intermediários ficam em work/ e são removidos automaticamente.
media/ permanece ignorada pelo Git, como nos módulos anteriores.
O resumo mantém o CSS compacto do Módulo 2, que oculta as imagens dos pares;
as seis imagens aparecem nas Descobertas.

## Verificação

Antes: check sem erros, 145 testes Django e 88 JavaScript aprovados.
Depois: check sem erros, 158 testes Django e 99 JavaScript aprovados.
makemigrations --check --dry-run: nenhuma mudança.
Os cenários antigos que usavam o Módulo 3 como não implementado agora usam o 4;
as regras e asserções de segurança foram preservadas.

No navegador: Trilha, explicação, três descobertas, resumo e conclusão verificados.
Imagens e áudios carregaram; resumo reproduziu até 26,724083 s sem erro.
POST de conclusão executado pelo botão real. Acertos de teste foram registrados
pela API apenas na conta temporária, sem simular fala humana.
Microfone iniciou a tentativa e retornou silêncio sem liberar Próxima.
Teste de pronúncia real e de permissão no celular permanece para o usuário.
