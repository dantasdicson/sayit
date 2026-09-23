"""Conteúdo dos resumos habilitados; mídia relativa ao storage de MEDIA_ROOT."""


def encerramento_resumo(numero):
    return (f'Você terminou a revisão do módulo {numero}. '
            f'Vamos para o próximo: o módulo {numero + 1}!')

RESUMOS = {
    9: {
        'subtitulo': 'Os dois sons de OO',
        'paragrafos': (
            'Você ouviu e falou MOON e BOOK, FOOD e GOOD, ROOM e LOOK, SCHOOL e FOOT.',
            'A combinação OO pode ter um som longo, como em MOON, ou um som curto, como em BOOK.',
            'Observe a posição da boca, escute cada palavra e repita sem pressa!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão dos sons de OO.',
        'audio': 'modulos/9/resumo.mp3',
        'conclusao': 'conclusao_modulo_9',
    },
    8: {
        'subtitulo': 'O som PH',
        'paragrafos': (
            'Você ouviu e falou PHONE e PHOTO, ELEPHANT e DOLPHIN, ALPHABET e TROPHY.',
            'Nestas palavras, P e H trabalham juntos e fazem o som de F.',
            'O PH pode aparecer no começo ou no meio das palavras. Escute e repita com calma!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão do som PH.',
        'audio': 'modulos/8/resumo.mp3',
        'conclusao': 'conclusao_modulo_8',
    },
    7: {
        'subtitulo': 'Os dois sons de TH',
        'paragrafos': (
            'Você ouviu e falou THINK e THIS, TOOTH e THAT, BATH e MOTHER.',
            'Para fazer o som TH, coloque de leve a ponta da língua entre os dentes e sopre.',
            'Em THINK, TOOTH e BATH, a garganta não vibra. Em THIS, THAT e MOTHER, ela vibra. Escute e repita com calma!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão dos sons de TH.',
        'audio': 'modulos/7/resumo.mp3',
        'conclusao': 'conclusao_modulo_7',
    },
    6: {
        'subtitulo': 'O som CH',
        'paragrafos': (
            'Você ouviu e falou CHAIR e CHICKEN, CHEESE e BEACH, CHILD e CHOCOLATE.',
            'Nestas palavras, C e H juntos fazem um som parecido com tch.',
            'O som CH pode aparecer no começo, como em CHAIR, ou no final, como em BEACH. Escute e repita com calma!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão do som CH.',
        'audio': 'modulos/6/resumo.mp3',
        'conclusao': 'conclusao_modulo_6',
    },
    5: {
        'subtitulo': 'O som SH',
        'paragrafos': (
            'Você ouviu e falou SHIP e FISH, SHARK e SHEEP, SHOP e SHOVEL.',
            'S e H juntos fazem um som parecido com o pedido de silêncio: shhh!',
            'Esse som aparece no começo de SHIP e no final de FISH. Escute e repita com calma!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão do som SH.',
        'audio': 'modulos/5/resumo.mp3',
        'conclusao': 'conclusao_modulo_5',
    },
    4: {
        'subtitulo': 'Magic E — Som do U',
        'paragrafos': (
            'Você ouviu e falou CUB e CUBE, TUB e TUBE, CUT e CUTE.',
            'Nessas palavras, o E no final fica silencioso e pode fazer o U soar como o nome da letra U em inglês.',
            'Compare CUB e CUBE: uma letra no final muda o som e o significado da palavra!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão do Magic E — som do U.',
        'audio': 'modulos/4/resumo.mp3',
        'conclusao': 'conclusao_modulo_4',
    },
    3: {
        'subtitulo': 'Magic E — Som do O',
        'paragrafos': (
            'Você ouviu e falou HOP e HOPE, NOT e NOTE, ROB e ROBE.',
            'Nessas palavras, o E no final fica silencioso e faz o O soar como o nome da letra O em inglês.',
            'Compare HOP e HOPE: uma letra no final muda o som e o significado da palavra!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão do Magic E — som do O.',
        'audio': 'modulos/3/resumo.mp3',
        'conclusao': 'conclusao_modulo_3',
    },
    2: {
        'subtitulo': 'Magic E — Som do I',
        'paragrafos': (
            'Você ouviu e falou BIT e BITE, CAN e CANE, PIN e PINE, SIT e SITE.',
            'Nessas palavras, o E no final fica silencioso e faz o I soar como o nome da letra I em inglês.',
            'Compare CAN e CANE: uma letra no final muda o som e o significado da palavra!',
        ),
        'reforco': 'Muito bem! Você terminou a revisão do Magic E — som do I.',
        'audio': 'modulos/2/resumo.mp3',
        'conclusao': 'conclusao_modulo_2',
    },
    1: {
        'subtitulo': 'Magic E — Som do A',
        'paragrafos': (
            'Você descobriu que a letra E no final de algumas palavras pode mudar o som da vogal A.',
            'Esse E geralmente não é pronunciado, mas faz o A ter um som longo, como o nome da letra A em inglês.',
        ),
        'reforco': 'Nessas palavras, o E final fica silencioso e muda o jeito de falar o A. Uma letra pode fazer diferença!',
        'audio': 'modulos/1/resumo.mp3',
        'conclusao': 'conclusao_modulo_1',
    },
}

for numero, resumo in RESUMOS.items():
    resumo['reforco'] = encerramento_resumo(numero)
