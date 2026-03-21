# ============================================================
# ARCHIVO 2/8 — dentistas/migrations/0003_tema_imagen_fondo.py
# UBICACIÓN: dentistas/migrations/0003_tema_imagen_fondo.py   CREAR
# ============================================================
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dentistas', '0002_perfildentista_activo_perfildentista_color_principal_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfildentista',
            name='tema_fondo',
            field=models.CharField(
                choices=[
                    ('minimal', 'Minimalista (blanco limpio)'),
                    ('verde', 'Verde salud'),
                    ('azul', 'Azul profesional'),
                    ('coral', 'Coral amigable'),
                    ('kawaii', 'Kawaii (suave pastel)'),
                    ('oscuro', 'Oscuro elegante'),
                    ('personalizado', 'Imagen personalizada'),
                ],
                default='minimal',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='perfildentista',
            name='imagen_fondo',
            field=models.ImageField(
                blank=True,
                help_text='Solo si tema_fondo=personalizado',
                null=True,
                upload_to='fondos/',
            ),
        ),
    ]
