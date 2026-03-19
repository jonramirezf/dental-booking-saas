from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
import json
from datetime import date

from .models import ConfiguracionAgenda, Reserva, Paciente, BloqueHorario
from .utils import generar_horarios, get_dias_disponibles_mes
from dentistas.models import PerfilDentista


def perfil_publico(request, slug):
    dentista = get_object_or_404(PerfilDentista, slug=slug)
    return render(request, 'agenda/reserva_publica.html', {
        'dentista': dentista,
        'slug': slug,
    })


def horarios_disponibles(request, slug):
    dentista = get_object_or_404(PerfilDentista, slug=slug)
    fecha_str = request.GET.get('fecha')

    if not fecha_str:
        return JsonResponse({'error': 'fecha requerida'}, status=400)

    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        return JsonResponse({'error': 'formato inválido'}, status=400)

    todos = generar_horarios(dentista, fecha)

    reservados = Reserva.objects.filter(
        dentista=dentista,
        fecha=fecha,
        estado__in=['pendiente', 'confirmada']
    ).values_list('hora', flat=True)

    disponibles = [
        h.strftime('%H:%M')
        for h in todos
        if h not in reservados
    ]

    return JsonResponse({'horarios': disponibles})


def dias_del_mes(request, slug):
    dentista = get_object_or_404(PerfilDentista, slug=slug)
    anio = int(request.GET.get('anio', date.today().year))
    mes = int(request.GET.get('mes', date.today().month))

    dias = get_dias_disponibles_mes(dentista, anio, mes)
    return JsonResponse({'dias': dias})


@csrf_exempt
@require_POST
def crear_reserva(request, slug):
    dentista = get_object_or_404(PerfilDentista, slug=slug)

    try:
        data = json.loads(request.body)
        nombre = data['nombre']
        email = data['email']
        fecha = date.fromisoformat(data['fecha'])
        hora = data['hora']
    except Exception:
        return JsonResponse({'error': 'datos inválidos'}, status=400)

    from datetime import time
    hora = time.fromisoformat(hora)

    existe = Reserva.objects.filter(
        dentista=dentista,
        fecha=fecha,
        hora=hora,
        estado__in=['pendiente', 'confirmada']
    ).exists()

    if existe:
        return JsonResponse({'error': 'ocupado'}, status=409)

    paciente, _ = Paciente.objects.get_or_create(
        email=email,
        defaults={'nombre': nombre}
    )

    reserva = Reserva.objects.create(
        dentista=dentista,
        paciente=paciente,
        fecha=fecha,
        hora=hora
    )

    return JsonResponse({'ok': True})


def cancelar_reserva(request, token):
    reserva = get_object_or_404(Reserva, token=token)
    reserva.estado = 'cancelada'
    reserva.save()
    return JsonResponse({'ok': True})