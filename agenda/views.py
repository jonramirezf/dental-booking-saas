# ============================================================
# ARCHIVO 4/8 — agenda/views.py
# UBICACIÓN: agenda/views.py   REEMPLAZAR COMPLETO
# NUEVO: emails HTML reales, timezone Chile, mejor manejo errores
# ============================================================
import json
from datetime import date
from datetime import time as time_type

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from dentistas.models import PerfilDentista
from .models import BloqueHorario, Paciente, Reserva
from .utils import ahora_chile, generar_horarios, get_dias_disponibles_mes


# ── PÁGINA PÚBLICA ───────────────────────────────────────────

def perfil_publico(request, slug):
    dentista = get_object_or_404(PerfilDentista, slug=slug, activo=True)
    vars_tema = dentista.tema_vars()
    return render(request, 'agenda/reserva_publica.html', {
        'dentista':   dentista,
        'slug':       slug,
        'vars_tema':  vars_tema,
        'imagen_fondo': dentista.imagen_fondo.url if dentista.imagen_fondo else None,
    })


# ── API: DÍAS DEL MES ────────────────────────────────────────

def dias_del_mes(request, slug):
    dentista = get_object_or_404(PerfilDentista, slug=slug)
    try:
        anio = int(request.GET.get('anio', date.today().year))
        mes  = int(request.GET.get('mes',  date.today().month))
        if not (1 <= mes <= 12) or anio < 2020:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Parámetros inválidos'}, status=400)

    dias = get_dias_disponibles_mes(dentista, anio, mes)
    return JsonResponse({'dias': dias, 'anio': anio, 'mes': mes})


# ── API: HORARIOS DISPONIBLES ────────────────────────────────

def horarios_disponibles(request, slug):
    dentista = get_object_or_404(PerfilDentista, slug=slug)
    fecha_str = request.GET.get('fecha', '')

    if not fecha_str:
        return JsonResponse({'error': 'Parámetro fecha requerido'}, status=400)

    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        return JsonResponse({'error': 'Formato inválido. Usa YYYY-MM-DD'}, status=400)

    hoy_chile = ahora_chile().date()
    if fecha < hoy_chile:
        return JsonResponse({'horarios': []})

    todos = generar_horarios(dentista, fecha)   # ya filtra horas pasadas
    if not todos:
        return JsonResponse({'horarios': []})

    reservados = set(
        Reserva.objects.filter(
            dentista=dentista,
            fecha=fecha,
            estado__in=['pendiente', 'confirmada'],
        ).values_list('hora', flat=True)
    )

    bloqueos = BloqueHorario.objects.filter(
        dentista=dentista, fecha=fecha, hora_inicio__isnull=False
    )
    horas_bloqueadas = set()
    for b in bloqueos:
        for h in todos:
            if b.hora_inicio <= h < b.hora_fin:
                horas_bloqueadas.add(h)

    disponibles = [
        h.strftime('%H:%M')
        for h in todos
        if h not in reservados and h not in horas_bloqueadas
    ]
    return JsonResponse({'horarios': disponibles})


# ── API: CREAR RESERVA ───────────────────────────────────────

@csrf_exempt
@require_POST
def crear_reserva(request, slug):
    dentista = get_object_or_404(PerfilDentista, slug=slug)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Body debe ser JSON válido'}, status=400)

    nombre    = data.get('nombre', '').strip()
    email     = data.get('email', '').strip().lower()
    fecha_str = data.get('fecha', '')
    hora_str  = data.get('hora', '')
    telefono  = data.get('telefono', '').strip()

    errores = {}
    if not nombre:               errores['nombre'] = 'Requerido'
    if not email or '@' not in email: errores['email'] = 'Email inválido'
    if not fecha_str:            errores['fecha'] = 'Requerido'
    if not hora_str:             errores['hora']  = 'Requerido'

    if errores:
        return JsonResponse({'error': 'Datos incompletos', 'campos': errores}, status=400)

    try:
        fecha = date.fromisoformat(fecha_str)
        hora  = time_type.fromisoformat(hora_str)
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha/hora inválido'}, status=400)

    hoy_chile = ahora_chile().date()
    if fecha < hoy_chile:
        return JsonResponse({'error': 'No se pueden hacer reservas en fechas pasadas'}, status=400)

    try:
        with transaction.atomic():
            existe = Reserva.objects.select_for_update().filter(
                dentista=dentista, fecha=fecha, hora=hora,
                estado__in=['pendiente', 'confirmada'],
            ).exists()

            if existe:
                return JsonResponse(
                    {'error': 'Este horario ya fue reservado. Elige otro.'},
                    status=409,
                )

            horarios_validos = generar_horarios(dentista, fecha)
            if hora not in horarios_validos:
                return JsonResponse(
                    {'error': 'Este horario no está disponible.'},
                    status=400,
                )

            paciente, _ = Paciente.objects.get_or_create(
                email=email,
                defaults={'nombre': nombre, 'telefono': telefono},
            )
            reserva = Reserva.objects.create(
                dentista=dentista,
                paciente=paciente,
                fecha=fecha,
                hora=hora,
            )

    except IntegrityError:
        return JsonResponse(
            {'error': 'Horario ocupado simultáneamente. Elige otro.'},
            status=409,
        )
    except Exception:
        return JsonResponse({'error': 'Error interno. Inténtalo de nuevo.'}, status=500)

    _enviar_confirmacion_paciente(reserva)
    _notificar_dentista(reserva)

    return JsonResponse({
        'ok':     True,
        'mensaje': f'Reserva confirmada para el {fecha.strftime("%d/%m/%Y")} a las {hora_str}',
        'token':  str(reserva.token),
    })


# ── CANCELAR POR LINK ────────────────────────────────────────

def cancelar_reserva(request, token):
    reserva = get_object_or_404(Reserva, token=token)
    if reserva.estado not in ['pendiente', 'confirmada']:
        return JsonResponse({'error': 'Esta reserva no se puede cancelar.'}, status=400)
    reserva.estado = 'cancelada'
    reserva.save(update_fields=['estado'])
    return render(request, 'agenda/cancelacion_ok.html', {'reserva': reserva})


# ── IA CHAT ──────────────────────────────────────────────────

@csrf_exempt
@require_POST
def chat_ia(request):
    try:
        data    = json.loads(request.body)
        mensaje = data.get('mensaje', '').strip()
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    if not mensaje:
        return JsonResponse({'error': 'Mensaje vacío'}, status=400)
    if len(mensaje) > 500:
        return JsonResponse({'error': 'Mensaje demasiado largo'}, status=400)

    try:
        from ia.services import responder
        return JsonResponse({'respuesta': responder(mensaje)})
    except ImportError:
        return JsonResponse({'error': 'Servicio IA no disponible'}, status=503)
    except Exception:
        return JsonResponse({'error': 'Error al procesar la pregunta'}, status=500)


# ── HELPERS DE EMAIL ─────────────────────────────────────────

def _enviar_confirmacion_paciente(reserva):
    """Email HTML al paciente con datos de la cita y link de cancelación."""
    try:
        cancel_url = f"{settings.BASE_URL}/cancelar/{reserva.token}/"
        ctx = {
            'reserva':    reserva,
            'cancel_url': cancel_url,
        }
        html_body = render_to_string('emails/confirmacion_paciente.html', ctx)
        text_body = (
            f"Hola {reserva.paciente.nombre},\n\n"
            f"Tu cita está confirmada:\n"
            f"  Fecha: {reserva.fecha.strftime('%d/%m/%Y')}\n"
            f"  Hora: {reserva.hora.strftime('%H:%M')}\n"
            f"  Consultorio: {reserva.dentista.nombre_consultorio}\n\n"
            f"Para cancelar: {cancel_url}\n\n"
            f"¡Te esperamos!"
        )
        msg = EmailMultiAlternatives(
            subject=f"✅ Reserva confirmada — {reserva.dentista.nombre_consultorio}",
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[reserva.paciente.email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=True)
    except Exception:
        pass


def _notificar_dentista(reserva):
    """Email simple al dentista avisando la nueva reserva."""
    try:
        email_dentista = reserva.dentista.usuario.email
        if not email_dentista:
            return
        text = (
            f"Nueva reserva recibida\n\n"
            f"Paciente: {reserva.paciente.nombre} <{reserva.paciente.email}>\n"
            f"Fecha:    {reserva.fecha.strftime('%d/%m/%Y')}\n"
            f"Hora:     {reserva.hora.strftime('%H:%M')}\n"
            f"Teléfono: {reserva.paciente.telefono or '—'}\n"
        )
        msg = EmailMultiAlternatives(
            subject=f"📅 Nueva cita: {reserva.paciente.nombre} — {reserva.hora.strftime('%H:%M')}",
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email_dentista],
        )
        msg.send(fail_silently=True)
    except Exception:
        pass
