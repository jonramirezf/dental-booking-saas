from django.contrib import admin
from django.urls import path
from agenda import views
from ia.views import chat

urlpatterns = [
    path('admin/', admin.site.urls),

    # agenda
    path('<slug:slug>/', views.perfil_publico),
    path('api/<slug:slug>/dias/', views.dias_del_mes),
    path('api/<slug:slug>/horarios/', views.horarios_disponibles),
    path('api/<slug:slug>/reservar/', views.crear_reserva),

    # IA
    path('api/chat/', chat),
]