# ============================================================
# agenda/views.py — REEMPLAZAR COMPLETO
# NUEVO: email con mensaje inteligente (IA simple sin API externa)
# Rate limiting básico con caché
# ============================================================
import json
from datetime import date
from datetime import time as time_type

from django.conf import settings
from django.core.cache import cache
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
    return render(request, 'agenda/reserva_publica.html', {
        'dentista':     dentista,
        'slug':         slug,
        'vars_tema':    dentista.tema_vars(),
        'imagen_fondo': dentista.imagen_fondo.url if dentista.imagen_fondo else None,
    })


# ── API: DÍAS DEL MES ────────────────────────────────────────

def dias_del_mes(request, slug):
    dentista = get_object_or_404(PerfilDentista, slug=slug)
    try:
        anio = int(request.GET.get('anio', date.today().year))
        mes  = int(request.GET.get('mes',  date.today().month))
        if not (1 <= mes <= 12) or anio < 2024:
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
        return JsonResponse({'error': 'Formato inválido YYYY-MM-DD'}, status=400)

    if fecha < ahora_chile().date():
        return JsonResponse({'horarios': []})

    todos = generar_horarios(dentista, fecha)
    if not todos:
        return JsonResponse({'horarios': []})

    reservados = set(
        Reserva.objects.filter(
            dentista=dentista, fecha=fecha,
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
    # Rate limiting: 5 intentos por IP en 10 minutos
    ip = _get_ip(request)
    rl_key = f'rl_reserva_{ip}'
    intentos = cache.get(rl_key, 0)
    if intentos >= 5:
        return JsonResponse({'error': 'Demasiadas solicitudes. Espera unos minutos.'}, status=429)
    cache.set(rl_key, intentos + 1, timeout=600)

    dentista = get_object_or_404(PerfilDentista, slug=slug)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    nombre   = data.get('nombre', '').strip()[:120]
    email    = data.get('email', '').strip().lower()[:120]
    fecha_str= data.get('fecha', '')
    hora_str = data.get('hora', '')
    telefono = data.get('telefono', '').strip()[:20]

    errores = {}
    if not nombre:                    errores['nombre'] = 'Requerido'
    if not email or '@' not in email: errores['email']  = 'Email inválido'
    if not fecha_str:                 errores['fecha']  = 'Requerido'
    if not hora_str:                  errores['hora']   = 'Requerido'
    if errores:
        return JsonResponse({'error': 'Datos incompletos', 'campos': errores}, status=400)

    try:
        fecha = date.fromisoformat(fecha_str)
        hora  = time_type.fromisoformat(hora_str)
    except ValueError:
        return JsonResponse({'error': 'Formato fecha/hora inválido'}, status=400)

    if fecha < ahora_chile().date():
        return JsonResponse({'error': 'No se reserva en fechas pasadas'}, status=400)

    try:
        with transaction.atomic():
            existe = Reserva.objects.select_for_update().filter(
                dentista=dentista, fecha=fecha, hora=hora,
                estado__in=['pendiente', 'confirmada'],
            ).exists()
            if existe:
                return JsonResponse({'error': 'Horario ya ocupado. Elige otro.'}, status=409)

            if hora not in generar_horarios(dentista, fecha):
                return JsonResponse({'error': 'Horario no disponible.'}, status=400)

            paciente, _ = Paciente.objects.get_or_create(
                email=email,
                defaults={'nombre': nombre, 'telefono': telefono},
            )
            reserva = Reserva.objects.create(
                dentista=dentista, paciente=paciente, fecha=fecha, hora=hora,
            )

    except IntegrityError:
        return JsonResponse({'error': 'Horario ocupado simultáneamente.'}, status=409)
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
    ya_cancelada = reserva.estado not in ['pendiente', 'confirmada']
    if not ya_cancelada:
        reserva.estado = 'cancelada'
        reserva.save(update_fields=['estado'])
    return render(request, 'agenda/cancelacion_ok.html', {
        'reserva': reserva, 'ya_cancelada': ya_cancelada
    })


# ── IA CHAT ──────────────────────────────────────────────────

@csrf_exempt
@require_POST
def chat_ia(request):
    try:
        data    = json.loads(request.body)
        mensaje = data.get('mensaje', '').strip()[:500]
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    if not mensaje:
        return JsonResponse({'error': 'Mensaje vacío'}, status=400)

    # IA simple sin API externa — respuesta inteligente basada en palabras clave
    respuesta = _ia_simple(mensaje)
    return JsonResponse({'respuesta': respuesta})


# ── HELPERS ──────────────────────────────────────────────────

def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '0.0.0.0')


def _ia_simple(mensaje):
    """
    IA simple local — sin API externa.
    Responde preguntas frecuentes de pacientes dentales.
    Reemplaza con OpenAI/Claude cuando estés listo para producción.
    """
    m = mensaje.lower()

    if any(w in m for w in ['hora', 'horario', 'atención', 'atienden', 'disponible']):
        return 'Puedes ver los horarios disponibles directamente en el calendario de esta página. Elige el día y la hora que más te acomode.'

    if any(w in m for w in ['precio', 'costo', 'valor', 'cuánto']):
        return 'Los precios varían según el tratamiento. Te recomendamos reservar una consulta de evaluación y el dentista te informará los costos en detalle.'

    if any(w in m for w in ['cancelar', 'anular', 'cambiar', 'reprogramar']):
        return 'Si necesitas cancelar o cambiar tu cita, puedes hacerlo desde el enlace que te enviamos por correo al hacer la reserva.'

    if any(w in m for w in ['urgencia', 'urgente', 'dolor', 'duele', 'emergencia']):
        return '¡Entendemos que es urgente! Por favor llama directamente al consultorio para atención de emergencias. También puedes reservar una cita para hoy si hay disponibilidad en el calendario.'

    if any(w in m for w in ['seguro', 'fonasa', 'isapre', 'cobertura', 'convenio']):
        return 'Aceptamos varios convenios y seguros. Te recomendamos consultar directamente al hacer tu cita para confirmar la cobertura específica de tu plan.'

    if any(w in m for w in ['hola', 'buenos', 'buenas', 'saludos']):
        return '¡Hola! Bienvenido/a. ¿En qué puedo ayudarte? Puedo informarte sobre horarios, reservas o responder preguntas sobre nuestros servicios.'

    if any(w in m for w in ['gracias', 'muchas gracias', 'perfecto', 'listo']):
        return '¡Con mucho gusto! Si necesitas algo más, aquí estoy. ¡Que tengas un excelente día! 😊'

    if any(w in m for w in ['limpieza', 'blanqueamiento', 'implante', 'ortodoncia', 'bracket']):
        return 'Ofrecemos una amplia variedad de tratamientos dentales. Para más detalles sobre un tratamiento específico, reserva una consulta de evaluación y el dentista te explicará todo.'

    # Respuesta genérica
    return 'Gracias por tu mensaje. Para reservar una cita, usa el calendario de esta página. Si tienes preguntas urgentes, contacta directamente al consultorio. ¡Estamos para ayudarte!'


def _enviar_confirmacion_paciente(reserva):
    """Email HTML al paciente con mensaje personalizado tipo IA."""
    try:
        cancel_url = f"{settings.BASE_URL}/cancelar/{reserva.token}/"
        ctx = {
            'reserva':    reserva,
            'cancel_url': cancel_url,
            'mensaje_ia': _generar_mensaje_confirmacion(reserva),
        }
        html_body = render_to_string('emails/confirmacion_paciente.html', ctx)
        text_body = (
            f"Hola {reserva.paciente.nombre},\n\n"
            f"Tu cita está confirmada:\n"
            f"  Fecha: {reserva.fecha.strftime('%d/%m/%Y')}\n"
            f"  Hora: {reserva.hora.strftime('%H:%M')}\n"
            f"  Consultorio: {reserva.dentista.nombre_consultorio}\n"
            f"  Dirección: {reserva.dentista.direccion or 'Consulta al consultorio'}\n\n"
            f"Para cancelar: {cancel_url}\n\n¡Te esperamos!"
        )
        msg = EmailMultiAlternatives(
            subject=f"✅ Cita confirmada — {reserva.dentista.nombre_consultorio}",
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[reserva.paciente.email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=True)
    except Exception:
        pass


def _generar_mensaje_confirmacion(reserva):
    """
    Genera un mensaje personalizado para el email de confirmación.
    Simula IA sin depender de API externa.
    """
    hora = reserva.hora.hour
    if hora < 12:
        saludo = "¡Buenos días"
        momento = "mañana"
    elif hora < 19:
        saludo = "¡Buenas tardes"
        momento = "en la tarde"
    else:
        saludo = "¡Buenas noches"
        momento = "en la noche"

    nombre_corto = reserva.paciente.nombre.split()[0]

    return (
        f"{saludo}, {nombre_corto}! Tu cita dental ha quedado reservada para "
        f"el {reserva.fecha.strftime('%d/%m/%Y')} a las {reserva.hora.strftime('%H:%M')} "
        f"({momento}). Si tienes alguna duda o necesitas reagendar, "
        f"no dudes en contactarnos. ¡Te esperamos!"
    )


def _notificar_dentista(reserva):
    """Email de notificación al dentista."""
    try:
        email_dentista = reserva.dentista.usuario.email
        if not email_dentista:
            return
        msg = EmailMultiAlternatives(
            subject=f"📅 Nueva reserva: {reserva.paciente.nombre} — {reserva.fecha.strftime('%d/%m/%Y')} {reserva.hora.strftime('%H:%M')}",
            body=(
                f"Nueva reserva recibida en {reserva.dentista.nombre_consultorio}\n\n"
                f"Paciente:  {reserva.paciente.nombre}\n"
                f"Email:     {reserva.paciente.email}\n"
                f"Teléfono:  {reserva.paciente.telefono or '—'}\n"
                f"Fecha:     {reserva.fecha.strftime('%d/%m/%Y')}\n"
                f"Hora:      {reserva.hora.strftime('%H:%M')}\n\n"
                f"Panel: {settings.BASE_URL}/panel/reservas/"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email_dentista],
        )
        msg.send(fail_silently=True)
    except Exception:
        pass
