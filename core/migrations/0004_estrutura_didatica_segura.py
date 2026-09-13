from django.db import migrations, models
import django.db.models.deletion


def verificar_dados(apps, schema_editor):
    alias = schema_editor.connection.alias
    Modulo = apps.get_model('core', 'Modulo')
    Palavra = apps.get_model('core', 'Palavra')
    problemas = []
    for model, campos in [(Modulo, ['ordem']), (Palavra, ['modulo_id', 'ordem'])]:
        registros = model.objects.using(alias)
        duplicados = registros.values(*campos).annotate(total=models.Count('pk')).filter(total__gt=1)
        for grupo in duplicados:
            filtro = {campo: grupo[campo] for campo in campos}
            ids = list(registros.filter(**filtro).values_list('pk', flat=True))
            problemas.append(f'{model.__name__}: {filtro}, IDs {ids}')
    for pk, traducao in Palavra.objects.using(alias).values_list('pk', 'traducao').iterator():
        if len(traducao) > 100:
            problemas.append(f'Palavra ID {pk}: tradução com mais de 100 caracteres')
    if problemas:
        raise RuntimeError('Corrija os dados antes de migrar. Nenhum conflito foi corrigido automaticamente:\n' + '\n'.join(problemas))


def preencher_numero(apps, schema_editor):
    Modulo = apps.get_model('core', 'Modulo')
    Modulo.objects.using(schema_editor.connection.alias).update(numero=models.F('ordem'))


class Migration(migrations.Migration):
    atomic = True
    dependencies = [('core', '0003_palavra_ativa_palavra_traducao')]

    operations = [
        migrations.RunPython(verificar_dados, migrations.RunPython.noop),
        migrations.RenameField(model_name='modulo', old_name='nome', new_name='titulo'),
        migrations.RemoveConstraint(model_name='palavra', name='palavra_unica_por_modulo'),
        migrations.RenameField(model_name='palavra', old_name='texto', new_name='palavra'),
        migrations.RenameField(model_name='palavra', old_name='dica', new_name='observacao'),
        migrations.AddField(model_name='modulo', name='numero', field=models.PositiveIntegerField(null=True)),
        migrations.AddField(model_name='modulo', name='conteudo_teorico', field=models.TextField(blank=True, default=''), preserve_default=False),
        migrations.AddField(model_name='palavra', name='imagem', field=models.ImageField(blank=True, default='', upload_to='palavras/imagens/'), preserve_default=False),
        migrations.AddField(model_name='palavra', name='audio', field=models.FileField(blank=True, default='', upload_to='palavras/audios/'), preserve_default=False),
        migrations.RunPython(preencher_numero, migrations.RunPython.noop),
        migrations.AlterField(model_name='modulo', name='numero', field=models.PositiveIntegerField(unique=True)),
        migrations.AlterField(model_name='modulo', name='titulo', field=models.CharField(max_length=150)),
        migrations.AlterField(model_name='modulo', name='descricao', field=models.TextField()),
        migrations.AlterField(model_name='modulo', name='ordem', field=models.PositiveIntegerField(unique=True)),
        migrations.AlterField(model_name='palavra', name='traducao', field=models.CharField(max_length=100)),
        migrations.AlterField(model_name='palavra', name='ordem', field=models.PositiveIntegerField()),
        migrations.AlterField(model_name='palavra', name='modulo', field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='palavras', to='core.modulo')),
        migrations.AlterModelOptions(name='modulo', options={'ordering': ['ordem']}),
        migrations.AlterModelOptions(name='palavra', options={'ordering': ['ordem']}),
        migrations.AddConstraint(model_name='palavra', constraint=models.UniqueConstraint(fields=['modulo', 'palavra'], name='palavra_unica_por_modulo')),
        migrations.AddConstraint(model_name='palavra', constraint=models.UniqueConstraint(fields=['modulo', 'ordem'], name='ordem_palavra_unica_por_modulo')),
        migrations.CreateModel(
            name='Comparacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('explicacao', models.TextField()),
                ('ordem', models.PositiveIntegerField()),
                ('modulo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comparacoes', to='core.modulo')),
                ('palavra_base', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='comparacoes_como_base', to='core.palavra')),
                ('palavra_comparada', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='comparacoes_como_destino', to='core.palavra')),
            ],
            options={'ordering': ['ordem']},
        ),
    ]
