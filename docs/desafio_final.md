# Módulo 10 — Desafio Final

Substitui a experiência de revisão geral por três desafios:

1. I like cake. — palavra-chave: cake.
2. The ship is big. — palavra-chave: ship.
3. The cute cat is on the ship. — palavras-chave: cute, cat, ship.

Configuração única: core/desafio_config.py. Ao trocar frases ou critérios, incremente VERSAO para não misturar notas de avaliações diferentes.

## Fluxo e nota

Montar por toque ou teclado → conferir no servidor → liberar microfone em en-US → avaliar e salvar → avançar com melhor nota de pelo menos 70.

As frases ficam visíveis como referência, conforme o enunciado. A montagem aceita as mesmas palavras, na ordem correta, ignorando maiúsculas e pontuação.

A nota é uma aproximação textual do reconhecimento, não uma medição acústica da pronúncia. O navegador pode transcrever incorretamente. A tela explica essa limitação.

O servidor normaliza texto e encontra a maior subsequência comum de palavras inteiras, preservando ordem e ocorrências repetidas:

- Até 60 pontos: 60 × palavras alinhadas ÷ máximo entre quantidade esperada e reconhecida. Palavras extras também reduzem essa parcela.
- Até 30 pontos: 30 × ocorrências importantes alinhadas ÷ ocorrências importantes esperadas.
- 10 pontos adicionais: todas as palavras presentes, em ordem, sem extras.
- Soma arredondada para inteiro mais próximo (meio ponto arredonda para cima); intervalo 0–100.

Não são aplicadas similaridades vagas nem os bypasses de palavras isoladas, como PEACH/BEACH. Exemplo: “I cake” recebe 70; “cake” recebe 50; “I like cake” recebe 100. Na frase de seis palavras “The ship is on the moon”, omitir o segundo “the” resulta em 80, sem valores fixos por exemplo.

Resultado final: média arredondada das melhores notas dos três desafios. Tentativas piores não diminuem a melhor nota; o histórico é persistente.

## Persistência, segurança e compatibilidade

A migration 0008_tentativa_desafio_final cria somente TentativaDesafio, com usuário, módulo, número do desafio, versão, ID único da requisição, frase esperada, transcrição, nota, feedback estruturado e data. É necessária porque Tentativa exige uma Palavra; associar uma frase a uma palavra criaria acertos fictícios e comprometeria a trilha antiga.

Progresso continua sendo a fonte da conclusão. O terceiro desafio aprovado grava 100% e concluido_em na mesma transação da tentativa, sem modificar módulos 1–9. Tentativas de frases não são contabilizadas como acertos de palavras isoladas.

Conclusões da revisão antiga são preservadas com a data original. Não há nota inventada: o aluno precisa completar os três novos desafios para acessar o novo resultado. Palavras, comparações, mídias e tentativas antigas não são excluídas. O áudio antigo de revisão não é reproduzido neste fluxo.

Autenticação, bloqueio sequencial e CSRF existentes são mantidos. O servidor valida a montagem, emite ticket assinado vinculado ao usuário/desafio/versão (15 minutos) e calcula a nota — não aceita nota enviada pelo cliente. Um ticket registra uma única tentativa; reenvio de rede com o mesmo texto não duplica. Rotas antigas de palavras não concluem o desafio.

Na interface não existe entrada digitada alternativa à fala. Como no reconhecimento anterior, a API recebe a transcrição do navegador, não o áudio: isso não é prova criptográfica de uso do microfone nem avaliação certificada antifraude.

Reaproveitamento: base_app, tokens CSS, breakpoints, módulo de reprodução de palavras, Progresso, validação de payload, normalização e fábrica de reconhecimento compartilhada em pronuncia.js. O controlador de palavras usa essa mesma fábrica, com a configuração anterior inalterada. Não foram alterados login/cadastro e não há novos arquivos de áudio.

## Atualização

1. Faça backup consistente do banco SQLite e preserve media/.
2. Execute python manage.py migrate.
3. Execute python manage.py popular_sayit --modulo 10 (atualiza metadados, preserva catálogo existente).
4. Reinicie Django. Em produção, atualize estáticos com o procedimento de implantação.
5. Execute python manage.py check, python manage.py test e node --test core/static/core/tests/*.test.cjs.

Os arquivos JavaScript compartilhados têm novas versões na URL para impedir mistura de cache antigo.

## Arquivos criados nesta reformulação

- core/desafio_config.py
- core/desafio_avaliacao.py
- core/desafio_service.py
- core/desafio_views.py
- core/migrations/0008_tentativa_desafio_final.py
- core/templates/core/desafio/base.html
- core/templates/core/desafio/introducao.html
- core/templates/core/desafio/atividade.html
- core/templates/core/desafio/resultado.html
- core/static/core/desafio_final.js
- core/static/core/desafio_final.css
- core/static/core/tests/desafio_final.test.cjs
- docs/desafio_final.md

## Arquivos alterados nesta reformulação

- core/models.py: tabela de tentativas de frases.
- core/progresso.py: encaminhamento específico do módulo 10.
- core/views.py e sayit/urls.py: rotas e compatibilidade com links antigos.
- core/management/commands/popular_sayit.py: título/conteúdo e preservação do legado.
- core/resumos.py: remove revisão antiga da lista de narrações ativas.
- core/static/core/pronuncia.js e descobertas_microfone.js: fábrica de reconhecimento compartilhada, sem mudar a avaliação dos módulos 1–9.
- core/templates/core/descoberta_modulo_1.html e pratica_modulo_1.html: versões dos scripts.
- core/templates/core/discovery_navigation.html e area.html: indicação de desafios e navegação.
- core/test_modulo_10.py: substitui testes da revisão por 22 testes de avaliação, API, progressão e preservação.
- core/test_continuacao_modulos.py e test_quatro_descobertas.py: módulo 10 passa a ter três desafios, mantendo quatro descobertas nos módulos 1–9.

## Verificação

Resultado final: 247 testes Django + 167 testes JavaScript = 414 testes aprovados. Django check sem problemas; makemigrations --check --dry-run sem alterações pendentes; git diff --check sem erros.

Migration aplicada após backup consistente em work/db-before-desafio-final-20260924-231511.sqlite3. Comparação antes/depois confirmou usuários, palavras, comparações, tentativas, progressos e metadados dos módulos 1–9 integralmente preservados.

Servidor atualizado na porta 8001. Link temporário https://accurate-communication-usgs-thank.trycloudflare.com (login e script do desafio verificados com HTTP 200).

Os 22 testes Python específicos abrangem frases perfeitas/parciais, normalização, palavra diferente/faltante, ordem, silêncio, notas abaixo/igual/acima de 70, estrelas, média, melhor tentativa, progressão, conclusão, autenticação, CSRF, idempotência, isolamento entre usuários, ticket expirado e preservação do legado.

Os 20 testes JavaScript específicos abrangem montagem, palavras repetidas, bloqueios, configuração de voz, resultados, histórico, falta de suporte/HTTPS, permissão negada, falhas do microfone/rede, silêncio, resultado parcial/tardio, reenvio e saída da página.

Validação visual realizada em 390, 768 e 1280 pixels, sem transbordamento horizontal nos estados conferidos. Montagem incorreta recusada, montagem correta libera o microfone, próximo bloqueado antes de nota aprovada; histórico e resultado final persistem ao recarregar.

Teste integrado da conta QA via views com CSRF: 50, 70 e 100 no primeiro desafio, 75 no segundo e 81 no terceiro; resultado final 85. Nenhum outro usuário alterado. Transcrições são sintéticas — teste de fala real no celular ainda exige validação humana.
