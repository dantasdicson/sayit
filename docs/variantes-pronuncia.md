# Exceções de reconhecimento de voz

As variantes em `core/data/pronuncia_variantes.json` são compartilhadas pela validação Python e JavaScript. São exceções explícitas de transcrição, sem comparação por similaridade.

## BIT

Para a palavra esperada `bit`, a transcrição `bitch` é aceita como acerto por solicitação do responsável pelo projeto. O feedback de acerto mostra `bit`; a transcrição original continua registrada no banco para análise. A exceção não vale para `bite`, frases ou plurais, e o par didático `bit / bite` permanece no catálogo.

Essa exceção é uma tolerância ao reconhecimento automático, não uma equivalência de pronúncia: torna a avaliação de `bit` mais permissiva. Os arquivos de áudio e as palavras apresentadas não mudam.

## CANE

Para a palavra esperada `cane`, a transcrição `kane` é aceita como acerto e exibida como `cane` no feedback. A transcrição original permanece no registro. A exceção não vale para `can`, plurais ou frases.

## BEACH

Para a palavra esperada `beach`, a transcrição `bitch` também é aceita por solicitação do responsável pelo projeto. O feedback mostra `beach`, preservando a transcrição original no banco. A exceção é uma tolerância ao reconhecimento automático, não uma equivalência de pronúncia; não aceita frases nem plurais.

A forma censurada exata `b****`, observada no Chrome do celular, também é aceita exclusivamente para `beach`. Não se trata de um curinga: outras quantidades de asteriscos e outras palavras não são aceitas por essa regra.

Validação: `manage.py test core.test_pronuncia` e `node --test core/static/core/tests/pratica_pronuncia.test.cjs`.
