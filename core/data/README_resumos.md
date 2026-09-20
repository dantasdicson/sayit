# Resumos dos módulos

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
