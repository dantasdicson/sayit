# Resumos dos módulos

## Gerador atual — narração v2

Os módulos 1–9 usam agora o gerador único `docs/gerar_narracoes.py`.
Execute `python docs/gerar_narracoes.py --output-dir caminho/novo --report auditoria.json`.
O destino deve ser novo: o comando não substitui automaticamente áudios em uso.
Para medir os arquivos instalados: `python docs/gerar_narracoes.py --audit-only --report auditoria.json`.
Os scripts antigos encaminham para esse gerador e também salvam em pasta de preparação.

O roteiro vem de `core/narracao_resumos.py`, do catálogo e de `core/resumos.py`.
São seis blocos: abertura portuguesa, quatro pares ingleses e explicação/encerramento portugueses.
Francisca a -5%, Jenny a -12%; somente duas trocas de voz. O áudio é decodificado para PCM,
tem margens de silêncio preservadas, bordas de 5 ms suavizadas, pausas de 450–550 ms
e normalização final em duas passagens. A exportação é MP3 mono, 24 kHz, 128 kbit/s.
Arquivos que não passam nas verificações de duração, volume, pico e silêncio são rejeitados.

Antes de publicar, faça backup dos MP3/JSON anteriores; valide os nove arquivos e seus
roteiros. Copie cada par MP3/JSON validado para o caminho correspondente em media/modulos.
Altere VERSAO_AUDIO para invalidar o cache quando publicar outro lote e reinicie o servidor.
As métricas são avaliação técnica, não substituem a audição humana nem validam sozinhas a pronúncia.

## Histórico da implementação inicial (superado pelo gerador acima)

Somente o Módulo 1 está habilitado: `/modulos/1/resumo/`.
Fluxo: explicação → descobertas 1–4 (dois acertos cada) → resumo → conclusão existente.
O resumo não exige microfone, reprodução do áudio ou nova avaliação.

## Narração a fornecer

Grave uma narração real em MP3 e adicione-a a:

`media/modulos/1/resumo.mp3` (relativo à raiz que contém `manage.py`).

O nome no storage é `modulos/1/resumo.mp3`, definido em `core/resumos.py`.
Use voz em português e pronuncie os exemplos em inglês. Roteiro correspondente à tela:

> O que você aprendeu? Magic E — Som do A.
> Você descobriu que a letra E no final de algumas palavras pode mudar o som da vogal A.
> O E final fica silencioso e muda o som do A.
> Veja novamente as palavras que você aprendeu: cat, cake; cap, cape; tap, tape; mad, made.
> Muito bem! Você terminou a revisão do Magic E.

Nenhum áudio é gerado ou baixado automaticamente. Não é necessário cadastrar o arquivo no banco.
A view verifica existência e tamanho no storage a cada acesso. Sem arquivo, ou em caso de
falha de acesso, não renderiza player, URL de áudio, botão ou aviso de indisponibilidade.
Depois de adicionar o MP3, basta recarregar a página. Use MP3 válido e não vazio;
erros de reprodução são informados na tela. O botão inicia, interrompe e permite ouvir
novamente; sem JavaScript, ficam disponíveis os controles nativos do áudio.

## Reutilização

`core/resumos.py` contém uma configuração por número de módulo: subtítulo, parágrafos,
reforço, caminho do áudio e nome da URL de conclusão. A view `resumo_modulo` recebe
o número pela URL e usa o template `core/resumo_modulo.html`. Os pares vêm das
comparações do módulo no banco, ordenadas por `ordem`, com as palavras relacionadas.
Imagens já cadastradas são exibidas somente quando existem no storage, sem cópias.
O template reaproveita a base visual e o CSS existentes do Módulo 1.

Para expansão futura, cadastrar o conteúdo de um módulo em `RESUMOS`, adicionar
sua rota para a mesma view e conectar seu último passo ao resumo. Os módulos 2–10
não possuem conteúdo ou rotas de resumo nesta implementação.

## Validação

- `python manage.py check`
- `python manage.py test`
- `node --test core/static/core/tests/descobertas_microfone.test.cjs`
- `node --test core/static/core/tests/resumo_audio.test.cjs`

Os testes de áudio simulam o storage e a reprodução; não criam MP3s fictícios.
