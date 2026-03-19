# ============================================================
# ARCHIVO 1/7 — dentistas/urls.py
# UBICACIÓN:   dentistas/urls.py   (archivo NUEVO)
# ============================================================
from django.urls import path
from . import views

app_name = 'dentistas'

urlpatterns = [
    # Auth
    path('login/',    views.login_view,    name='login'),
    path('logout/',   views.logout_view,   name='logout'),
    path('registro/', views.registro_view, name='registro'),

    # Panel principal
    path('panel/',              views.dashboard,         name='dashboard'),
    path('panel/reservas/',     views.reservas_view,     name='reservas'),
    path('panel/agenda/',       views.agenda_view,       name='agenda'),
    path('panel/perfil/',       views.perfil_view,       name='perfil'),

    # API JSON — agenda
    path('panel/api/agenda/guardar/',  views.api_guardar_agenda,  name='api_guardar_agenda'),
    path('panel/api/agenda/eliminar/', views.api_eliminar_agenda, name='api_eliminar_agenda'),

    # API JSON — reservas
    path('panel/api/reserva/estado/', views.api_cambiar_estado,  name='api_cambiar_estado'),
]
