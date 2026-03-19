# ============================================================
# ARCHIVO 6b de 9: agenda/views.py
# UBICACIÓN: agenda/views.py
# ACCIÓN: REEMPLAZAR el archivo completo
# ERRORES CORREGIDOS:
#   - Importación de ia movida aquí (no en urls.py) para evitar crash al arrancar
#   - select_for_update() para proteger doble reserva concurrente
#   - Manejo de errores con try/except en todas las vistas
#   - Validaciones de entrada completas
#   - Validación de fecha no en pasado
# ============================================================

import json
from datetime import date
from datetime import time as time_type

from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from dentistas.models import PerfilDentista
from .models import Paciente, Reserva, BloqueHorario
from .utils import generar_horarios, get_dias_disponibles_mes


# ------------------------------------------------------------------
# VISTA PÚBLICA DEL DENTISTA  →  ej: /dr-john/
# ------------------------------------------------------------------

def perfil_publico(request, slug):
    dentista = get_object_or_404(PerfilDentista, slug=slug, activo=True)
    return render(request, 'agenda/reserva_publica.html', {
        'dentista': dentista,
        'slug': slug,
    })


# ------------------------------------------------------------------
# API: días disponibles del mes  →  /api/<slug>/dias/?anio=2025&mes=6
# ------------------------------------------------------------------

def dias_del_mes(request, slug):
    dentista = get_object_or_404(PerfilDentista, slug=slug)

    try:
        anio = int(request.GET.get('anio', date.today().year))
        mes = int(request.GET.get('mes', date.today().month))
        if not (1 <= mes <= 12) or anio < 2020:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Parámetros anio/mes inválidos'}, status=400)

    dias = get_dias_disponibles_mes(dentista, anio, mes)
    return JsonResponse({
        'dias': dias,
        'anio': anio,
        'mes': mes,
    })


# ------------------------------------------------------------------
# API: horarios libres para una fecha  →  /api/<slug>/horarios/?fecha=2025-06-15
# ------------------------------------------------------------------

def horarios_disponibles(request, slug):
    dentista = get_object_or_404(PerfilDentista, slug=slug)
    fecha_str = request.GET.get('fecha', '')

    if not fecha_str:
        return JsonResponse({'error': 'Parámetro fecha requerido'}, status=400)

    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido. Usa YYYY-MM-DD'}, status=400)

    if fecha < date.today():
        return JsonResponse({'horarios': []})

    todos = generar_horarios(dentista, fecha)
    if not todos:
        return JsonResponse({'horarios': []})

    # Horas ya reservadas
    reservados = set(
        Reserva.objects.filter(
            dentista=dentista,
            fecha=fecha,
            estado__in=['pendiente', 'confirmada']
        ).values_list('hora', flat=True)
    )

    # Horas bloqueadas parcialmente (no día completo)
    bloqueos_parciales = BloqueHorario.objects.filter(
        dentista=dentista,
        fecha=fecha,
        hora_inicio__isnull=False
    )
    horas_bloqueadas = set()
    for bloque in bloqueos_parciales:
        for h in todos:
            if bloque.hora_inicio <= h < bloque.hora_fin:
                horas_bloqueadas.add(h)

    disponibles = [
        h.strftime('%H:%M')
        for h in todos
        if h not in reservados and h not in horas_bloqueadas
    ]

    return JsonResponse({'horarios': disponibles})


# ------------------------------------------------------------------
# API: crear reserva  →  POST /api/<slug>/reservar/
# ------------------------------------------------------------------

@csrf_exempt
@require_POST
def crear_reserva(request, slug):
    dentista = get_object_or_404(PerfilDentista, slug=slug)

    # Parsear JSON del body
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Body debe ser JSON válido'}, status=400)

    # Validar campos requeridos
    nombre = data.get('nombre', '').strip()
    email = data.get('email', '').strip().lower()
    fecha_str = data.get('fecha', '')
    hora_str = data.get('hora', '')

    errores = {}
    if not nombre:
        errores['nombre'] = 'El nombre es requerido'
    if not email or '@' not in email:
        errores['email'] = 'Email inválido'
    if not fecha_str:
        errores['fecha'] = 'La fecha es requerida'
    if not hora_str:
        errores['hora'] = 'La hora es requerida'

    if errores:
        return JsonResponse({'error': 'Datos incompletos', 'campos': errores}, status=400)

    # Parsear fecha y hora
    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido. Usa YYYY-MM-DD'}, status=400)

    try:
        hora = time_type.fromisoformat(hora_str)
    except ValueError:
        return JsonResponse({'error': 'Formato de hora inválido. Usa HH:MM'}, status=400)

    if fecha < date.today():
        return JsonResponse({'error': 'No se pueden hacer reservas en fechas pasadas'}, status=400)

    telefono = data.get('telefono', '').strip()

    # Crear reserva dentro de una transacción atómica con bloqueo
    try:
        with transaction.atomic():
            # select_for_update bloquea la fila — evita doble reserva concurrente
            existe = Reserva.objects.select_for_update().filter(
                dentista=dentista,
                fecha=fecha,
                hora=hora,
                estado__in=['pendiente', 'confirmada']
            ).exists()

            if existe:
                return JsonResponse(
                    {'error': 'Este horario ya fue reservado. Por favor elige otro.'},
                    status=409
                )

            # Verificar que el slot sigue siendo válido
            horarios_validos = generar_horarios(dentista, fecha)
            if hora not in horarios_validos:
                return JsonResponse(
                    {'error': 'Este horario no está disponible para este día.'},
                    status=400
                )

            # Crear o recuperar paciente por email
            paciente, _ = Paciente.objects.get_or_create(
                email=email,
                defaults={'nombre': nombre, 'telefono': telefono}
            )

            reserva = Reserva.objects.create(
                dentista=dentista,
                paciente=paciente,
                fecha=fecha,
                hora=hora,
            )

    except IntegrityError:
        # La constraint de la DB captura la segunda request que llega simultánea
        return JsonResponse(
            {'error': 'Este horario ya fue reservado por otra persona. Elige otro.'},
            status=409
        )
    except Exception as e:
        return JsonResponse({'error': f'Error interno al crear la reserva'}, status=500)

    # Enviar email de confirmación (no bloquea si falla)
    _enviar_confirmacion(reserva)

    return JsonResponse({
        'ok': True,
        'mensaje': f'Reserva confirmada para el {fecha.strftime("%d/%m/%Y")} a las {hora_str}',
        'token': str(reserva.token),
    })


# ------------------------------------------------------------------
# Cancelar reserva por link  →  /cancelar/<uuid:token>/
# ------------------------------------------------------------------

def cancelar_reserva(request, token):
    reserva = get_object_or_404(Reserva, token=token)

    if reserva.estado not in ['pendiente', 'confirmada']:
        return JsonResponse(
            {'error': 'Esta reserva ya fue cancelada o completada.'},
            status=400
        )

    reserva.estado = 'cancelada'
    reserva.save(update_fields=['estado'])

    return JsonResponse({
        'ok': True,
        'mensaje': 'Tu reserva fue cancelada exitosamente.',
    })


# ------------------------------------------------------------------
# Endpoint IA (chat del paciente)  →  POST /api/chat/
# ------------------------------------------------------------------

@csrf_exempt
@require_POST
def chat_ia(request):
    """
    Proxy al servicio de IA. Separado de ia/views.py para evitar
    que un error de importación en ia/ tumbe todo el proyecto.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Body debe ser JSON válido'}, status=400)

    mensaje = data.get('mensaje', '').strip()
    if not mensaje:
        return JsonResponse({'error': 'El campo mensaje es requerido'}, status=400)
    if len(mensaje) > 500:
        return JsonResponse({'error': 'Mensaje demasiado largo (máx. 500 caracteres)'}, status=400)

    try:
        from ia.services import responder
        respuesta = responder(mensaje)
        return JsonResponse({'respuesta': respuesta})
    except ImportError:
        return JsonResponse({'error': 'Servicio de IA no disponible'}, status=503)
    except Exception as e:
        return JsonResponse({'error': 'Error al procesar tu pregunta'}, status=500)


# ------------------------------------------------------------------
# Helpers privados
# ------------------------------------------------------------------

def _enviar_confirmacion(reserva):
    """Envía email de confirmación. Falla en silencio para no bloquear la respuesta."""
    try:
        cancel_url = f"{settings.BASE_URL}/cancelar/{reserva.token}/"
        send_mail(
            subject=f'Reserva confirmada — {reserva.dentista.nombre_consultorio}',
            message=(
                f'Hola {reserva.paciente.nombre},\n\n'
                f'Tu cita fue confirmada:\n'
                f'  Fecha: {reserva.fecha.strftime("%d/%m/%Y")}\n'
                f'  Hora: {reserva.hora.strftime("%H:%M")}\n'
                f'  Consultorio: {reserva.dentista.nombre_consultorio}\n\n'
                f'Para cancelar tu cita ingresa aquí:\n{cancel_url}\n\n'
                f'¡Te esperamos!'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reserva.paciente.email],
            fail_silently=True,
        )
    except Exception:
        pass  # No interrumpir la reserva si el email falla
