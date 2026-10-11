from django.db import migrations


def alinhar_modulo(apps, schema_editor):
    apps.get_model('core', 'Modulo').objects.using(schema_editor.connection.alias).filter(numero=2).update(
        titulo='Magic E — o efeito do E final',
        descricao='Descubra como o E final silencioso pode mudar o som da vogal anterior.',
        conteudo_teorico='O E no final fica silencioso e pode mudar o som da vogal anterior. Compare bit e bite, can e cane, pin e pine, sit e site. Nestes exemplos, o E modifica o som do I ou do A. Ouça cada par e perceba a diferença!',
    )


class Migration(migrations.Migration):
    dependencies = [('core', '0009_usuario_apresentacao_vista_em')]
    operations = [migrations.RunPython(alinhar_modulo, migrations.RunPython.noop)]
