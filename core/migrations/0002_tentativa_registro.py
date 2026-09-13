import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrar_registros(apps, schema_editor):
    Tentativa = apps.get_model("core", "Tentativa")
    for tentativa in Tentativa.objects.using(schema_editor.connection.alias).select_related("sessao").iterator():
        tentativa.usuario_id = tentativa.sessao.usuario_id
        tentativa.resultado = "correto" if tentativa.acertou else "incorreto"
        tentativa.save(using=schema_editor.connection.alias, update_fields=["usuario", "resultado"])


def restaurar_acertos(apps, schema_editor):
    Tentativa = apps.get_model("core", "Tentativa")
    registros = Tentativa.objects.using(schema_editor.connection.alias)
    registros.update(acertou=False)
    registros.filter(resultado="correto").update(acertou=True)


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.RenameField(model_name="tentativa", old_name="resposta", new_name="resposta_reconhecida"),
        migrations.RenameField(model_name="tentativa", old_name="criada_em", new_name="data_hora"),
        migrations.AlterModelOptions(name="tentativa", options={"ordering": ["-data_hora", "-pk"]}),
        migrations.AddField(
            model_name="tentativa", name="usuario",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="tentativas", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="tentativa", name="resultado",
            field=models.CharField(choices=[("correto", "Correto"), ("incorreto", "Incorreto"), ("nao_reconhecido", "Não reconhecido")], default="nao_reconhecido", max_length=15),
        ),
        migrations.AddField(model_name="tentativa", name="pontuacao", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="tentativa", name="feedback", field=models.TextField(blank=True)),
        migrations.RunPython(migrar_registros, restaurar_acertos),
        migrations.AlterField(
            model_name="tentativa", name="usuario",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tentativas", to=settings.AUTH_USER_MODEL),
        ),
        migrations.RemoveField(model_name="tentativa", name="acertou"),
        migrations.AlterField(
            model_name="tentativa", name="sessao",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="tentativas", to="core.sessao"),
        ),
        migrations.AddConstraint(
            model_name="tentativa",
            constraint=models.CheckConstraint(condition=models.Q(resultado__in=["correto", "incorreto", "nao_reconhecido"]), name="tentativa_resultado_valido"),
        ),
    ]
