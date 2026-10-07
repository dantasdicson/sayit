import os
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Cria um administrador inicial por variáveis privadas; nunca redefine uma conta.'

    def handle(self, *args, **options):
        values = [os.getenv(key, '') for key in ['ADMIN_USERNAME', 'ADMIN_EMAIL', 'ADMIN_PASSWORD']]
        if not any(values):
            return
        if not all(values):
            raise CommandError('Informe ADMIN_USERNAME, ADMIN_EMAIL e ADMIN_PASSWORD juntos.')
        username, email, password = values
        user_model = get_user_model()
        if user_model.objects.filter(username=username).exists():
            self.stdout.write('Conta existente preservada; senha não modificada.')
            return
        candidate = user_model(username=username, email=email)
        try:
            validate_password(password, candidate)
            candidate.full_clean(exclude=['password'])
        except ValidationError:
            raise CommandError('Dados do administrador inválidos; confira e-mail, nome e força da senha.') from None
        user_model.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS('Administrador inicial criado. Remova ADMIN_PASSWORD do ambiente.'))
