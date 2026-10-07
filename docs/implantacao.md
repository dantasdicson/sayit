# PostgreSQL, Render Free e Vercel

O SayIt usa PostgreSQL 17, Django no Render e Vercel como entrada pública.
Os templates continuam no Django. Vercel encaminha páginas, APIs, arquivos e
cookies para o Render; não contém banco nem outra implementação das telas.

## Configuração local

1. Instale PostgreSQL 17 e crie um usuário e banco `sayit`.
2. Crie o ambiente Python 3.12 e instale `pip install -r requirements.txt`.
3. Copie `.env.example` para `.env` e configure `DATABASE_URL` e `SECRET_KEY`.
4. Execute `python manage.py migrate`, `python manage.py inicializar_catalogo`,
   `python manage.py runserver`. Use `createsuperuser` para o administrador local.
5. Execute `python manage.py collectstatic --noinput` antes de testes de produção.

O ambiente local preparado nesta revisão usa PostgreSQL em `127.0.0.1:5433`.
As credenciais ficam apenas em `.env`. O banco, backups e exportações privadas
não pertencem ao Git. O banco anterior está preservado para recuperação.

## Render: criação gratuita

1. Envie os arquivos revisados para `master` do repositório `dantasdicson/sayit`.
2. Em **New > Blueprint**, conecte esse repositório.
3. Use nome `sayit`, branch `master`, caminho `render.yaml`.
4. Confirme que **Web Service sayit** e **Postgres sayit-postgres** usam **Free**.
   Não selecione plano pago ou disco persistente nesta configuração.
5. Crie o Blueprint. O Render gera `SECRET_KEY` e fornece `DATABASE_URL` interna.
6. Acompanhe os logs. O build instala dependências e coleta estáticos. Na
   inicialização, as migrações são aplicadas e o catálogo é carregado apenas se
   estiver vazio. Reinícios preservam conteúdo e progresso no PostgreSQL.
7. Abra `https://SEU-SERVICO.onrender.com/health/` e confirme `{"status":"ok"}`.
8. Para o admin no plano sem Shell, adicione em **Environment**:
   `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` com dados escolhidos por você.
   Faça redeploy. A senha precisa passar pelos validadores Django. Após a criação,
   remova as três variáveis. O comando não redefine contas existentes.

O catálogo público contém somente módulos, palavras e comparações. As contas
locais e seus históricos não são publicados automaticamente.

## Vercel: criação do projeto

1. Importe o mesmo repositório. Selecione **Root Directory: deploy/vercel**.
2. Selecione **Framework Preset: Other**; o build é `npm run build`.
3. Adicione `RENDER_ORIGIN=https://SEU-SERVICO.onrender.com` nos ambientes desejados.
4. Faça deploy. `build.mjs` gera a configuração da Build Output API com o proxy.
5. No Render, configure `PUBLIC_BASE_URL=https://SEU-PROJETO.vercel.app` e
   `CSRF_TRUSTED_ORIGINS=https://SEU-PROJETO.vercel.app`.
   `ALLOWED_HOSTS` pode listar esse host e o host exato do Render, separados por
   vírgula. Ambos também são adicionados pela configuração de domínio público.
6. Faça redeploy no Render e teste login, cadastro, logout e recuperação pelo
   domínio Vercel. Os cookies são seguros; páginas privadas possuem `no-store`.
7. URLs de preview adicionais só devem ser habilitadas por domínio explícito,
   com banco separado se forem usadas para testes destrutivos.

`TRUST_PROXY_SSL_HEADER=true` é definido no Render para o proxy HTTPS da plataforma.
`X-Forwarded-Host` não é usado. O domínio dos links de senha vem de `PUBLIC_BASE_URL`.
Não há necessidade de CORS entre as telas: o navegador usa um único domínio.

`check --deploy` registra dois avisos opcionais (W005 e W021): HSTS cobre o host
atual, sem incluir subdomínios nem solicitar preload. Essa escolha mantém o escopo
do domínio utilizado na demonstração; o build bloqueia erros, não esses avisos.

## Recuperação de senha no Render Free

O plano gratuito bloqueia SMTP nas portas 25, 465 e 587. Há um backend preparado
para a API HTTPS do Resend, sem dependência de SMTP.

1. Crie uma conta no Resend e uma chave de envio. Cadastre e verifique seu domínio
   para enviar a destinatários reais. O remetente de teste do Resend tem restrições
   de destinatário; não representa recuperação disponível para todos os usuários.
2. Configure no Render `RESEND_API_KEY` e `DEFAULT_FROM_EMAIL=SayIt <contato@SEU-DOMINIO>`.
3. O Blueprint define `EMAIL_BACKEND=core.email_backend.ResendEmailBackend`.
4. Faça redeploy e solicite recuperação para uma conta de teste. Confirme a chegada
   do e-mail, o domínio Vercel no link e a invalidação após trocar a senha.

Sem chave e remetente válidos, a entrega real de e-mail permanece pendente.
Nunca cole chaves no relatório, no Git ou em conversas públicas.

## Dados existentes, backup e migração

Na revisão local, 252 registros foram transferidos e comparados campo a campo:
2 usuários, 10 módulos, 74 palavras, 30 comparações, 10 progressos, 1 tentativa
de frase e 125 tentativas de palavras. Os conteúdos exportados e importados são
idênticos. Sessões ativas e logs administrativos não fazem parte dessa exportação;
os usuários entram novamente. Os hashes de senha são preservados.

Para transferir os dados locais para um banco remoto **vazio**:

1. Pare novas gravações e faça backup privado (`pg_dump --format=custom`).
2. Exporte `dumpdata --all --exclude contenttypes --exclude auth.permission
   --exclude admin.logentry --exclude sessions.session --output dados.json`.
3. No ambiente de destino, aplique `migrate` e carregue `loaddata dados.json`.
   Não execute a inicialização automática de catálogo antes dessa importação.
4. Compare quantidades e conteúdos, valide IDs/relacionamentos e confira sequência
   de IDs. `loaddata` reinicializa as sequências PostgreSQL dos modelos importados.
5. Para acesso externo ao banco Render, autorize somente seu IP no painel, use a
   URL externa com `sslmode=require`, e remova a autorização ao concluir.
   O Blueprint bloqueia conexões externas por padrão (`ipAllowList: []`).
6. Preserve cópia privada dos arquivos de mídia junto ao backup do banco.

Backups contêm dados pessoais e hashes de senha: não publique `dados.json`.
O comando inicial de catálogo é para uma apresentação com contas novas.

## Limites da demonstração gratuita

- O banco gratuito do Render expira após **30 dias** e não possui backup gerenciado.
  Faça backup antes da expiração; não descreva esse plano como hospedagem definitiva.
- O serviço dorme após 15 minutos sem acesso; a primeira abertura pode demorar.
- Arquivos enviados ao disco local desaparecem em reinícios. Os arquivos pedagógicos
  versionados reaparecem com cada implantação. Novos uploads pelo admin não têm
  persistência garantida; alterações de mídia são distribuídas pelo Git.
- Áudios de estudantes não são gravados. O serviço de mídia aceita apenas os
  caminhos pedagógicos públicos e extensões WebP/MP3.
- Banco, SMTP/API, HTTPS e fluxo real Vercel → Render precisam ser verificados depois
  da criação dos serviços. Testes locais não comprovam disponibilidade em nuvem.

## Fontes da configuração

- [Django no Render](https://render.com/docs/deploy-django)
- [Blueprints](https://render.com/docs/blueprint-spec)
- [Limites do Render Free](https://render.com/docs/free)
- [Rewrites externos no Vercel](https://vercel.com/docs/routing/rewrites)
- [Build Output API](https://vercel.com/docs/build-output-api/configuration)
- [Envio de e-mail pelo Resend](https://resend.com/docs/api-reference/emails/send-email)
