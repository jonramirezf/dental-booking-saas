from django.urls import path
from agenda import views

urlpatterns = [
    path('<slug:slug>/', views.perfil_publico, name='perfil_publico'),
    path('api/<slug:slug>/dias/', views.dias_del_mes, name='dias_del_mes'),
    path('api/<slug:slug>/horarios/', views.horarios_disponibles, name='horarios_disponibles'),
    path('api/<slug:slug>/reservar/', views.crear_reserva, name='crear_reserva'),
    path('cancelar/<uuid:token>/', views.cancelar_reserva, name='cancelar_reserva'),
]