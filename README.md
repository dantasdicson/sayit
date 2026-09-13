# Sayit

Projeto Django com app `core` e SQLite, configurado para desenvolvimento local.

## Executar

Na pasta `sayit`, com o ambiente virtual ativado:

```shell
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Administração disponível em http://127.0.0.1:8000/admin/.

## Carregar a trilha oficial

```shell
python manage.py migrate
python manage.py popular_sayit
```

Carrega os 10 módulos e as 71 palavras da trilha, incluindo traduções. O comando usa o título como `Modulo.nome`, o número como `Modulo.ordem` e a palavra como `Palavra.texto`. As traduções ficam em `Palavra.traducao` e o indicador de ativação em `Palavra.ativa`.

Executar novamente atualiza os módulos pelo nome e as palavras pelo par módulo/texto, sem duplicá-los. Não remova nem renomeie esses identificadores se quiser que a próxima execução reconheça os mesmos registros. Dicas e registros extras são preservados. A carga inteira ocorre em uma transação: qualquer falha desfaz as alterações dessa execução.

## Modelos

- `Usuario`: herda de `AbstractUser`, com `data_nascimento` opcional. `AUTH_USER_MODEL = 'core.Usuario'`.
- `Modulo`: nome, descrição, ordem e indicador ativo.
- `Palavra`: pertence a um módulo; texto único dentro dele, dica e ordem.
- `Progresso`: percentual de 0 a 100, único por usuário e módulo; 100 representa conclusão.
- `Sessao`: pertence a um usuário, com início e fim opcional; fim não pode anteceder início.
- `Tentativa`: pertence diretamente a um usuário e a uma palavra, com sessão opcional. Registra `resposta_reconhecida`, `resultado` (`correto`, `incorreto` ou `nao_reconhecido`), `pontuacao` inteira não negativa, `feedback` e `data_hora`. Resposta e feedback podem ficar vazios.

Quando houver sessão, a validação do modelo (`full_clean()`, também executada pelos formulários do admin) exige que ela pertença ao usuário da tentativa. Ao gravar diretamente pelo ORM, execute `full_clean()` antes de `save()` para validar essa relação. Os resultados permitidos e a unicidade do progresso também são garantidos no SQLite.

A migração de atualização preserva respostas e datas anteriores, copia o usuário da sessão e converte `acertou` em `correto` ou `incorreto`.

Uma sessão pode conter palavras de diferentes módulos. O progresso é armazenado explicitamente e não é calculado automaticamente a partir das tentativas. A exclusão de palavras com tentativas é protegida para preservar o histórico. Excluir um usuário remove suas sessões, tentativas e progressos.

Os campos e relacionamentos usam recursos compatíveis com SQLite. A migração inicial inclui o usuário personalizado antes da criação das tabelas de autenticação dependentes.

Configurações geradas para uso local (`DEBUG=True`); ajuste segredo, hosts e demais configurações antes de publicar.
