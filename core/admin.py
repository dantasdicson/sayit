from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Modulo, Palavra, Progresso, Sessao, Tentativa, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Dados pessoais adicionais", {"fields": ("data_nascimento",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Dados pessoais adicionais", {"fields": ("data_nascimento",)}),)


admin.site.register([Modulo, Palavra, Progresso, Sessao, Tentativa])
