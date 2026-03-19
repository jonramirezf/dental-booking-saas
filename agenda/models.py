from django.db import models
from django.core.exceptions import ValidationError
from dentistas.models import PerfilDentista
import uuid


class ConfiguracionAgenda(models.Model):
    DIAS = [
        (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'),
        (3, 'Jueves'), (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo'),
    ]
    dentista = models.ForeignKey(PerfilDentista, on_delete=models.CASCADE)
    dia_semana = models.IntegerField(choices=DIAS)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    duracion_cita = models.IntegerField(default=30)

    class Meta:
        unique_together = ['dentista', 'dia_semana']

    def __str__(self):
        return f"{self.dentista} - {self.get_dia_semana_display()}"


class Paciente(models.Model):
    nombre = models.CharField(max_length=120)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.email})"


class BloqueHorario(models.Model):
    """Bloquear días/horarios específicos (feriados, vacaciones, etc.)"""
    dentista = models.ForeignKey(PerfilDentista, on_delete=models.CASCADE)
    fecha = models.DateField()
    hora_inicio = models.TimeField(null=True, blank=True)  # null = día completo
    hora_fin = models.TimeField(null=True, blank=True)
    motivo = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.dentista} - {self.fecha} bloqueado"


class Reserva(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('completada', 'Completada'),
    ]

    dentista = models.ForeignKey(PerfilDentista, on_delete=models.CASCADE)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    fecha = models.DateField()
    hora = models.TimeField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    notas = models.TextField(blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True)  # para cancelar sin login
    recordatorio_enviado = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['dentista', 'fecha', 'hora']  # evita doble reserva
        ordering = ['fecha', 'hora']

    def clean(self):
        # Validar que no exista otra reserva en ese slot
        existe = Reserva.objects.filter(
            dentista=self.dentista,
            fecha=self.fecha,
            hora=self.hora,
            estado__in=['pendiente', 'confirmada']
        ).exclude(pk=self.pk).exists()
        if existe:
            raise ValidationError("Este horario ya está reservado.")

    def __str__(self):
        return f"{self.paciente.nombre} - {self.fecha} {self.hora}"