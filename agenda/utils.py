# ============================================================
# ARCHIVO 3/8 — agenda/utils.py
# UBICACIÓN: agenda/utils.py   REEMPLAZAR COMPLETO
# FIX: horarios pasados en el día actual (zona horaria Chile)
# ============================================================
import calendar
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from .models import ConfiguracionAgenda, Reserva, BloqueHorario

TZ_CHILE = ZoneInfo('America/Santiago')


def ahora_chile():
    """Retorna datetime aware en zona horaria de Chile."""
    return datetime.now(TZ_CHILE)


def generar_horarios(dentista, fecha):
    """
    Retorna lista de objetos time con todos los slots del día.
    Si la fecha es hoy (hora Chile), filtra los slots que ya pasaron
    + deja un margen de 30 min (no permite reservar dentro de 30 min).
    """
    dia_semana = fecha.weekday()

    try:
        config = ConfiguracionAgenda.objects.get(
            dentista=dentista, dia_semana=dia_semana
        )
    except ConfiguracionAgenda.DoesNotExist:
        return []

    horarios = []
    hora_actual = datetime.combine(fecha, config.hora_inicio)
    hora_fin    = datetime.combine(fecha, config.hora_fin)

    while hora_actual < hora_fin:
        horarios.append(hora_actual.time())
        hora_actual += timedelta(minutes=config.duracion_cita)

    # --- FIX: filtrar slots pasados si es hoy ---
    hoy_chile = ahora_chile().date()
    if fecha == hoy_chile:
        # tiempo mínimo = ahora + 30 minutos de margen
        minimo = (ahora_chile() + timedelta(minutes=30)).time().replace(second=0, microsecond=0)
        horarios = [h for h in horarios if h >= minimo]

    return horarios


def get_dias_disponibles_mes(dentista, anio, mes):
    """
    Retorna dict {dia_int: estado_str} para todos los días del mes.
    Estados: 'pasado' | 'sin_horario' | 'bloqueado' | 'lleno' | 'disponible'
    """
    hoy = ahora_chile().date()
    _, dias_en_mes = calendar.monthrange(anio, mes)

    dias_config = set(
        ConfiguracionAgenda.objects.filter(dentista=dentista)
        .values_list('dia_semana', flat=True)
    )

    dias_bloqueados = set(
        BloqueHorario.objects.filter(
            dentista=dentista,
            fecha__year=anio,
            fecha__month=mes,
            hora_inicio__isnull=True,
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

        # generar_horarios ya filtra horas pasadas para hoy
        total_slots = len(generar_horarios(dentista, fecha))
        slots_ocupados = Reserva.objects.filter(
            dentista=dentista,
            fecha=fecha,
            estado__in=['pendiente', 'confirmada'],
        ).count()

        if total_slots == 0:
            resultado[dia] = 'sin_horario'
        elif slots_ocupados >= total_slots:
            resultado[dia] = 'lleno'
        else:
            resultado[dia] = 'disponible'

    return resultado
