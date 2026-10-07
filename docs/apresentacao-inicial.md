# Apresentação inicial

A página inicial apresenta um diálogo curto explicando imagens e áudio, prática
de fala, trilha progressiva e desafios finais. O microfone é solicitado somente
na atividade de fala. A apresentação não solicita permissões.

**Vamos começar** registra a apresentação como vista e abre a trilha.
**Explorar depois**, o botão de fechar e Escape registram a apresentação como
vista e retornam ao início. A opção **Como funciona o SayIt?** abre novamente.

O registro fica no PostgreSQL (`Usuario.apresentacao_vista_em`), separado do
progresso pedagógico. Vale para a conta em outros dispositivos e sessões.
Contas existentes também recebem a introdução uma vez após essa atualização.
Somente uma ação POST autenticada e protegida por CSRF altera o registro;
abrir a página não marca a introdução como lida.

O diálogo nativo contém foco e permite navegação por teclado. Em navegadores
sem suporte a showModal ou sem JavaScript, o conteúdo permanece disponível
com os botões de formulário, sem depender de armazenamento do navegador.
