# ============================================================
# ARCHIVO 3/7 — config/urls.py
# UBICACIÓN:   config/urls.py   (reemplaza el existente)
# ============================================================
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from agenda import views as agenda_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Panel del dentista
    path('', include('dentistas.urls')),

    # Reservas públicas del paciente
    path('<slug:slug>/', agenda_views.perfil_publico,       name='perfil_publico'),
    path('api/<slug:slug>/dias/',      agenda_views.dias_del_mes,         name='dias_del_mes'),
    path('api/<slug:slug>/horarios/',  agenda_views.horarios_disponibles,  name='horarios_disponibles'),
    path('api/<slug:slug>/reservar/',  agenda_views.crear_reserva,         name='crear_reserva'),
    path('cancelar/<uuid:token>/',     agenda_views.cancelar_reserva,      name='cancelar_reserva'),
    path('api/chat/',                  agenda_views.chat_ia,               name='chat_ia'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
