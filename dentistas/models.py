# ============================================================
# ARCHIVO 4 de 9: dentistas/models.py
# UBICACIÓN: dentistas/models.py
# ACCIÓN: REEMPLAZAR el archivo completo
# CAMBIOS:
#   - Agrega campos de personalización visual (color, logo, foto, descripción)
#   - Agrega campo direccion
#   - Mantiene compatibilidad con lo que ya tenías
# ============================================================

from django.contrib.auth.models import User
from django.db import models


class PerfilDentista(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    slug = models.SlugField(unique=True)
    nombre_consultorio = models.CharField(max_length=120)
    telefono = models.CharField(max_length=20, blank=True)

    # --- Personalización visual (diferenciador SaaS) ---
    color_principal = models.CharField(
        max_length=7,
        default='#0F6E56',
        help_text='Color hex, ej: #0F6E56'
    )
    logo = models.ImageField(
        upload_to='logos/',
        blank=True,
        null=True,
        help_text='Logo del consultorio'
    )
    foto_perfil = models.ImageField(
        upload_to='dentistas/',
        blank=True,
        null=True,
        help_text='Foto del dentista'
    )
    descripcion = models.TextField(
        blank=True,
        help_text='Texto que ve el paciente al entrar al perfil'
    )
    direccion = models.CharField(max_length=200, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} — {self.nombre_consultorio}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('perfil_publico', kwargs={'slug': self.slug})
