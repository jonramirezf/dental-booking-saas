from django.contrib.auth.models import User
from django.db import models


class PerfilDentista(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    slug = models.SlugField(unique=True)
    nombre_consultorio = models.CharField(max_length=120)
    telefono = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.usuario.username
