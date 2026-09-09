from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Agricultor, Tecnico


@admin.register(Tecnico)
class TecnicoAdmin(UserAdmin):
    model = Tecnico
    list_display = ["username", "email", "cpf", "nome_cidade", "is_staff", "is_active"]
    list_filter = ["is_staff", "is_active", "groups"]
    search_fields = ["username", "email", "cpf"]

    fieldsets = UserAdmin.fieldsets + (
        (
            "Informações adicionais",
            {
                "fields": (
                    "cpf",
                    "nome_cidade",
                    "endereco",
                    "nome_bairro",
                    "foto_perfil",
                ),
            },
        ),
    )

@admin.register(Agricultor)
class AgricultorAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "primeiro_acesso",
    )

    @admin.display(description='Nome de Titular')
    def nome_titular(self, object):
        if object.familia:
            return object.familia.nome_titular
        return '-'