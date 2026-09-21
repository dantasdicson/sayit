# Módulo 5 — SH

Implementado sobre `d3da670` de `origin/master`. A cópia local estava em
`424a525`, limpa, e foi atualizada por fast-forward antes da implementação.

## Inspeção e decisões

O Módulo 4 usa explicação, três descobertas com dois cards cada, resumo e
conclusão por POST. Cada palavra precisa de seu próprio acerto confirmado
pelo servidor. Uma descoberta completa libera a próxima; três descobertas
completas liberam o resumo. O percentual é 0, 33, 66 e 100; `concluido_em`
só é registrado ao concluir pelo resumo. GET não cria progresso. Esses
comportamentos foram mantidos no Módulo 5, inclusive início persistido no
primeiro acerto, retomada após reload/login e conclusão idempotente.

O banco já continha o módulo SH ativo, sua teoria e estas seis palavras,
na ordem abaixo. Não havia comparações. A teoria foi preservada:

> S e H juntos fazem um som parecido com o pedido de silêncio: shhh! Procure
> esse som em ship e fish. Ele pode aparecer no começo ou no final.

As três descobertas novas agrupam as palavras cadastradas, sem inventar
vocabulário: ship/fish, shoe/sheep, shop/shell. São pares de prática de SH,
não transformações de Magic E. Os textos específicos foram adaptados.

## Fluxo e reutilização

Trilha → explicação → descoberta 1 → descoberta 2 → descoberta 3 → resumo
→ conclusão → próximo módulo disponível ou trilha.

- Views: `explicacao_modulo_2`, `descoberta_modulo_1`, `resumo_modulo`,
  `conclusao_modulo_2`, parametrizadas com número 5.
- Templates: `explicacao_modulo.html`, `descoberta_modulo_1.html`,
  `resumo_modulo.html`, `conclusao_modulo.html`, bases e sidebar existentes.
- Progresso: `_catalogo`, `_estado`, `_completa`, `_permitida`,
  `consultar_progresso`, `registrar_acerto`, `concluir_modulo`,
  `resumo_pode_ser_acessado` e a API existente.
- Voz: `pronuncia.js`, `descobertas_microfone.js`, `core/pronuncia.py`,
  normalização, seleção de alternativas e aliases existentes, sem alterações.
- Áudio: `modulo_1.js`, `resumo_audio.js` e detecção via `default_storage`.
- CSS: `design_system.css`, `descobertas_layout.css` e `resumo_modulo.css`,
  sem alterações. As imagens no resumo continuam ocultas pelo CSS existente;
  os seis exemplos textuais seguem o padrão do Módulo 4.

O sistema atual disponibiliza os módulos implementados e ativos na trilha;
não exige terminar um módulo para abrir sua explicação. Isso foi preservado.
Os bloqueios sequenciais dentro das descobertas permanecem obrigatórios.
O painel geral de progresso continua com o comportamento anterior; o
Módulo 5 entra em `consultar_meu_progresso` após o primeiro acerto.

## Mídias

Todos os caminhos abaixo são relativos a `MEDIA_ROOT`, que corresponde a
`media/` na raiz do projeto. Os campos foram associados no banco local.

| Ordem | Palavra | Tradução | Campo imagem | Campo audio |
|---|---|---|---|---|
| 1 | ship | navio | palavras/imagens/ship.webp | palavras/audios/ship.mp3 |
| 2 | fish | peixe | palavras/imagens/fish.webp | palavras/audios/fish.mp3 |
| 3 | shoe | sapato | palavras/imagens/shoe.webp | palavras/audios/shoe.mp3 |
| 4 | sheep | ovelha | palavras/imagens/sheep.webp | palavras/audios/sheep.mp3 |
| 5 | shop | loja | palavras/imagens/shop.webp | palavras/audios/shop.mp3 |
| 6 | shell | concha | palavras/imagens/shell.webp | palavras/audios/shell.mp3 |

Imagens: seis ilustrações novas, inspecionadas visualmente, em WebP RGB,
1254 × 1254, qualidade 90. Geração pela ferramenta integrada `image_gen`,
uma imagem por chamada; conversão de formato com Pillow já instalado.
Fundo creme limpo, pintura infantil suave, assunto central, sem texto.
Os prompts estão em `docs/modulo_5_imagens_prompts.json`.

`associar_imagens --modulo 5 --dry-run` validou seis arquivos antes da
associação real: zero ausentes, zero inválidos, zero referências quebradas.
O manifesto de imagens agora marca essas seis entradas como `gerado`.

Áudios das palavras: os seis MP3s já existiam. Foram preservados, decodificados
e associados com `associar_audios --modulo 5`, após dry-run sem erros.
Nenhum áudio anterior foi recriado ou alterado.

Resumo: `media/modulos/5/resumo.mp3`, **35,88 segundos**, MP3 mono, 24 kHz.
Gerador: `docs/gerar_resumo_modulo_5.py`. Português com
`pt-BR-FranciscaNeural`; cada exemplo inglês com `en-US-JennyNeural`.
Taxa `+0%`, concatenação dos segmentos e pausas naturais iguais ao gerador
do Módulo 4. O arquivo existente é preservado em execuções posteriores.

## Continuação

A conclusão do Módulo 4 agora oferece a explicação do 5 pelo mecanismo
existente. A conclusão do 5 mantém **“Continuar para o próximo módulo”**.
O próximo número é 6. Ele só recebe link direto quando está implementado
no catálogo de progresso, ativo, com catálogo válido e rota resolvível.
Atualmente o 6 não está implementado: aparece uma mensagem curta e o botão
leva à trilha, sem URL quebrada. Há cobertura para módulo inativo,
catálogo incompleto, rota ausente e implementação futura disponível.

## Arquivos

Criados:

- `core/test_modulo_5.py`
- `core/test_modulo_5_http.py`
- `docs/gerar_resumo_modulo_5.py`
- `docs/modulo_5.md`
- `docs/modulo_5_imagens_prompts.json`
- `media/modulos/5/resumo.mp3`
- As seis imagens WebP listadas acima.

Alterados:

- `.gitignore`: permite versionar apenas as mídias necessárias do Módulo 5.
- `core/data/imagens_manifest.json`
- `core/management/commands/popular_sayit.py`: pares SH e filtro opcional
  `--modulo`, usado para não recarregar os módulos anteriores no banco local.
- `core/progresso.py`
- `core/resumos.py`
- `core/views.py`
- `sayit/urls.py`
- `core/templates/core/area.html`
- `core/templates/core/explicacao_modulo.html`
- `core/templates/core/descoberta_modulo_1.html`
- `core/templates/core/conclusao_modulo.html`
- `core/templates/core/discovery_navigation.html`
- `core/static/core/tests/descobertas_microfone.test.cjs`
- `core/test_continuacao_modulos.py`
- `core/test_resumo.py`

Os seis MP3s de palavras existentes passam a estar visíveis ao Git, sem
alteração de conteúdo. `db.sqlite3` recebeu os três pares e as associações
do Módulo 5; continua ignorado pelo Git. Nenhuma migration, biblioteca ou
dependência foi adicionada; `settings.py` não foi alterado.

Em outro banco, executar com o Python configurado para o projeto:

```text
python manage.py popular_sayit --modulo 5
python manage.py associar_imagens --modulo 5 --dry-run
python manage.py associar_imagens --modulo 5
python manage.py associar_audios --modulo 5 --dry-run
python manage.py associar_audios --modulo 5
```

## Verificação

Base anterior: 165 testes Django e 102 testes JavaScript aprovados.

Resultado final:

- `python manage.py check`: nenhum problema (0 silenced).
- `python manage.py test --noinput`: **180 testes aprovados**, 37,724 s.
- `node --test core/static/core/tests/*.test.cjs`: **114 testes aprovados**.
- `git diff --check`: sem erros de whitespace.
- Módulos 1–4: suíte de regressão aprovada. As únicas expectativas antigas
  ajustadas foram o último módulo implementado e o resumo 5 antes inexistente.
- Fluxo HTTP e arquivos referenciados: respostas 200; nenhum 404/500 no fluxo
  permitido. Acesso antecipado às etapas protegidas continua retornando 409.

O teste HTTP usa servidor Django real em IPv4 e banco de teste isolado:
login de teste, trilha, explicação, três descobertas, seis POSTs com CSRF,
reload de cada etapa, resumo, conclusão e retorno à trilha. Também verifica
respostas HTTP dos CSS, JavaScript, imagens e MP3s referenciados. Os testes
de mídia decodificam os WebP e MP3 reais. Os testes JavaScript simulam
acerto, erro, silêncio, permissão negada, navegador sem suporte, alternativas,
persistência de estados individuais e bloqueio/liberação de avanço.

Limite: isso não valida fala humana nem reprodução perceptiva. A sessão
não disponibilizou navegador conectado (`chrome` e `iab` indisponíveis;
inventário de navegadores vazio). Portanto ainda é necessária a validação
manual em navegador com microfone: layout desktop/mobile, imagens visíveis,
reprodução audível das palavras e do resumo, permissão/início do microfone,
pronúncia das seis palavras e navegação até a conclusão. A implementação
automatizada está entregue; a homologação manual não deve ser considerada
concluída até essa checagem.
