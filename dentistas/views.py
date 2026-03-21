# ============================================================
# dentistas/views.py — REEMPLAZAR COMPLETO
# Dashboard rediseñado: stats semana, próximas citas, vista semanal
# Reservas: cards con filtros hoy/semana/todas, detalle modal
# ============================================================
import json
import os
import re
import calendar as cal_mod
from datetime import date, timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from agenda.models import ConfiguracionAgenda, Reserva
from .models import PerfilDentista, TEMAS_FONDO


# ── helpers ──────────────────────────────────────────────────

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
    errores, datos = {}, {}
    if request.method == 'POST':
        nombre      = request.POST.get('nombre', '').strip()
        email       = request.POST.get('email', '').strip().lower()
        password    = request.POST.get('password', '')
        password2   = request.POST.get('password2', '')
        consultorio = request.POST.get('consultorio', '').strip()
        slug        = request.POST.get('slug', '').strip().lower()
        datos = {'nombre': nombre, 'email': email, 'consultorio': consultorio, 'slug': slug}

        if not nombre:                           errores['nombre']      = 'Requerido.'
        if not email or '@' not in email:        errores['email']       = 'Email inválido.'
        elif User.objects.filter(email=email).exists(): errores['email'] = 'Email ya registrado.'
        if len(password) < 8:                    errores['password']    = 'Mínimo 8 caracteres.'
        if password != password2:                errores['password2']   = 'No coinciden.'
        if not consultorio:                      errores['consultorio'] = 'Requerido.'
        if not slug:                             errores['slug']        = 'Requerido.'
        elif not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', slug):
            errores['slug'] = 'Solo letras, números y guiones.'
        elif PerfilDentista.objects.filter(slug=slug).exists():
            errores['slug'] = 'Slug ya en uso.'

        if not errores:
            user = User.objects.create_user(
                username=slug, email=email, password=password, first_name=nombre,
            )
            PerfilDentista.objects.create(usuario=user, slug=slug, nombre_consultorio=consultorio)
            login(request, user)
            return redirect('dentistas:dashboard')

    return render(request, 'dentistas/registro.html', {'errores': errores, 'datos': datos})


# ── DASHBOARD ────────────────────────────────────────────────

@dentista_required
def dashboard(request):
    dentista = get_dentista(request)
    hoy      = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())       # lunes
    fin_semana    = inicio_semana + timedelta(days=6)          # domingo

    # ── Estadísticas ──────────────────────────────────────────
    reservas_hoy = Reserva.objects.filter(
        dentista=dentista, fecha=hoy,
        estado__in=['pendiente', 'confirmada']
    ).select_related('paciente').order_by('hora')

    total_semana = Reserva.objects.filter(
        dentista=dentista,
        fecha__range=[inicio_semana, fin_semana],
        estado__in=['pendiente', 'confirmada', 'completada']
    ).count()

    canceladas_semana = Reserva.objects.filter(
        dentista=dentista,
        fecha__range=[inicio_semana, fin_semana],
        estado='cancelada'
    ).count()

    pendientes = Reserva.objects.filter(
        dentista=dentista, estado='pendiente'
    ).count()

    total_mes = Reserva.objects.filter(
        dentista=dentista,
        fecha__year=hoy.year, fecha__month=hoy.month,
        estado__in=['pendiente', 'confirmada', 'completada']
    ).count()

    # ── Próximas 5 reservas futuras (desde mañana) ───────────
    proximas = Reserva.objects.filter(
        dentista=dentista,
        fecha__gt=hoy,
        estado__in=['pendiente', 'confirmada']
    ).select_related('paciente').order_by('fecha', 'hora')[:5]

    # ── Vista semanal: dict {fecha: [reservas]} ───────────────
    semana_dias = []
    nombres_dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    reservas_semana_qs = Reserva.objects.filter(
        dentista=dentista,
        fecha__range=[inicio_semana, fin_semana],
        estado__in=['pendiente', 'confirmada']
    ).select_related('paciente').order_by('hora')

    reservas_por_dia = {}
    for r in reservas_semana_qs:
        reservas_por_dia.setdefault(r.fecha, []).append(r)

    for i in range(7):
        d = inicio_semana + timedelta(days=i)
        semana_dias.append({
            'fecha':     d,
            'nombre':    nombres_dias[i],
            'es_hoy':    d == hoy,
            'pasado':    d < hoy,
            'reservas':  reservas_por_dia.get(d, []),
        })

    return render(request, 'dentistas/dashboard.html', {
        'dentista':          dentista,
        'reservas_hoy':      reservas_hoy,
        'total_semana':      total_semana,
        'canceladas_semana': canceladas_semana,
        'pendientes':        pendientes,
        'total_mes':         total_mes,
        'proximas':          proximas,
        'semana_dias':       semana_dias,
        'inicio_semana':     inicio_semana,
        'fin_semana':        fin_semana,
        'hoy':               hoy,
    })


# ── RESERVAS ─────────────────────────────────────────────────

@dentista_required
def reservas_view(request):
    dentista = get_dentista(request)
    filtro   = request.GET.get('filtro', 'proximas')
    busqueda = request.GET.get('q', '').strip()
    hoy      = date.today()

    qs = Reserva.objects.filter(dentista=dentista).select_related('paciente')

    if filtro == 'hoy':
        qs = qs.filter(fecha=hoy)
    elif filtro == 'semana':
        inicio = hoy - timedelta(days=hoy.weekday())
        qs = qs.filter(fecha__range=[inicio, inicio + timedelta(days=6)])
    elif filtro == 'proximas':
        qs = qs.filter(fecha__gte=hoy, estado__in=['pendiente', 'confirmada'])
    elif filtro == 'pasadas':
        qs = qs.filter(fecha__lt=hoy).exclude(estado='cancelada')
    elif filtro == 'canceladas':
        qs = qs.filter(estado='cancelada')
    # 'todas' → sin filtro adicional

    if busqueda:
        qs = qs.filter(paciente__nombre__icontains=busqueda)

    qs = qs.order_by('fecha', 'hora')

    # Contadores para las tabs
    counts = {
        'hoy':       Reserva.objects.filter(dentista=dentista, fecha=hoy).count(),
        'proximas':  Reserva.objects.filter(dentista=dentista, fecha__gte=hoy, estado__in=['pendiente','confirmada']).count(),
        'todas':     Reserva.objects.filter(dentista=dentista).count(),
        'canceladas':Reserva.objects.filter(dentista=dentista, estado='cancelada').count(),
    }

    return render(request, 'dentistas/reservas.html', {
        'dentista': dentista,
        'reservas': qs,
        'filtro':   filtro,
        'busqueda': busqueda,
        'counts':   counts,
        'hoy':      hoy,
    })


# ── CALENDARIO ───────────────────────────────────────────────

@dentista_required
def calendario_view(request):
    """Vista mensual de citas — tipo Google Calendar."""
    import calendar as cal_mod
    from datetime import date, timedelta

    dentista = get_dentista(request)
    hoy      = date.today()

    # Parámetros de mes/año desde la URL
    try:
        anio = int(request.GET.get('anio', hoy.year))
        mes  = int(request.GET.get('mes',  hoy.month))
        if not (1 <= mes <= 12) or anio < 2000:
            raise ValueError
    except (ValueError, TypeError):
        anio, mes = hoy.year, hoy.month

    # Mes anterior y siguiente (robustos)
    if mes == 1:
        mes_anterior  = date(anio - 1, 12, 1)
    else:
        mes_anterior  = date(anio, mes - 1, 1)

    if mes == 12:
        mes_siguiente = date(anio + 1, 1, 1)
    else:
        mes_siguiente = date(anio, mes + 1, 1)

    # Reservas del mes
    reservas_mes = (
        Reserva.objects
        .filter(
            dentista=dentista,
            fecha__year=anio,
            fecha__month=mes,
            estado__in=['pendiente', 'confirmada'],
        )
        .select_related('paciente')
        .order_by('fecha', 'hora')
    )

    # Agrupar reservas por día
    reservas_por_dia = {}
    for r in reservas_mes:
        reservas_por_dia.setdefault(r.fecha.day, []).append(r)

    # Construir grilla de semanas
    _, dias_en_mes = cal_mod.monthrange(anio, mes)
    primer_dia     = date(anio, mes, 1).weekday()  # 0 = lunes

    semanas = []
    semana  = [None] * primer_dia          # celdas vacías hasta el día 1

    for d in range(1, dias_en_mes + 1):
        fecha_celda = date(anio, mes, d)
        semana.append({
            'dia':      d,
            'fecha':    fecha_celda,
            'es_hoy':   fecha_celda == hoy,
            'pasado':   fecha_celda < hoy,
            'reservas': reservas_por_dia.get(d, []),
        })
        if len(semana) == 7:
            semanas.append(semana)
            semana = []

    # Última semana incompleta
    if semana:
        while len(semana) < 7:
            semana.append(None)
        semanas.append(semana)

    MESES = [
        '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]

    # dias_semana lo usaba el template de ChatGPT — lo pasamos por si acaso
    dias_semana = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do']

    return render(request, 'dentistas/calendario.html', {
        'dentista':      dentista,
        'semanas':       semanas,
        'dias_semana':   dias_semana,          # ← este faltaba
        'anio':          anio,
        'mes':           mes,
        'nombre_mes':    MESES[mes],
        'mes_anterior':  mes_anterior,
        'mes_siguiente': mes_siguiente,
        'total_mes':     reservas_mes.count(),
        'hoy':           hoy,
    })
@dentista_required
def calendario_view(request):
    """Vista mensual de citas — tipo Google Calendar."""
    import calendar as cal_mod
    from datetime import date, timedelta

    dentista = get_dentista(request)
    hoy      = date.today()

    # Parámetros de mes/año desde la URL
    try:
        anio = int(request.GET.get('anio', hoy.year))
        mes  = int(request.GET.get('mes',  hoy.month))
        if not (1 <= mes <= 12) or anio < 2000:
            raise ValueError
    except (ValueError, TypeError):
        anio, mes = hoy.year, hoy.month

    # Mes anterior y siguiente (robustos)
    if mes == 1:
        mes_anterior  = date(anio - 1, 12, 1)
    else:
        mes_anterior  = date(anio, mes - 1, 1)

    if mes == 12:
        mes_siguiente = date(anio + 1, 1, 1)
    else:
        mes_siguiente = date(anio, mes + 1, 1)

    # Reservas del mes
    reservas_mes = (
        Reserva.objects
        .filter(
            dentista=dentista,
            fecha__year=anio,
            fecha__month=mes,
            estado__in=['pendiente', 'confirmada'],
        )
        .select_related('paciente')
        .order_by('fecha', 'hora')
    )

    # Agrupar reservas por día
    reservas_por_dia = {}
    for r in reservas_mes:
        reservas_por_dia.setdefault(r.fecha.day, []).append(r)

    # Construir grilla de semanas
    _, dias_en_mes = cal_mod.monthrange(anio, mes)
    primer_dia     = date(anio, mes, 1).weekday()  # 0 = lunes

    semanas = []
    semana  = [None] * primer_dia          # celdas vacías hasta el día 1

    for d in range(1, dias_en_mes + 1):
        fecha_celda = date(anio, mes, d)
        semana.append({
            'dia':      d,
            'fecha':    fecha_celda,
            'es_hoy':   fecha_celda == hoy,
            'pasado':   fecha_celda < hoy,
            'reservas': reservas_por_dia.get(d, []),
        })
        if len(semana) == 7:
            semanas.append(semana)
            semana = []

    # Última semana incompleta
    if semana:
        while len(semana) < 7:
            semana.append(None)
        semanas.append(semana)

    MESES = [
        '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]

    # dias_semana lo usaba el template de ChatGPT — lo pasamos por si acaso
    dias_semana = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do']

    return render(request, 'dentistas/calendario.html', {
        'dentista':      dentista,
        'semanas':       semanas,
        'dias_semana':   dias_semana,          # ← este faltaba
        'anio':          anio,
        'mes':           mes,
        'nombre_mes':    MESES[mes],
        'mes_anterior':  mes_anterior,
        'mes_siguiente': mes_siguiente,
        'total_mes':     reservas_mes.count(),
        'hoy':           hoy,
    })



# ── AGENDA ───────────────────────────────────────────────────

@dentista_required
def agenda_view(request):
    dentista = get_dentista(request)
    configs  = ConfiguracionAgenda.objects.filter(dentista=dentista).order_by('dia_semana')
    DIAS     = [(0,'Lunes'),(1,'Martes'),(2,'Miércoles'),
                (3,'Jueves'),(4,'Viernes'),(5,'Sábado'),(6,'Domingo')]
    return render(request, 'dentistas/agenda.html', {
        'dentista': dentista, 'configs': configs, 'DIAS': DIAS,
        'dias_configurados': {c.dia_semana: c for c in configs},
    })


# ── PERFIL ───────────────────────────────────────────────────

@dentista_required
def perfil_view(request):
    dentista = get_dentista(request)
    ok = False; error = None

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

        # Foto de perfil
        eliminar_foto = request.POST.get('eliminar_foto_perfil') == '1'
        if eliminar_foto and dentista.foto_perfil:
            ruta = dentista.foto_perfil.path
            if os.path.isfile(ruta): os.remove(ruta)
            dentista.foto_perfil = None
        elif 'foto_perfil' in request.FILES:
            archivo = request.FILES['foto_perfil']
            if archivo.size > 5 * 1024 * 1024:
                error = 'La foto no puede superar los 5 MB.'
            elif not archivo.content_type.startswith('image/'):
                error = 'El archivo debe ser una imagen.'
            else:
                if dentista.foto_perfil:
                    ruta_ant = dentista.foto_perfil.path
                    if os.path.isfile(ruta_ant): os.remove(ruta_ant)
                dentista.foto_perfil = archivo

        # Imagen de fondo
        eliminar_fondo = request.POST.get('eliminar_imagen_fondo') == '1'
        if eliminar_fondo and dentista.imagen_fondo:
            ruta = dentista.imagen_fondo.path
            if os.path.isfile(ruta): os.remove(ruta)
            dentista.imagen_fondo = None
        elif 'imagen_fondo' in request.FILES:
            archivo = request.FILES['imagen_fondo']
            if archivo.size > 10 * 1024 * 1024:
                error = 'La imagen de fondo no puede superar los 10 MB.'
            elif not archivo.content_type.startswith('image/'):
                error = 'El archivo debe ser una imagen.'
            else:
                if dentista.imagen_fondo:
                    ruta_ant = dentista.imagen_fondo.path
                    if os.path.isfile(ruta_ant): os.remove(ruta_ant)
                dentista.imagen_fondo = archivo

        if not error:
            dentista.save(); ok = True

    return render(request, 'dentistas/perfil.html', {
        'dentista': dentista, 'ok': ok, 'error': error, 'TEMAS_FONDO': TEMAS_FONDO,
    })


# ── APIs JSON ─────────────────────────────────────────────────

@dentista_required
@require_POST
def api_guardar_agenda(request):
    dentista = get_dentista(request)
    try:
        data = json.loads(request.body)
        dia_semana  = int(data['dia_semana'])
        hora_inicio = data['hora_inicio']
        hora_fin    = data['hora_fin']
        duracion    = int(data.get('duracion', 30))
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
        data  = json.loads(request.body)
        rid   = int(data['id'])
        nuevo = data['estado']
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Datos inválidos'}, status=400)
    if nuevo not in ['pendiente', 'confirmada', 'cancelada', 'completada']:
        return JsonResponse({'error': 'Estado inválido'}, status=400)
    reserva = get_object_or_404(Reserva, pk=rid, dentista=dentista)
    reserva.estado = nuevo
    reserva.save(update_fields=['estado'])
    return JsonResponse({'ok': True, 'estado': nuevo})
