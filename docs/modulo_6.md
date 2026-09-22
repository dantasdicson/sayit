# Módulo 6 — CH

Fluxo implementado: Trilha → Explicação → 3 descobertas → Resumo → Conclusão.

## Conteúdo

- Palavras: chair, chicken, cheese, beach, child e chocolate.
- Pares: chair/chicken, cheese/beach e child/chocolate.
- Regra: C e H juntos fazem um som parecido com “tch”.
- O Módulo 5 encaminha para a explicação do Módulo 6.
- A conclusão do Módulo 6 encaminha para a explicação do Módulo 7.

## Mídias

- Imagens WebP: `media/palavras/imagens/<palavra>.webp`, todas com 1254 × 1254 px.
- Áudios das palavras: `media/palavras/audios/<palavra>.mp3`.
- Resumo: `media/modulos/6/resumo.mp3`, 34,44 segundos, 48 kbps.
- Narração em português: `pt-BR-FranciscaNeural`.
- Palavras em inglês: `en-US-JennyNeural`.

## Validação

- `python manage.py check`: sem problemas.
- Django: 184 testes aprovados.
- JavaScript: 117 testes aprovados.
- Associação: 6 imagens e 6 áudios válidos, sem ausências ou referências quebradas.
- HTTP público: login, imagem, áudio de palavra e áudio do resumo responderam 200.

O reconhecimento por voz foi validado por testes simulados. A pronúncia humana real e as permissões do microfone no aparelho precisam ser verificadas manualmente no celular.
