# Recuperação de senha — SayIt!

## Uso

1. Na tela de entrada, selecione **Esqueci minha senha**.
2. Informe o e-mail usado no cadastro e selecione **Enviar link de recuperação**.
3. Confira sua caixa de entrada e a pasta de spam. Se necessário, peça ajuda a um responsável.
4. Abra o link recebido, informe e confirme uma nova senha e selecione **Salvar nova senha**.
5. Volte à tela de entrada e use a nova senha. O progresso da conta é preservado.

O link vale por **1 hora**, não efetua login automaticamente e deixa de funcionar após a troca de senha. Links inválidos, expirados ou já utilizados exibem uma opção para solicitar outro. Solicitar recuperação não altera a senha atual. A confirmação não informa se o e-mail existe no banco.

## Testes locais e pelo celular

O backend padrão é `django.core.mail.backends.console.EmailBackend`: a mensagem aparece no terminal do Django, **sem envio à caixa de entrada**. Quando o servidor é iniciado em segundo plano nesta instalação, consulte `work/sayit/.runlogs/server.out.log`. O log contém links sensíveis de recuperação; não publique nem compartilhe seu conteúdo.

Cadastre uma conta de teste com um e-mail válido, solicite a recuperação e abra o link registrado no log. Para testar no celular, faça a solicitação pelo endereço HTTPS do túnel, pois o link utiliza o mesmo domínio da solicitação. Para domínios `.trycloudflare.com`, o link é HTTPS mesmo que o Django receba HTTP do túnel local. O computador, servidor e túnel precisam continuar ativos. Reiniciar o túnel pode mudar o endereço e exigir uma nova solicitação.

## Configuração de envio real

Copie `.env.example` para `.env` na raiz do repositório e configure os dados de SMTP fornecidos pelo provedor:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.seu-provedor.com
EMAIL_PORT=587
EMAIL_HOST_USER=seu-usuario
EMAIL_HOST_PASSWORD=sua-senha-de-aplicativo
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
DEFAULT_FROM_EMAIL=SayIt! <contato@seu-dominio.com>
```

Use um remetente autorizado pelo provedor e, quando exigido, uma senha de aplicativo. Para SSL implícito, normalmente use porta 465, `EMAIL_USE_TLS=false` e `EMAIL_USE_SSL=true`; confirme os valores com o provedor. TLS e SSL não podem estar ativos simultaneamente. Reinicie o servidor após alterar `.env`. O timeout de SMTP é 15 segundos.

O arquivo `.env` é ignorado pelo Git; não coloque credenciais na documentação ou nos commits. A entrega real precisa ser validada com uma caixa de testes após configurar o provedor. O Django registra falhas de envio no log e mantém a confirmação genérica para o usuário; uma tela de confirmação não prova a entrega da mensagem.

Em hospedagem definitiva, configure o domínio exato em `ALLOWED_HOSTS`, use HTTPS e configure o proxy confiável de acordo com a infraestrutura. Os links são gerados pelo host validado da solicitação. Não habilite confiança global em cabeçalhos de proxy sem garantir que o proxy os sobrescreve. A configuração de túnel local não substitui a configuração de produção.

## Implementação

| Rota | Nome Django | Função |
| --- | --- | --- |
| `/esqueci-minha-senha/` | `password_reset` | Solicitar link por e-mail |
| `/esqueci-minha-senha/enviado/` | `password_reset_done` | Confirmação genérica |
| `/redefinir-senha/<uidb64>/<token>/` | `password_reset_confirm` | Validar link e definir nova senha |
| `/redefinir-senha/concluido/` | `password_reset_complete` | Confirmação da alteração |

O fluxo usa as views e formulários de autenticação do Django, com templates em português que herdam o layout público responsivo existente. O token é validado pelo `default_token_generator`, com `PASSWORD_RESET_TIMEOUT=3600`. Somente contas ativas com senha utilizável recebem a mensagem; a busca de e-mail ignora maiúsculas e minúsculas.

O Django remove o token da URL após validá-lo e o mantém na sessão durante a troca. A senha passa pelos validadores já utilizados no cadastro, é armazenada com hash e invalida sessões anteriores da conta. Os formulários exigem CSRF; nenhum token é mostrado na confirmação pública. A recuperação não altera dados pessoais, tentativas nem progresso, e não requer migração do banco.

Antes de uso público em produção, configure limitação de solicitações no proxy/serviço de aplicação para reduzir abuso de envio. Esta implementação não adiciona limitação de frequência nem uma fila de e-mail.

## Validação

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test core.test_auth core.test_password_reset --noinput
```

Os testes usam o backend de e-mail em memória, sem enviar mensagens reais, e verificam solicitação, endereço desconhecido/inativo, validação de campos, HTTPS, troca completa, senha antiga, reutilização, expiração, link adulterado, invalidação de sessão e CSRF. Verifique também a apresentação no celular e a entrega real ao configurar SMTP.
