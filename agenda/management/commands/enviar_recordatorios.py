# ============================================================
# ARCHIVO EXTRA — agenda/management/commands/enviar_recordatorios.py
# Crea también:
#   agenda/management/__init__.py          (vacío)
#   agenda/management/commands/__init__.py (vacío)
#
# Uso: python manage.py enviar_recordatorios
# Cron (ejecutar a las 9am cada día):
#   0 9 * * * /ruta/venv/bin/python /ruta/manage.py enviar_recordatorios
# ============================================================
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from datetime import date, timedelta
from agenda.models import Reserva


class Command(BaseCommand):
    help = 'Envía recordatorios de citas para mañana'

    def handle(self, *args, **kwargs):
        manana    = date.today() + timedelta(days=1)
        reservas  = Reserva.objects.filter(
            fecha=manana,
            estado__in=['pendiente', 'confirmada'],
            recordatorio_enviado=False
        ).select_related('paciente', 'dentista')

        enviados = 0
        for r in reservas:
            try:
                cancel_url = f"{settings.BASE_URL}/cancelar/{r.token}/"
                send_mail(
                    subject=f'Recordatorio: tu cita es mañana a las {r.hora.strftime("%H:%M")}',
                    message=(
                        f'Hola {r.paciente.nombre},\n\n'
                        f'Te recordamos que mañana tienes una cita:\n'
                        f'  Fecha: {r.fecha.strftime("%d/%m/%Y")}\n'
                        f'  Hora: {r.hora.strftime("%H:%M")}\n'
                        f'  Consultorio: {r.dentista.nombre_consultorio}\n\n'
                        f'Si necesitas cancelar, haz clic aquí:\n{cancel_url}\n\n'
                        f'¡Te esperamos!'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[r.paciente.email],
                    fail_silently=False,
                )
                r.recordatorio_enviado = True
                r.save(update_fields=['recordatorio_enviado'])
                enviados += 1
            except Exception as e:
                self.stderr.write(f'Error enviando a {r.paciente.email}: {e}')

        self.stdout.write(self.style.SUCCESS(f'{enviados} recordatorio(s) enviados para {manana}.'))
