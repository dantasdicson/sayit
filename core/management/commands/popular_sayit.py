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
        "titulo": "Magic E: mudança do som do I",
        "descricao": "Aprenda como o E final silencioso pode modificar a pronúncia da vogal I.",
        "palavras": [
            ("bit", "pedaço", 1),
            ("bite", "mordida", 2),
            ("can", "lata", 3),
            ("cane", "cana", 4),
            ("pin", "alfinete", 5),
            ("pine", "pinheiro", 6),
            ("sit", "sentar", 6),
            ("site", "local", 7),
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
        "titulo": "Revisão geral",
        "descricao": "Revise e compare os principais padrões de pronúncia estudados na trilha.",
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
    2: "O E silencioso pode mudar o som do I. Compare kit e kite: em kite, o I soa como seu nome em inglês. Vamos ouvir a diferença?",
    3: "O E no final pode mudar o som do O sem ter um som próprio. Compare hop e hope e repita cada palavra com calma.",
    4: "O E silencioso pode mudar o som do U. Compare cub e cube, tub e tube, cut e cute. Escute cada palavra: a pronúncia também pode variar entre sotaques.",
    5: "S e H juntos fazem um som parecido com o pedido de silêncio: shhh! Procure esse som em ship e fish. Ele pode aparecer no começo ou no final.",
    6: "Nestas palavras, C e H juntos fazem um som parecido com tch. Escute chair e beach e tente repetir. Nem toda palavra com CH segue essa regra!",
    7: "Para experimentar TH, coloque de leve a ponta da língua entre os dentes e sopre. Em think, a garganta não vibra; em this, ela vibra. Tente sentir a diferença!",
    8: "P e H juntos costumam soar como F. Escute phone e elephant e procure esse som. Duas letras podem trabalhar juntas para formar um só som!",
    9: "OO pode ter sons diferentes. Compare moon e book: a posição da boca muda, não apenas a duração do som. Ouça as palavras e repita sem pressa.",
    10: "Vamos rever o que aprendemos! Escute as palavras, procure o E silencioso e as combinações de letras. Repita com calma e tente perceber o que muda em cada som.",
}

PARES_DIDATICOS = {
    1: [("cat", "cake"), ("cap", "cape"), ("tap", "tape"), ("mad", "made")],
    2: [("bit", "bite"), ("can", "cane"), ("pin", "pine"), ("sit", "site")],
    3: [("hop", "hope"), ("not", "note"), ("rob", "robe")],
    4: [("cub", "cube"), ("tub", "tube"), ("cut", "cute")],
    5: [("ship", "fish"), ("shark", "sheep"), ("shop", "shovel")],
    6: [("chair", "chicken"), ("cheese", "beach"), ("child", "chocolate")],
    7: [("think", "this"), ("tooth", "that"), ("bath", "mother")],
    8: [("phone", "photo"), ("elephant", "dolphin"), ("alphabet", "trophy")],
    9: [("moon", "book"), ("food", "good"), ("room", "look"), ("school", "foot")],
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
                if modulo.numero == 2:
                    # Reaproveita registros antigos protegidos por tentativas.
                    for antiga, nova, traducao in [('kit', 'sit', 'sentar'), ('kite', 'site', 'local')]:
                        if modulo.palavras.filter(palavra=antiga).exists() and not modulo.palavras.filter(palavra=nova).exists():
                            modulo.palavras.filter(palavra=antiga).update(
                                palavra=nova, traducao=traducao, imagem='', audio='',
                                ordem=1000000 + modulo.palavras.filter(palavra=antiga).values_list('pk', flat=True).first()
                            )
                    for antiga, nova, traducao in [('fin', 'can', 'lata'), ('fine', 'cane', 'cana')]:
                        if not modulo.palavras.filter(palavra=nova).exists():
                            modulo.palavras.filter(palavra=antiga).update(
                                palavra=nova, traducao=traducao, imagem='', audio=''
                            )
                    # As comparações antigas podem ter a mesma ordem de uma nova;
                    # recriá-las torna a carga idempotente sem apagar tentativas.
                    modulo.comparacoes.all().delete()
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
                if modulo.numero == 2:
                    # Libera temporariamente as posições antigas antes de
                    # trocar palavras ou aumentar o catálogo. A constraint
                    # modulo_id + ordem é única no SQLite.
                    for palavra_existente in modulo.palavras.only('pk').iterator():
                        Palavra.objects.filter(pk=palavra_existente.pk).update(
                            ordem=1000000 + palavra_existente.pk
                        )
                for palavra, traducao, ordem in dados_modulo["palavras"]:
                    registro, _ = Palavra.objects.update_or_create(
                        modulo=modulo,
                        palavra=palavra,
                        defaults={
                            "traducao": traducao,
                            "observacao": "",
                            "ordem": 2000000 + ordem if modulo.numero == 2 else ordem,
                            "ativa": True,
                        },
                    )
                    palavras_modulo[palavra] = registro
                    totais["palavras"] += 1

                if modulo.numero == 2:
                    for palavra, _, ordem in dados_modulo["palavras"]:
                        Palavra.objects.filter(pk=palavras_modulo[palavra].pk).update(ordem=ordem)

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
                    comparacao.ordem = ordem
                    comparacao.full_clean()
                    comparacao.save()
                    totais["comparacoes"] += 1

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
