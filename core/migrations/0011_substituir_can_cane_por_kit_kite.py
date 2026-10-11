from django.db import migrations


def corrigir_modulo(apps, schema_editor):
    alias = schema_editor.connection.alias
    Modulo = apps.get_model('core', 'Modulo')
    Palavra = apps.get_model('core', 'Palavra')
    Comparacao = apps.get_model('core', 'Comparacao')
    modulos = Modulo.objects.using(alias).filter(numero=2)
    for modulo in modulos:
        palavras = Palavra.objects.using(alias).filter(modulo_id=modulo.pk)
        for antiga, nova, traducao in [('can', 'kit', 'conjunto'), ('cane', 'kite', 'pipa')]:
            if not palavras.filter(palavra=nova).exists():
                palavras.filter(palavra=antiga).update(
                    palavra=nova, traducao=traducao,
                    imagem=f'palavras/imagens/{nova}.webp', audio=f'palavras/audios/{nova}.mp3',
                )
        Comparacao.objects.using(alias).filter(modulo_id=modulo.pk, ordem=2).update(
            explicacao='Compare kit e kite: o E final de kite é silencioso e muda o som do I. Escute a diferença entre as duas palavras.'
        )
    modulos.update(
        titulo='Magic E: mudança do som do I',
        descricao='Aprenda como o E final silencioso pode modificar a pronúncia da vogal I.',
        conteudo_teorico='O E final fica silencioso e pode mudar o som do I. Compare bit e bite, kit e kite, pin e pine, sit e site. Nessas palavras, o I passa a soar como o nome da letra I em inglês. Ouça cada par e perceba a diferença!',
    )


class Migration(migrations.Migration):
    dependencies = [('core', '0010_alinhar_modulo_2_magic_e')]
    operations = [migrations.RunPython(corrigir_modulo, migrations.RunPython.noop)]
