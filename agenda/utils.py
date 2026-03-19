from datetime import datetime, timedelta, date
import calendar
from .models import ConfiguracionAgenda, Reserva, BloqueHorario


def generar_horarios(dentista, fecha):
    dia_semana = fecha.weekday()
    try:
        config = ConfiguracionAgenda.objects.get(dentista=dentista, dia_semana=dia_semana)
    except ConfiguracionAgenda.DoesNotExist:
        return []

    horarios = []
    hora_actual = datetime.combine(fecha, config.hora_inicio)
    hora_fin = datetime.combine(fecha, config.hora_fin)

    while hora_actual < hora_fin:
        horarios.append(hora_actual.time())
        hora_actual += timedelta(minutes=config.duracion_cita)

    return horarios


def get_dias_disponibles_mes(dentista, anio, mes):
    hoy = date.today()
    _, dias_en_mes = calendar.monthrange(anio, mes)

    dias_config = set(
        ConfiguracionAgenda.objects.filter(dentista=dentista)
        .values_list('dia_semana', flat=True)
    )

    bloques_mes = BloqueHorario.objects.filter(
        dentista=dentista,
        fecha__year=anio,
        fecha__month=mes,
        hora_inicio__isnull=True
    ).values_list('fecha__day', flat=True)

    resultado = {}

    for dia in range(1, dias_en_mes + 1):
        fecha = date(anio, mes, dia)

        if fecha < hoy:
            resultado[dia] = 'pasado'
        elif dia in bloques_mes:
            resultado[dia] = 'bloqueado'
        elif fecha.weekday() in dias_config:
            total = len(generar_horarios(dentista, fecha))

            ocupados = Reserva.objects.filter(
                dentista=dentista,
                fecha=fecha,
                estado__in=['pendiente', 'confirmada']
            ).count()

            resultado[dia] = 'disponible' if total > ocupados else 'lleno'
        else:
            resultado[dia] = 'sin_horario'

    return resultado