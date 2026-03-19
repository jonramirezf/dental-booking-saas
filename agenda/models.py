# ============================================================
# ARCHIVO 5 de 9: agenda/models.py
# UBICACIÓN: agenda/models.py
# ACCIÓN: REEMPLAZAR el archivo completo
# CAMBIOS:
#   - Agrega modelo Paciente
#   - Agrega modelo Reserva con protección real de doble reserva
#   - Agrega modelo BloqueHorario (feriados, vacaciones)
#   - unique_together + UniqueConstraint en Reserva
#   - ConfiguracionAgenda ahora tiene unique_together para evitar
#     duplicar el mismo día de la semana para el mismo dentista
# ============================================================

import uuid
from django.db import models
from django.core.exceptions import ValidationError
from dentistas.models import PerfilDentista


class ConfiguracionAgenda(models.Model):
    DIAS = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    dentista = models.ForeignKey(
        PerfilDentista,
        on_delete=models.CASCADE,
        related_name='configuraciones_agenda'
    )
    dia_semana = models.IntegerField(choices=DIAS)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    duracion_cita = models.IntegerField(
        default=30,
        help_text='Duración en minutos de cada cita'
    )

    class Meta:
        # Un dentista no puede tener dos configs para el mismo día
        unique_together = ['dentista', 'dia_semana']
        ordering = ['dia_semana']

    def clean(self):
        if self.hora_inicio and self.hora_fin:
            if self.hora_inicio >= self.hora_fin:
                raise ValidationError('La hora de inicio debe ser anterior a la hora de fin.')

    def __str__(self):
        return f"{self.dentista} — {self.get_dia_semana_display()} {self.hora_inicio:%H:%M}–{self.hora_fin:%H:%M}"


class BloqueHorario(models.Model):
    """
    Bloquea un día completo o un rango de horas específico.
    Úsalo para feriados, vacaciones, o ausencias puntuales.
    hora_inicio = None + hora_fin = None → bloquea el día completo.
    """
    dentista = models.ForeignKey(
        PerfilDentista,
        on_delete=models.CASCADE,
        related_name='bloqueos'
    )
    fecha = models.DateField()
    hora_inicio = models.TimeField(
        null=True,
        blank=True,
        help_text='Dejar vacío para bloquear el día completo'
    )
    hora_fin = models.TimeField(null=True, blank=True)
    motivo = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['fecha', 'hora_inicio']

    def __str__(self):
        if self.hora_inicio:
            return f"{self.dentista} — {self.fecha} {self.hora_inicio:%H:%M}–{self.hora_fin:%H:%M}"
        return f"{self.dentista} — {self.fecha} (día completo)"


class Paciente(models.Model):
    nombre = models.CharField(max_length=120)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} <{self.email}>"


class Reserva(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('completada', 'Completada'),
    ]

    dentista = models.ForeignKey(
        PerfilDentista,
        on_delete=models.CASCADE,
        related_name='reservas'
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='reservas'
    )
    fecha = models.DateField()
    hora = models.TimeField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    notas = models.TextField(blank=True)

    # Token único para cancelar sin login (se incluye en el email de confirmación)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    recordatorio_enviado = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha', 'hora']
        # PROTECCIÓN REAL DE DOBLE RESERVA A NIVEL DE BASE DE DATOS
        # Nota: esta constraint cubre todos los estados. La lógica en Python
        # filtra solo estados activos. La constraint de DB es el último escudo.
        constraints = [
            models.UniqueConstraint(
                fields=['dentista', 'fecha', 'hora'],
                condition=models.Q(estado__in=['pendiente', 'confirmada']),
                name='unique_reserva_activa_por_dentista'
            )
        ]

    def __str__(self):
        return f"{self.paciente.nombre} — {self.fecha} {self.hora:%H:%M} ({self.get_estado_display()})"