from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Comparacao, Modulo, Palavra


MODULOS = [
    {
        "numero": 1,
        "titulo": "Magic E: mudança do som do A",
        "descricao": "Aprenda como o E final silencioso pode modificar a pronúncia da vogal A.",
        "palavras": [
            ("cat", "gato", 1),
            ("cake", "bolo", 2),
            ("cap", "boné", 3),
            ("cape", "capa", 4),
            ("tap", "tocar", 5),
            ("tape", "fita", 6),
            ("mad", "zangado", 7),
            ("made", "feito", 8),
        ],
    },
    {
        "numero": 2,
        "titulo": "Magic E: mudança dos sons de A e I",
        "descricao": "Compare quatro pares e descubra como o E final muda os sons de A e I.",
        "palavras": [
            ("bit", "broca", 1),
            ("bite", "mordida", 2),
            ("can", "lata", 3),
            ("cane", "bengala", 4),
            ("pin", "alfinete", 5),
            ("pine", "pinheiro", 6),
            ("sit", "sentar", 7),
            ("site", "local", 8),
        ],
    },
    {
        "numero": 3,
        "titulo": "Magic E: mudança do som do O",
        "descricao": "Aprenda como o E final silencioso pode modificar a pronúncia da vogal O.",
        "palavras": [
            ("hop", "pular", 1),
            ("hope", "esperança", 2),
            ("not", "não", 3),
            ("note", "nota", 4),
            ("rob", "roubar", 5),
            ("robe", "roupão", 6),
            ("cop", "policial", 7),
            ("cope", "lidar com uma dificuldade", 8),
        ],
    },
    {
        "numero": 4,
        "titulo": "Magic E: mudança do som do U",
        "descricao": "Aprenda como o E final silencioso pode modificar a pronúncia da vogal U.",
        "palavras": [
            ("cub", "filhote", 1),
            ("cube", "cubo", 2),
            ("tub", "banheira", 3),
            ("tube", "tubo", 4),
            ("cut", "cortar", 5),
            ("cute", "fofo", 6),
            ("plum", "ameixa", 7),
            ("plume", "pluma", 8),
        ],
    },
    {
        "numero": 5,
        "titulo": "SH",
        "descricao": "Aprenda a reconhecer e pronunciar palavras que apresentam a combinação SH.",
        "palavras": [
            ("ship", "navio", 1),
            ("fish", "peixe", 2),
            ("shark", "tubarão", 3),
            ("sheep", "ovelha", 4),
            ("shop", "loja", 5),
            ("shovel", "pá", 6),
            ("dish", "prato", 7),
            ("brush", "escova", 8),
        ],
    },
    {
        "numero": 6,
        "titulo": "CH",
        "descricao": "Aprenda a reconhecer e pronunciar palavras que apresentam a combinação CH.",
        "palavras": [
            ("chair", "cadeira", 1),
            ("chicken", "galinha", 2),
            ("cheese", "queijo", 3),
            ("beach", "praia", 4),
            ("child", "criança", 5),
            ("chocolate", "chocolate", 6),
            ("cherry", "cereja", 7),
            ("peach", "pêssego", 8),
        ],
    },
    {
        "numero": 7,
        "titulo": "TH",
        "descricao": "Aprenda os dois principais sons encontrados na combinação TH.",
        "palavras": [
            ("think", "pensar", 1),
            ("tooth", "dente", 2),
            ("bath", "banho", 3),
            ("this", "isto", 4),
            ("that", "aquilo", 5),
            ("mother", "mãe", 6),
            ("thumb", "polegar", 7),
            ("father", "pai", 8),
        ],
    },
    {
        "numero": 8,
        "titulo": "PH",
        "descricao": "Aprenda palavras em que a combinação PH normalmente possui som de F.",
        "palavras": [
            ("phone", "telefone", 1),
            ("photo", "foto", 2),
            ("elephant", "elefante", 3),
            ("dolphin", "golfinho", 4),
            ("alphabet", "alfabeto", 5),
            ("trophy", "troféu", 6),
            ("graph", "gráfico", 7),
            ("sphere", "esfera", 8),
        ],
    },
    {
        "numero": 9,
        "titulo": "OO",
        "descricao": "Compare diferentes sons encontrados em palavras escritas com a combinação OO.",
        "palavras": [
            ("moon", "lua", 1),
            ("food", "comida", 2),
            ("room", "quarto", 3),
            ("school", "escola", 4),
            ("book", "livro", 5),
            ("look", "olhar", 6),
            ("good", "bom", 7),
            ("foot", "pé", 8),
        ],
    },
    {
        "numero": 10,
        "titulo": "Desafio Final",
        "descricao": "Monte e fale frases em inglês em três desafios para concluir sua jornada.",
        "palavras": [
            ("cat", "gato", 1),
            ("cake", "bolo", 2),
            ("kit", "kit", 3),
            ("kite", "pipa", 4),
            ("hop", "pular", 5),
            ("hope", "esperança", 6),
            ("cub", "filhote", 7),
            ("cube", "cubo", 8),
            ("ship", "navio", 9),
            ("chip", "chip", 10),
            ("think", "pensar", 11),
            ("this", "isto", 12),
            ("book", "livro", 13),
            ("moon", "lua", 14),
        ],
    },
]


CONTEUDOS_TEORICOS = {
    1: "O E no final fica silencioso e pode mudar o som do A. Compare cat e cake: em cake, o A soa como seu nome em inglês. Escute e repita devagar!",
    2: "Compare BIT e BITE, CAN e CANE, PIN e PINE, SIT e SITE. O E final é silencioso e muda o som da vogal: o A em CAN e CANE, e o I nos outros três pares.",
    3: "O E no final pode mudar o som do O sem ter um som próprio. Compare hop e hope e repita cada palavra com calma.",
    4: "O E silencioso pode mudar o som do U. Compare cub e cube, tub e tube, cut e cute, plum e plume. Escute cada palavra: a pronúncia também pode variar entre sotaques.",
    5: "S e H juntos fazem um som parecido com o pedido de silêncio: shhh! Procure esse som em ship e fish. Ele pode aparecer no começo ou no final.",
    6: "Nestas palavras, C e H juntos fazem um som parecido com tch. Escute chair e beach e tente repetir. Nem toda palavra com CH segue essa regra!",
    7: "Para experimentar TH, coloque de leve a ponta da língua entre os dentes e sopre. Em think, a garganta não vibra; em this, ela vibra. Tente sentir a diferença!",
    8: "P e H juntos costumam soar como F. Escute phone e elephant e procure esse som. Duas letras podem trabalhar juntas para formar um só som!",
    9: "OO pode ter sons diferentes. Compare moon e book: a posição da boca muda, não apenas a duração do som. Ouça as palavras e repita sem pressa.",
    10: "Monte as palavras na ordem correta e use o microfone para falar a frase. Alcance pelo menos 70 pontos em cada um dos três desafios.",
}

PARES_DIDATICOS = {
    1: [("cat", "cake"), ("cap", "cape"), ("tap", "tape"), ("mad", "made")],
    2: [("bit", "bite"), ("can", "cane"), ("pin", "pine"), ("sit", "site")],
    3: [("hop", "hope"), ("not", "note"), ("rob", "robe"), ("cop", "cope")],
    4: [("cub", "cube"), ("tub", "tube"), ("cut", "cute"), ("plum", "plume")],
    5: [("ship", "fish"), ("shark", "sheep"), ("shop", "shovel"), ("dish", "brush")],
    6: [("chair", "chicken"), ("cheese", "beach"), ("child", "chocolate"), ("cherry", "peach")],
    7: [("think", "this"), ("tooth", "that"), ("bath", "mother"), ("thumb", "father")],
    8: [("phone", "photo"), ("elephant", "dolphin"), ("alphabet", "trophy"), ("graph", "sphere")],
    9: [("moon", "book"), ("food", "good"), ("room", "look"), ("school", "foot")],
    10: [("cat", "cake"), ("ship", "chip"), ("think", "this"), ("moon", "book")],
}


class Command(BaseCommand):
    help = "Popula o banco de dados com os módulos, palavras e comparações do SayIt!"

    def add_arguments(self, parser):
        parser.add_argument('--modulo', type=int, choices=range(1, 11),
                            help='Limita a carga ao módulo informado.')

    def handle(self, *args, **options):
        modulos = [m for m in MODULOS if options.get('modulo') in (None, m['numero'])]
        totais = {"modulos": 0, "palavras": 0, "comparacoes": 0}
        with transaction.atomic():
            for dados_modulo in modulos:
                modulo, _ = Modulo.objects.update_or_create(
                    numero=dados_modulo["numero"],
                    defaults={
                        "titulo": dados_modulo["titulo"],
                        "descricao": dados_modulo["descricao"],
                        "conteudo_teorico": CONTEUDOS_TEORICOS[dados_modulo["numero"]],
                        "ordem": dados_modulo["numero"],
                        "ativo": True,
                    },
                )
                totais["modulos"] += 1
                if modulo.numero == 10 and modulo.palavras.exists():
                    # O novo desafio usa frases; o catálogo legado é só histórico.
                    continue
                # Libera todas as posições antes de renomear ou criar palavras.
                existentes = list(modulo.palavras.all())
                limite = max([p.ordem for p in existentes] + [len(dados_modulo["palavras"])])
                for indice, p in enumerate(existentes, 1):
                    p.ordem = limite + indice
                    p.save(update_fields=["ordem"])
                comparacoes = list(modulo.comparacoes.all())
                limite = max([c.ordem for c in comparacoes] + [0])
                for indice, c in enumerate(comparacoes, 1):
                    c.ordem = limite + indice
                    c.save(update_fields=["ordem"])
                if modulo.numero == 2:
                    # Mantém as palavras antigas inativas para preservar seu histórico.
                    modulo.palavras.exclude(
                        palavra__in=[p[0] for p in dados_modulo["palavras"]]
                    ).update(ativa=False)
                # Mantém o PK e os acertos da versão inicial do Módulo 5.
                if modulo.numero == 5 and not modulo.palavras.filter(palavra='shark').exists():
                    modulo.palavras.filter(palavra='shoe').update(
                        palavra='shark', traducao='tubarão', imagem='', audio=''
                    )
                if modulo.numero == 5 and not modulo.palavras.filter(palavra='shovel').exists():
                    modulo.palavras.filter(palavra='shell').update(
                        palavra='shovel', traducao='pá', imagem='', audio=''
                    )
                # Mantém o PK e eventuais acertos durante a troca pedagógica no Módulo 7.
                if modulo.numero == 7 and not modulo.palavras.filter(palavra='tooth').exists():
                    modulo.palavras.filter(palavra='three').update(
                        palavra='tooth', traducao='dente', imagem='', audio=''
                    )
                palavras_modulo = {}
                for palavra, traducao, ordem in dados_modulo["palavras"]:
                    registro, _ = Palavra.objects.update_or_create(
                        modulo=modulo,
                        palavra=palavra,
                        defaults={
                            "traducao": traducao,
                            "observacao": "",
                            "ordem": ordem,
                            "ativa": True,
                        },
                    )
                    palavras_modulo[palavra] = registro
                    totais["palavras"] += 1

                if modulo.numero == 10:
                    # Preserva palavras e tentativas legadas fora dos quatro pares.
                    ativas = {p for par in PARES_DIDATICOS[10] for p in par}
                    modulo.palavras.exclude(palavra__in=ativas).update(ativa=False)
                ids_comparacoes = []
                for ordem, (base, destino) in enumerate(
                    PARES_DIDATICOS.get(modulo.numero, []), start=1
                ):
                    comparacao = Comparacao.objects.filter(
                        modulo=modulo,
                        palavra_base=palavras_modulo[base],
                        palavra_comparada=palavras_modulo[destino],
                    ).first()
                    if comparacao is None:
                        comparacao = Comparacao(
                            modulo=modulo,
                            palavra_base=palavras_modulo[base],
                            palavra_comparada=palavras_modulo[destino],
                        )
                    comparacao.explicacao = (
                        f"Escute {base} e {destino}: procure o som SH nas duas palavras. "
                        "S e H juntos fazem um som parecido com o pedido de silêncio: shhh!"
                    ) if modulo.numero == 5 else (
                        f"Escute {base} e {destino}: procure o som CH nas duas palavras. "
                        "C e H juntos fazem um som parecido com tch."
                    ) if modulo.numero == 6 else (
                        f"Escute {base} e {destino}: compare os dois sons de TH. "
                        f"Em {base}, a garganta não vibra; em {destino}, ela vibra."
                    ) if modulo.numero == 7 else (
                        f"Escute {base} e {destino}: procure o som de F nas duas palavras. "
                        "Nestas palavras, P e H trabalham juntos e soam como F."
                    ) if modulo.numero == 8 else (
                        f"Escute {base} e {destino}: compare os dois sons de OO. "
                        f"Em {base}, o som é longo; em {destino}, o som é curto."
                    ) if modulo.numero == 9 else (
                        f"Compare {base} e {destino}: o E final de {destino} "
                        "é silencioso e muda o som da vogal. "
                        "Observe também as outras letras e o significado de cada palavra."
                    )
                    if modulo.numero == 10:
                        comparacao.explicacao = {
                            'cat': 'Compare cat e cake: o E final é silencioso e muda o som do A.',
                            'ship': 'Compare ship e chip: SH soa como um pedido de silêncio; CH soa parecido com tch.',
                            'think': 'Compare think e this: em think, a garganta não vibra; em this, ela vibra.',
                            'moon': 'Compare moon e book: OO tem sons diferentes. Observe a posição da boca e escute cada palavra.',
                        }[base]
                    comparacao.ordem = ordem
                    comparacao.full_clean()
                    comparacao.save()
                    ids_comparacoes.append(comparacao.pk)
                    totais["comparacoes"] += 1
                modulo.comparacoes.exclude(pk__in=ids_comparacoes).delete()

        for dados_modulo in modulos:
            self.stdout.write(self.style.SUCCESS(
                f'Módulo {dados_modulo["numero"]} - {dados_modulo["titulo"]} carregado.'
            ))
        self.stdout.write(self.style.SUCCESS(
            "Carga do SayIt! concluída: "
            f'{totais["modulos"]} módulos, '
            f'{totais["palavras"]} palavras, '
            f'{totais["comparacoes"]} comparações.'
        ))
