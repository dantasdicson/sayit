from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone


class Usuario(AbstractUser):
    data_nascimento = models.DateField(null=True, blank=True)


class Modulo(models.Model):
    numero = models.PositiveIntegerField(unique=True)
    titulo = models.CharField(max_length=150)
    descricao = models.TextField()
    conteudo_teorico = models.TextField(blank=True)
    ordem = models.PositiveIntegerField(unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['ordem']

    def __str__(self):
        return f'{self.numero} - {self.titulo}'


class Palavra(models.Model):
    modulo = models.ForeignKey(Modulo, on_delete=models.PROTECT, related_name='palavras')
    palavra = models.CharField(max_length=100)
    traducao = models.CharField(max_length=100)
    imagem = models.ImageField(upload_to='palavras/imagens/', blank=True)
    audio = models.FileField(upload_to='palavras/audios/', blank=True)
    observacao = models.TextField(blank=True)
    ordem = models.PositiveIntegerField()
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ['ordem']
        constraints = [
            models.UniqueConstraint(fields=['modulo', 'palavra'], name='palavra_unica_por_modulo'),
            models.UniqueConstraint(fields=['modulo', 'ordem'], name='ordem_palavra_unica_por_modulo'),
        ]

    def __str__(self):
        return self.palavra


class Comparacao(models.Model):
    modulo = models.ForeignKey(
        Modulo, on_delete=models.CASCADE, related_name='comparacoes'
    )
    palavra_base = models.ForeignKey(
        Palavra, on_delete=models.PROTECT, related_name='comparacoes_como_base'
    )
    palavra_comparada = models.ForeignKey(
        Palavra, on_delete=models.PROTECT, related_name='comparacoes_como_destino'
    )
    explicacao = models.TextField()
    ordem = models.PositiveIntegerField()

    class Meta:
        ordering = ['ordem']
        constraints = [
            models.UniqueConstraint(
                fields=['modulo', 'ordem'],
                name='ordem_comparacao_unica_por_modulo'
            ),
            models.UniqueConstraint(
                fields=['modulo', 'palavra_base', 'palavra_comparada'],
                name='comparacao_unica_por_modulo'
            ),
            models.CheckConstraint(
                condition=~models.Q(
                    palavra_base=models.F('palavra_comparada')
                ),
                name='comparacao_palavras_diferentes'
            ),
        ]

    def clean(self):
        erros = {}

        if self.palavra_base_id and self.modulo_id:
            if self.palavra_base.modulo_id != self.modulo_id:
                erros['palavra_base'] = (
                    'A palavra base deve pertencer ao mesmo módulo da comparação.'
                )

        if self.palavra_comparada_id and self.modulo_id:
            if self.palavra_comparada.modulo_id != self.modulo_id:
                erros['palavra_comparada'] = (
                    'A palavra comparada deve pertencer ao mesmo módulo da comparação.'
                )

        if (
            self.palavra_base_id
            and self.palavra_comparada_id
            and self.palavra_base_id == self.palavra_comparada_id
        ):
            erros['palavra_comparada'] = (
                'A palavra comparada deve ser diferente da palavra base.'
            )

        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f'{self.palavra_base} → {self.palavra_comparada}'


class Progresso(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progressos")
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name="progressos")
    percentual = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["usuario", "modulo"], name="progresso_unico_por_usuario_modulo"),
            models.CheckConstraint(condition=models.Q(percentual__lte=100), name="progresso_percentual_ate_100"),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.modulo}: {self.percentual}%"


class Sessao(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessoes")
    iniciada_em = models.DateTimeField(default=timezone.now)
    finalizada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-iniciada_em", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(finalizada_em__isnull=True) | models.Q(finalizada_em__gte=models.F("iniciada_em")),
                name="sessao_fim_apos_inicio",
            ),
        ]

    def __str__(self):
        return f"Sessão {self.pk} - {self.usuario}"


class Tentativa(models.Model):
    class Resultado(models.TextChoices):
        CORRETO = "correto", "Correto"
        INCORRETO = "incorreto", "Incorreto"
        NAO_RECONHECIDO = "nao_reconhecido", "Não reconhecido"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tentativas")
    sessao = models.ForeignKey(Sessao, on_delete=models.CASCADE, related_name="tentativas", null=True, blank=True)
    palavra = models.ForeignKey(Palavra, on_delete=models.PROTECT, related_name="tentativas")
    resposta_reconhecida = models.CharField(max_length=255, blank=True)
    resultado = models.CharField(max_length=15, choices=Resultado.choices, default=Resultado.NAO_RECONHECIDO)
    pontuacao = models.PositiveIntegerField(default=0)
    feedback = models.TextField(blank=True)
    data_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-data_hora", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(resultado__in=["correto", "incorreto", "nao_reconhecido"]),
                name="tentativa_resultado_valido",
            ),
        ]

    def clean(self):
        super().clean()
        if self.sessao_id and self.usuario_id:
            if not Sessao.objects.filter(pk=self.sessao_id, usuario_id=self.usuario_id).exists():
                raise ValidationError({"sessao": "A sessão deve pertencer ao usuário da tentativa."})

    def __str__(self):
        return f"{self.palavra} - {self.get_resultado_display()}"
