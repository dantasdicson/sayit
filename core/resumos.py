"""Conteúdo dos resumos habilitados; mídia relativa ao storage de MEDIA_ROOT."""


def encerramento_resumo(numero):
    if numero == 10:
        return ('Você terminou os desafios! Veja seu resultado para finalizar a trilha. '
                'Continue praticando: você pode voltar aos módulos sempre que quiser.')
    return (f'Você terminou a revisão do módulo {numero}. '
            f'Vamos para o próximo: o módulo {numero + 1}!')

RESUMOS = {
    9: {
        'subtitulo': 'Os dois sons de OO',
        'paragrafos': (
            'Você ouviu e falou MOON e BOOK, FOOD e GOOD, ROOM e LOOK, SCHOOL e FOOT.',
            'Nestes pares, a primeira palavra tem um som longo e a segunda tem um som curto.',
            'Observe a posição da boca, escute cada palavra e repita sem pressa!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão dos sons de OO.',
        'audio': 'modulos/9/resumo.mp3',
        'conclusao': 'conclusao_modulo_9',
    },
    8: {
        'subtitulo': 'O som PH',
        'paragrafos': (
            'Você ouviu e falou PHONE e PHOTO, ELEPHANT e DOLPHIN, ALPHABET e TROPHY, GRAPH e SPHERE.',
            'Nestas palavras, P e H trabalham juntos e fazem o som de F.',
            'O PH pode aparecer no começo, no meio ou no final das palavras. Escute e repita com calma!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão do som PH.',
        'audio': 'modulos/8/resumo.mp3',
        'conclusao': 'conclusao_modulo_8',
    },
    7: {
        'subtitulo': 'Os dois sons de TH',
        'paragrafos': (
            'Você ouviu e falou THINK e THIS, TOOTH e THAT, BATH e MOTHER, THUMB e FATHER.',
            'Para fazer o som TH, coloque de leve a ponta da língua entre os dentes e sopre.',
            'Na primeira palavra de cada par, a garganta não vibra. Na segunda, ela vibra. Escute e repita com calma!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão dos sons de TH.',
        'audio': 'modulos/7/resumo.mp3',
        'conclusao': 'conclusao_modulo_7',
    },
    6: {
        'subtitulo': 'O som CH',
        'paragrafos': (
            'Você ouviu e falou CHAIR e CHICKEN, CHEESE e BEACH, CHILD e CHOCOLATE, CHERRY e PEACH.',
            'Nestas palavras, C e H juntos fazem um som parecido com tch.',
            'Esse som pode aparecer no começo ou no final das palavras. Escute e repita com calma!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão do som CH.',
        'audio': 'modulos/6/resumo.mp3',
        'conclusao': 'conclusao_modulo_6',
    },
    5: {
        'subtitulo': 'O som SH',
        'paragrafos': (
            'Você ouviu e falou SHIP e FISH, SHARK e SHEEP, SHOP e SHOVEL, DISH e BRUSH.',
            'As letras S e H juntas fazem um som parecido com um pedido de silêncio.',
            'Esse som pode aparecer no começo ou no final das palavras. Escute e repita com calma!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão do som SH.',
        'audio': 'modulos/5/resumo.mp3',
        'conclusao': 'conclusao_modulo_5',
    },
    4: {
        'subtitulo': 'Magic E — Som do U',
        'paragrafos': (
            'Você ouviu e falou CUB e CUBE, TUB e TUBE, CUT e CUTE, PLUM e PLUME.',
            'Nessas palavras, o E no final fica silencioso e muda o som do U. Escute a diferença em cada par.',
            'Compare as palavras de cada par: uma letra no final muda o som e o significado!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão do Magic E — som do U.',
        'audio': 'modulos/4/resumo.mp3',
        'conclusao': 'conclusao_modulo_4',
    },
    3: {
        'subtitulo': 'Magic E — Som do O',
        'paragrafos': (
            'Você ouviu e falou HOP e HOPE, NOT e NOTE, ROB e ROBE, COP e COPE.',
            'Nessas palavras, o E no final fica silencioso e faz o O soar como o nome da letra O em inglês.',
            'Compare as palavras de cada par: uma letra no final muda o som e o significado!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão do Magic E — som do O.',
        'audio': 'modulos/3/resumo.mp3',
        'conclusao': 'conclusao_modulo_3',
    },
    2: {
        'subtitulo': 'Magic E — Sons de A e I',
        'paragrafos': (
            'Você ouviu e falou BIT e BITE, CAN e CANE, PIN e PINE, SIT e SITE.',
            'O E final fica silencioso e muda o som da vogal: o A no segundo par, e o I nos outros três pares.',
            'Compare as palavras de cada par: uma letra no final muda o som e o significado!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão do Magic E — sons de A e I.',
        'audio': 'modulos/2/resumo.mp3',
        'conclusao': 'conclusao_modulo_2',
    },
    1: {
        'subtitulo': 'Magic E — Som do A',
        'paragrafos': (
            'Você descobriu que a letra E no final de algumas palavras pode mudar o som da vogal A.',
            'O E final fica silencioso e muda o som do A.',
        ),
        'reforco': 'Nessas palavras, o E final fica silencioso e muda o jeito de falar o A. Uma letra pode fazer diferença!',
        'audio': 'modulos/1/resumo.mp3',
        'conclusao': 'conclusao_modulo_1',
    },
}

for numero, resumo in RESUMOS.items():
    resumo['reforco'] = encerramento_resumo(numero)
