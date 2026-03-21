# ============================================================
# agenda/migrations/0004_reserva_recordatorio_2h.py — CREAR
# ============================================================
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # Ajusta al número real de tu última migración
        ('agenda', '0003_alter_bloquehorario_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reserva',
            name='recordatorio_2h_enviado',
            field=models.BooleanField(default=False),
        ),
    ]
