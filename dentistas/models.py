# ============================================================
# ARCHIVO 1/8 — dentistas/models.py
# UBICACIÓN: dentistas/models.py   REEMPLAZAR COMPLETO
# NUEVO: campo imagen_fondo + tema_fondo (predeterminados)
# ============================================================
from django.contrib.auth.models import User
from django.db import models


TEMAS_FONDO = [
    ('minimal',      'Minimalista (blanco limpio)'),
    ('verde',        'Verde salud'),
    ('azul',         'Azul profesional'),
    ('coral',        'Coral amigable'),
    ('kawaii',       'Kawaii (suave pastel)'),
    ('oscuro',       'Oscuro elegante'),
    ('personalizado','Imagen personalizada'),
]


class PerfilDentista(models.Model):
    usuario             = models.OneToOneField(User, on_delete=models.CASCADE)
    slug                = models.SlugField(unique=True)
    nombre_consultorio  = models.CharField(max_length=120)
    telefono            = models.CharField(max_length=20, blank=True)

    # Personalización visual
    color_principal = models.CharField(max_length=7, default='#0d9e75',
                                       help_text='Color hex, ej: #0d9e75')
    logo            = models.ImageField(upload_to='logos/',     blank=True, null=True)
    foto_perfil     = models.ImageField(upload_to='dentistas/', blank=True, null=True)
    descripcion     = models.TextField(blank=True)
    direccion       = models.CharField(max_length=200, blank=True)
    activo          = models.BooleanField(default=True)

    # NUEVO — fondo página pública
    tema_fondo      = models.CharField(max_length=20, choices=TEMAS_FONDO,
                                       default='minimal')
    imagen_fondo    = models.ImageField(upload_to='fondos/', blank=True, null=True,
                                        help_text='Solo si tema_fondo=personalizado')

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} — {self.nombre_consultorio}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('perfil_publico', kwargs={'slug': self.slug})

    # CSS vars que se inyectan en la página pública del paciente
    TEMAS_CSS = {
        'minimal': {
            'bg':    '#f8fafc',
            'shell': '#ffffff',
            'accent':'#0d9e75',
        },
        'verde': {
            'bg':    '#ecfdf5',
            'shell': '#ffffff',
            'accent':'#059669',
        },
        'azul': {
            'bg':    '#eff6ff',
            'shell': '#ffffff',
            'accent':'#2563eb',
        },
        'coral': {
            'bg':    '#fff1f2',
            'shell': '#ffffff',
            'accent':'#f43f5e',
        },
        'kawaii': {
            'bg':    '#fdf4ff',
            'shell': '#ffffff',
            'accent':'#d946ef',
        },
        'oscuro': {
            'bg':    '#0f172a',
            'shell': '#1e293b',
            'accent':'#38bdf8',
        },
        'personalizado': {
            'bg':    '#f8fafc',
            'shell': '#ffffff',
            'accent':'#0d9e75',
        },
    }

    def tema_vars(self):
        t = self.TEMAS_CSS.get(self.tema_fondo, self.TEMAS_CSS['minimal'])
        # override accent con el color elegido por el dentista
        t = dict(t)
        t['accent'] = self.color_principal
        return t
