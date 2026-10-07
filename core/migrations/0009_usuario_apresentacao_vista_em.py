from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0008_tentativa_desafio_final')]
    operations = [migrations.AddField(
        model_name='usuario', name='apresentacao_vista_em',
        field=models.DateTimeField(blank=True, editable=False, null=True),
    )]
