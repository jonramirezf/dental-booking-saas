# ============================================================
# ARCHIVO 6a de 9: agenda/utils.py
# UBICACIÓN: agenda/utils.py
# ACCIÓN: REEMPLAZAR el archivo completo
# ============================================================

import calendar
from datetime import datetime, timedelta, date
from .models import ConfiguracionAgenda, Reserva, BloqueHorario


def generar_horarios(dentista, fecha):
    """
    Retorna lista de objetos time con todos los slots del día,
    según la ConfiguracionAgenda del dentista para ese día de la semana.
    Retorna [] si no hay configuración para ese día.
    """
    dia_semana = fecha.weekday()

    try:
        config = ConfiguracionAgenda.objects.get(
            dentista=dentista,
            dia_semana=dia_semana
        )
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
    """
    Retorna dict {dia_int: estado_str} para todos los días del mes.
    Estados posibles:
        'pasado'      → anterior a hoy
        'sin_horario' → el dentista no trabaja ese día de la semana
        'bloqueado'   → bloqueado manualmente (feriado, vacación)
        'lleno'       → tiene horarios pero todos están ocupados
        'disponible'  → tiene al menos un slot libre
    """
    hoy = date.today()
    _, dias_en_mes = calendar.monthrange(anio, mes)

    # Días de la semana que el dentista tiene configurados
    dias_config = set(
        ConfiguracionAgenda.objects.filter(dentista=dentista)
        .values_list('dia_semana', flat=True)
    )

    # Días del mes bloqueados completamente (hora_inicio es null)
    dias_bloqueados = set(
        BloqueHorario.objects.filter(
            dentista=dentista,
            fecha__year=anio,
            fecha__month=mes,
            hora_inicio__isnull=True
        ).values_list('fecha__day', flat=True)
    )

    resultado = {}
    for dia in range(1, dias_en_mes + 1):
        fecha = date(anio, mes, dia)

        if fecha < hoy:
            resultado[dia] = 'pasado'
            continue

        if dia in dias_bloqueados:
            resultado[dia] = 'bloqueado'
            continue

        if fecha.weekday() not in dias_config:
            resultado[dia] = 'sin_horario'
            continue

        # Verificar si quedan slots libres
        total_slots = len(generar_horarios(dentista, fecha))
        slots_ocupados = Reserva.objects.filter(
            dentista=dentista,
            fecha=fecha,
            estado__in=['pendiente', 'confirmada']
        ).count()

        if total_slots == 0:
            resultado[dia] = 'sin_horario'
        elif slots_ocupados >= total_slots:
            resultado[dia] = 'lleno'
        else:
            resultado[dia] = 'disponible'

    return resultado
