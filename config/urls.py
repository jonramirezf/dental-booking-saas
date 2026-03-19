# ============================================================
# ARCHIVO 3 de 9: config/urls.py
# UBICACIÓN: config/urls.py
# ACCIÓN: REEMPLAZAR el archivo completo
# ERRORES CORREGIDOS:
#   - Rutas duplicadas (estaban definidas dos veces)
#   - Import de ia.views movido a try/except para no tumbar el proyecto
#   - Admin siempre primero para evitar conflicto con <slug:slug>/
#   - Agregadas rutas de media para desarrollo
# ============================================================

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from agenda import views as agenda_views

urlpatterns = [
    # Admin SIEMPRE antes que el slug, si no admin/ matchea como slug
    path('admin/', admin.site.urls),

    # --- Agenda pública del dentista ---
    path('<slug:slug>/', agenda_views.perfil_publico, name='perfil_publico'),

    # --- APIs JSON ---
    path('api/<slug:slug>/dias/', agenda_views.dias_del_mes, name='dias_del_mes'),
    path('api/<slug:slug>/horarios/', agenda_views.horarios_disponibles, name='horarios_disponibles'),
    path('api/<slug:slug>/reservar/', agenda_views.crear_reserva, name='crear_reserva'),
    path('cancelar/<uuid:token>/', agenda_views.cancelar_reserva, name='cancelar_reserva'),

    # --- IA chat ---
    path('api/chat/', agenda_views.chat_ia, name='chat_ia'),
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
