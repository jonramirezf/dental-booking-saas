# Dental Booking SaaS

Aplicación web de gestión de reservas para clínicas y profesionales dentales desarrollada con Django.

El proyecto permite que cada dentista gestione su agenda y disponga de una página pública donde los pacientes pueden consultar horarios disponibles y reservar una cita.

## Funcionalidades

- Registro e inicio de sesión para dentistas
- Panel de administración con resumen de reservas
- Gestión de horarios de atención
- Calendario de citas
- Página pública personalizada por dentista
- Reserva de horas según disponibilidad
- Bloqueo de días, vacaciones y horarios
- Prevención de reservas duplicadas
- Gestión de pacientes
- Estados de reserva: pendiente, confirmada, cancelada y completada
- Cancelación mediante enlace único
- Confirmación de reservas por correo electrónico
- Recordatorios automáticos de citas
- Personalización de colores, imágenes y datos del consultorio
- Asistente básico para consultas frecuentes de pacientes

## Tecnologías

- Python
- Django
- HTML
- CSS
- JavaScript
- SQLite para desarrollo
- PostgreSQL preparado para producción
- Gunicorn
- WhiteNoise

## Estructura principal

```text
dental-booking-saas/
├── agenda/          # Reservas, pacientes, horarios y disponibilidad
├── dentistas/       # Usuarios, perfiles y panel del dentista
├── ia/              # Integración experimental con asistentes
├── config/          # Configuración principal de Django
├── templates/       # Plantillas y correos
├── manage.py
├── requirements.txt
├── build.sh
└── Procfile
