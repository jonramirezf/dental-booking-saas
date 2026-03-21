# ============================================================
# ARCHIVO 8/8 — dentistas/views.py
# UBICACIÓN: dentistas/views.py   REEMPLAZAR COMPLETO
# NUEVO: perfil_view incluye tema_fondo + imagen_fondo
# ============================================================
import json
import re
from datetime import date, timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from agenda.models import ConfiguracionAgenda, Reserva
from .models import PerfilDentista, TEMAS_FONDO


def get_dentista(request):
    try:
        return request.user.perfildentista
    except PerfilDentista.DoesNotExist:
        return None


def dentista_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('dentistas:login')
        if not get_dentista(request):
            return redirect('dentistas:login')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ── AUTH ─────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated and get_dentista(request):
        return redirect('dentistas:dashboard')
    error = None
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
        except User.DoesNotExist:
            user = None
        if user:
            login(request, user)
            return redirect('dentistas:dashboard')
        error = 'Email o contraseña incorrectos.'
    return render(request, 'dentistas/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('dentistas:login')


def registro_view(request):
    if request.user.is_authenticated:
        return redirect('dentistas:dashboard')
    errores = {}
    datos   = {}
    if request.method == 'POST':
        nombre      = request.POST.get('nombre', '').strip()
        email       = request.POST.get('email', '').strip().lower()
        password    = request.POST.get('password', '')
        password2   = request.POST.get('password2', '')
        consultorio = request.POST.get('consultorio', '').strip()
        slug        = request.POST.get('slug', '').strip().lower()
        datos       = {'nombre': nombre, 'email': email,
                       'consultorio': consultorio, 'slug': slug}

        if not nombre:              errores['nombre'] = 'Requerido.'
        if not email or '@' not in email: errores['email'] = 'Email inválido.'
        elif User.objects.filter(email=email).exists(): errores['email'] = 'Email ya registrado.'
        if len(password) < 8:       errores['password'] = 'Mínimo 8 caracteres.'
        if password != password2:   errores['password2'] = 'Las contraseñas no coinciden.'
        if not consultorio:         errores['consultorio'] = 'Requerido.'
        if not slug:                errores['slug'] = 'Requerido.'
        elif not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', slug):
            errores['slug'] = 'Solo letras, números y guiones. Ej: dr-perez'
        elif PerfilDentista.objects.filter(slug=slug).exists():
            errores['slug'] = 'Slug ya en uso.'

        if not errores:
            user = User.objects.create_user(
                username=slug, email=email,
                password=password, first_name=nombre,
            )
            PerfilDentista.objects.create(
                usuario=user, slug=slug, nombre_consultorio=consultorio,
            )
            login(request, user)
            return redirect('dentistas:dashboard')

    return render(request, 'dentistas/registro.html', {'errores': errores, 'datos': datos})


# ── DASHBOARD ────────────────────────────────────────────────

@dentista_required
def dashboard(request):
    dentista = get_dentista(request)
    hoy      = date.today()
    manana   = hoy + timedelta(days=1)

    reservas_hoy    = Reserva.objects.filter(
        dentista=dentista, fecha=hoy,
        estado__in=['pendiente','confirmada']
    ).select_related('paciente').order_by('hora')

    reservas_manana = Reserva.objects.filter(
        dentista=dentista, fecha=manana,
        estado__in=['pendiente','confirmada']
    ).select_related('paciente').order_by('hora')

    total_mes = Reserva.objects.filter(
        dentista=dentista,
        fecha__year=hoy.year, fecha__month=hoy.month,
        estado__in=['pendiente','confirmada','completada']
    ).count()

    pendientes = Reserva.objects.filter(dentista=dentista, estado='pendiente').count()

    return render(request, 'dentistas/dashboard.html', {
        'dentista': dentista,
        'reservas_hoy': reservas_hoy,
        'reservas_manana': reservas_manana,
        'total_mes': total_mes,
        'pendientes': pendientes,
        'hoy': hoy,
        'manana': manana,
    })


# ── RESERVAS ────────────────────────────────────────────────

@dentista_required
def reservas_view(request):
    dentista = get_dentista(request)
    filtro   = request.GET.get('estado', 'activas')
    busqueda = request.GET.get('q', '').strip()

    qs = Reserva.objects.filter(dentista=dentista).select_related('paciente')
    if filtro == 'activas':
        qs = qs.filter(estado__in=['pendiente','confirmada'], fecha__gte=date.today())
    elif filtro == 'pasadas':
        qs = qs.filter(fecha__lt=date.today()).exclude(estado='cancelada')
    elif filtro == 'canceladas':
        qs = qs.filter(estado='cancelada')
    if busqueda:
        qs = qs.filter(paciente__nombre__icontains=busqueda)

    return render(request, 'dentistas/reservas.html', {
        'dentista': dentista,
        'reservas': qs.order_by('fecha', 'hora'),
        'filtro':   filtro,
        'busqueda': busqueda,
    })


# ── AGENDA ──────────────────────────────────────────────────

@dentista_required
def agenda_view(request):
    dentista = get_dentista(request)
    configs  = ConfiguracionAgenda.objects.filter(dentista=dentista).order_by('dia_semana')
    DIAS     = [(0,'Lunes'),(1,'Martes'),(2,'Miércoles'),
                (3,'Jueves'),(4,'Viernes'),(5,'Sábado'),(6,'Domingo')]
    return render(request, 'dentistas/agenda.html', {
        'dentista': dentista,
        'configs':  configs,
        'DIAS':     DIAS,
        'dias_configurados': {c.dia_semana: c for c in configs},
    })


# ── PERFIL ──────────────────────────────────────────────────

@dentista_required
def perfil_view(request):
    dentista = get_dentista(request)
    ok = False

    if request.method == 'POST':
        dentista.nombre_consultorio = request.POST.get('consultorio', dentista.nombre_consultorio).strip()
        dentista.telefono           = request.POST.get('telefono', '').strip()
        dentista.descripcion        = request.POST.get('descripcion', '').strip()
        dentista.direccion          = request.POST.get('direccion', '').strip()

        color = request.POST.get('color', dentista.color_principal).strip()
        if re.match(r'^#[0-9A-Fa-f]{6}$', color):
            dentista.color_principal = color

        tema = request.POST.get('tema_fondo', dentista.tema_fondo)
        if tema in dict(TEMAS_FONDO):
            dentista.tema_fondo = tema

        if 'foto_perfil' in request.FILES:
            dentista.foto_perfil = request.FILES['foto_perfil']
        if 'imagen_fondo' in request.FILES:
            dentista.imagen_fondo = request.FILES['imagen_fondo']

        dentista.save()
        ok = True

    return render(request, 'dentistas/perfil.html', {
        'dentista':    dentista,
        'ok':          ok,
        'TEMAS_FONDO': TEMAS_FONDO,
    })


# ── APIs JSON ────────────────────────────────────────────────

@dentista_required
@require_POST
def api_guardar_agenda(request):
    dentista = get_dentista(request)
    try:
        data         = json.loads(request.body)
        dia_semana   = int(data['dia_semana'])
        hora_inicio  = data['hora_inicio']
        hora_fin     = data['hora_fin']
        duracion     = int(data.get('duracion', 30))
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Datos inválidos'}, status=400)

    if hora_inicio >= hora_fin:
        return JsonResponse({'error': 'Inicio debe ser antes que fin'}, status=400)
    if duracion not in [15, 20, 30, 45, 60]:
        return JsonResponse({'error': 'Duración inválida'}, status=400)

    ConfiguracionAgenda.objects.update_or_create(
        dentista=dentista, dia_semana=dia_semana,
        defaults={'hora_inicio': hora_inicio, 'hora_fin': hora_fin, 'duracion_cita': duracion}
    )
    return JsonResponse({'ok': True})


@dentista_required
@require_POST
def api_eliminar_agenda(request):
    dentista = get_dentista(request)
    try:
        data = json.loads(request.body)
        ConfiguracionAgenda.objects.filter(
            dentista=dentista, dia_semana=int(data['dia_semana'])
        ).delete()
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Datos inválidos'}, status=400)
    return JsonResponse({'ok': True})


@dentista_required
@require_POST
def api_cambiar_estado(request):
    dentista = get_dentista(request)
    try:
        data   = json.loads(request.body)
        rid    = int(data['id'])
        nuevo  = data['estado']
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Datos inválidos'}, status=400)

    if nuevo not in ['pendiente','confirmada','cancelada','completada']:
        return JsonResponse({'error': 'Estado inválido'}, status=400)

    reserva = get_object_or_404(Reserva, pk=rid, dentista=dentista)
    reserva.estado = nuevo
    reserva.save(update_fields=['estado'])
    return JsonResponse({'ok': True, 'estado': nuevo})
