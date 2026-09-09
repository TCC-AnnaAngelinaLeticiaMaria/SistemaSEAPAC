from django.db import models
from django.contrib.auth.models import AbstractUser
from seapac.models import Municipality
import os
from PIL import Image
from django.conf import settings


class Usuario(AbstractUser):
    username = models.CharField(max_length=50, unique=True, null=False)
    email = models.EmailField(blank=False)

    @property
    def is_administrador(self):
        return self.groups.filter(name="ADMINISTRADORES").exists()

    @property
    def is_tecnico(self):
        return self.groups.filter(name="TECNICOS").exists()

    @property
    def is_agricultor(self):
        return self.groups.filter(name="AGRICULTORES").exists()


class Tecnico(Usuario):
    endereco = models.CharField(max_length=255, blank=True, null=True)
    nome_bairro = models.CharField(max_length=100, blank=True, null=True)
    cpf = models.CharField(
        max_length=18, unique=True, null=True, blank=True, verbose_name="CPF"
    )
    foto_perfil = models.ImageField(
        upload_to="perfil/", null=True, blank=True, verbose_name="Foto de Perfil"
    )
    nome_cidade = models.ForeignKey(
        Municipality, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "Tecnico"
        verbose_name_plural = "Tecnicos"

    def has_valid_photo(self):
        if self.foto_perfil and self.foto_perfil.name:
            caminho = os.path.join(settings.MEDIA_ROOT, self.foto_perfil.name)
            return os.path.exists(caminho)
        return False

    def get_photo_url(self):
        if self.has_valid_photo():
            return self.foto_perfil.url
        return None

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.foto_perfil:
            caminho = os.path.join(settings.MEDIA_ROOT, self.foto_perfil.name)

            img = Image.open(caminho)
            tamanho_max = (400, 400)
            img.thumbnail(tamanho_max)
            img.save(caminho)


    def __str__(self):
        return f"{self.username} - {self.cpf}"


class Agricultor(Usuario):
    familia = models.OneToOneField('seapac.Family', on_delete=models.SET_NULL, blank=True, null=True, related_name='agricultor')

    primeiro_acesso = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Agricultor"
        verbose_name_plural = "Agricultores"

    def __str__(self):
        return f"Agricultor - {self.username}"