# 🦷 Dental Booking SaaS

Aplicación web de gestión de reservas para profesionales y clínicas dentales desarrollada con **Python y Django**.

Dental Booking SaaS permite que cada dentista gestione su agenda, pacientes y reservas desde un panel privado, mientras dispone de una página pública personalizada donde sus pacientes pueden consultar disponibilidad y reservar una cita.

Además del desarrollo funcional de la aplicación, el proyecto se utiliza como laboratorio práctico para aplicar conceptos de **seguridad de aplicaciones, administración de dependencias, automatización y prácticas DevOps**.

---

## 🎯 Objetivo del proyecto

El objetivo es construir una aplicación SaaS funcional y evolucionarla progresivamente hacia una arquitectura más cercana a un entorno real de producción.

El proyecto trabaja sobre tres áreas principales:

```text
Aplicación funcional
        +
Seguridad
        +
DevOps
```

Esto significa que no solo se desarrollan funcionalidades.

También se revisan aspectos como:

- seguridad de endpoints;
- gestión de secretos;
- dependencias vulnerables;
- integridad de datos;
- automatización;
- testing;
- despliegue;
- CI/CD;
- observabilidad.

---

# ✨ Funcionalidades

## 👨‍⚕️ Gestión de dentistas

Cada profesional dispone de su propio perfil dentro de la plataforma.

Incluye:

- registro e inicio de sesión;
- panel privado;
- perfil independiente;
- URL pública mediante slug;
- nombre del consultorio;
- dirección;
- teléfono;
- descripción;
- foto de perfil;
- imagen de fondo;
- selección de colores;
- diferentes temas visuales;
- activación o desactivación del perfil.

Ejemplo:

```text
/dra-maria-lopez/
/clinica-dental-norte/
```

---

## 📅 Gestión de agenda

Cada dentista puede configurar su propia disponibilidad.

El sistema permite:

- seleccionar días de atención;
- configurar hora de inicio;
- configurar hora de término;
- definir duración de cada cita;
- generar horarios automáticamente;
- bloquear días completos;
- bloquear rangos de horas;
- gestionar vacaciones;
- gestionar feriados;
- gestionar ausencias;
- evitar horarios pasados;
- aplicar un margen mínimo para reservas del mismo día.

La aplicación utiliza:

```text
America/Santiago
```

como zona horaria principal.

---

## 🗓️ Sistema de reservas

El paciente puede reservar directamente desde la página pública del dentista.

Flujo:

```text
Paciente
   │
   ▼
Página pública
   │
   ▼
Selecciona fecha
   │
   ▼
Consulta horarios disponibles
   │
   ▼
Selecciona horario
   │
   ▼
Ingresa sus datos
   │
   ▼
Confirma reserva
   │
   ▼
Reserva almacenada
```

Cada reserva contiene:

- dentista;
- paciente;
- fecha;
- hora;
- estado;
- token UUID;
- fecha de creación.

Estados soportados:

```text
pendiente
confirmada
cancelada
completada
```

---

# 🔒 Integridad de reservas

Uno de los objetivos técnicos del proyecto es evitar inconsistencias y dobles reservas.

Antes de crear una cita se comprueba:

- que la fecha sea válida;
- que no corresponda a una fecha pasada;
- que el horario pertenezca a la agenda;
- que el horario no esté bloqueado;
- que no exista otra reserva activa.

La creación utiliza transacciones:

```python
transaction.atomic()
```

Además existe una restricción a nivel de base de datos mediante:

```python
UniqueConstraint
```

para impedir que un mismo dentista tenga dos reservas activas en la misma fecha y hora.

Arquitectura simplificada:

```text
Solicitud de reserva
        │
        ▼
Validar fecha y horario
        │
        ▼
Consultar disponibilidad
        │
        ▼
¿Horario ocupado?
     ┌──┴──┐
     │     │
    Sí     No
     │     │
     ▼     ▼
 Rechazar Crear
             │
             ▼
      Constraint de BD
```

Esto agrega protección tanto en la aplicación como en la base de datos.

---

# 👥 Gestión de pacientes

Los pacientes se encuentran asociados al dentista correspondiente.

Esto permite mantener separados los datos entre diferentes profesionales.

Cada paciente almacena:

- nombre;
- correo electrónico;
- teléfono;
- dentista asociado;
- fecha de creación.

Un mismo email puede pertenecer a pacientes de diferentes dentistas sin mezclar información entre cuentas.

---

# 📊 Dashboard

El dentista dispone de un panel privado con información de su agenda.

Incluye:

- reservas del día;
- próximas citas;
- reservas pendientes;
- cantidad de citas semanales;
- reservas canceladas;
- estadísticas mensuales;
- vista semanal;
- calendario mensual.

---

# 🔎 Gestión de reservas

Las reservas pueden filtrarse por:

```text
Hoy
Próximas
Semana
Pasadas
Canceladas
Todas
```

También existe búsqueda por nombre del paciente.

Cada dentista solo puede consultar información relacionada con su propio perfil.

---

# 📧 Notificaciones por correo

La aplicación incorpora soporte para correos electrónicos mediante Django.

Al crear una reserva se puede enviar:

### Paciente

- confirmación;
- fecha;
- hora;
- consultorio;
- dirección;
- enlace de gestión/cancelación.

### Dentista

- nombre del paciente;
- email;
- teléfono;
- fecha;
- hora;
- enlace al panel.

En desarrollo se utiliza por defecto:

```text
django.core.mail.backends.console.EmailBackend
```

Las credenciales SMTP se reciben mediante variables de entorno.

No se almacenan credenciales reales dentro del repositorio.

---

# 🔑 Gestión de cancelaciones

Cada reserva genera un token UUID único.

Ejemplo:

```text
/cancelar/550e8400-e29b-41d4-a716-446655440000/
```

El UUID permite identificar una reserva sin exponer IDs incrementales.

Como parte del proceso de hardening de seguridad se está mejorando el flujo para separar correctamente:

```text
GET
│
└──► consultar / mostrar confirmación

POST
│
└──► modificar estado de la reserva
```

Esto evita que crawlers, previsualizadores de correo o solicitudes automáticas puedan modificar accidentalmente el estado de una reserva simplemente visitando un enlace.

---

# ⏰ Recordatorios

El proyecto incluye un Django Management Command:

```bash
python manage.py enviar_recordatorios
```

que busca reservas correspondientes al día siguiente.

Flujo:

```text
Buscar reservas de mañana
          │
          ▼
¿Reserva activa?
          │
          ▼
¿Recordatorio enviado?
      ┌───┴───┐
      │       │
     Sí       No
      │       │
      ▼       ▼
 Ignorar    Enviar
                │
                ▼
       Marcar como enviado
```

Este comando puede ejecutarse posteriormente mediante:

- cron;
- systemd timers;
- Render Cron Jobs;
- Celery;
- otros schedulers.

La automatización periódica todavía debe configurarse externamente.

---

# 🤖 Asistente de consultas

La aplicación incluye un asistente básico para preguntas frecuentes relacionadas con:

- horarios;
- reservas;
- cancelaciones;
- precios;
- tratamientos;
- urgencias;
- convenios.

Actualmente el flujo principal utiliza respuestas locales basadas en reglas.

Por lo tanto, la aplicación puede funcionar sin depender de una API externa.

El repositorio también contiene un módulo experimental:

```text
ia/services.py
```

preparado para realizar consultas a un modelo externo utilizando:

```text
OPENAI_API_KEY
```

Esta integración todavía no forma parte del flujo principal.

---

# 🎨 Personalización

Cada dentista puede personalizar su página pública.

Opciones actuales:

- foto de perfil;
- imagen de fondo;
- color principal;
- nombre del consultorio;
- descripción;
- dirección;
- teléfono;
- tema visual.

Temas disponibles:

```text
Minimalista
Verde
Azul
Coral
Kawaii
Oscuro
Personalizado
```

---

# 🛡️ Seguridad y DevSecOps

Una parte importante del proyecto es mejorar progresivamente la seguridad de la aplicación.

## Gestión de secretos

La aplicación obtiene valores sensibles mediante variables de entorno:

```text
SECRET_KEY
EMAIL_HOST_PASSWORD
OPENAI_API_KEY
```

Por ejemplo:

```python
SECRET_KEY = os.environ.get("SECRET_KEY")
```

Las credenciales no deben almacenarse directamente en el código.

---

## Configuración segura de Django

Actualmente:

```text
SECRET_KEY      → variable de entorno
DEBUG           → variable de entorno
ALLOWED_HOSTS   → variable de entorno
.env            → ignorado por Git
db.sqlite3      → ignorado por Git
```

---

## Auditoría de dependencias

Las dependencias del proyecto fueron actualizadas y auditadas utilizando:

```bash
python -m pip_audit -r requirements.txt
```

Último resultado:

```text
No known vulnerabilities found
```

También se ejecutó:

```bash
python manage.py check
```

con resultado:

```text
System check identified no issues (0 silenced).
```

---

## Hardening progresivo

El proyecto está siendo revisado para mejorar aspectos como:

- solicitudes que modifican estado;
- protección CSRF;
- validación de archivos;
- autenticación;
- rate limiting;
- dependencias;
- seguridad de cookies;
- HTTPS;
- gestión de proxies;
- configuración de producción.

La idea es tratar estas mejoras como parte del ciclo normal de mantenimiento de una aplicación.

---

# 🧰 Stack tecnológico

## Backend

```text
Python
Django 5.2 LTS
Django ORM
```

## Frontend

```text
HTML
CSS
JavaScript
Django Templates
```

## Base de datos

Actualmente:

```text
SQLite
```

para desarrollo local.

PostgreSQL forma parte del siguiente paso para entornos de producción.

---

## Application Server

```text
Gunicorn
```

---

## Seguridad

```text
Django Authentication
CSRF
UUID
Environment Variables
pip-audit
Database Constraints
```

---

# 🏗️ Arquitectura

```text
                          Paciente
                             │
                             ▼
                    Página pública /slug/
                             │
             ┌───────────────┼───────────────┐
             │               │               │
             ▼               ▼               ▼
          Fechas          Horarios        Reserva
             │               │               │
             └───────────────┴───────┬───────┘
                                     │
                                     ▼
                               Django Backend
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
          ▼                          ▼                          ▼
      Pacientes                   Reservas                    Agenda
          │                          │                          │
          └──────────────────────────┼──────────────────────────┘
                                     │
                                     ▼
                              Base de datos
                                     │
                         ┌───────────┴───────────┐
                         │                       │
                         ▼                       ▼
                Panel del dentista        Notificaciones
                                              Email
```

---

# 📁 Estructura

```text
dental-booking-saas/
│
├── agenda/
│   │
│   ├── management/
│   │   └── commands/
│   │       └── enviar_recordatorios.py
│   │
│   ├── migrations/
│   ├── static/
│   ├── templates/
│   ├── templatetags/
│   ├── models.py
│   ├── utils.py
│   └── views.py
│
├── dentistas/
│   ├── migrations/
│   ├── templates/
│   ├── models.py
│   ├── urls.py
│   └── views.py
│
├── ia/
│   ├── services.py
│   └── views.py
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── templates/
│   └── emails/
│
├── build.sh
├── Procfile
├── manage.py
├── requirements.txt
└── README.md
```

---

# 🚀 Instalación local

## Clonar repositorio

```bash
git clone https://github.com/jonramirezf/dental-booking-saas.git
cd dental-booking-saas
```

---

## Crear entorno virtual

```bash
python3 -m venv .venv
```

Activar:

```bash
source .venv/bin/activate
```

---

## Instalar dependencias

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## Configurar SECRET_KEY

Para desarrollo:

```bash
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
```

---

## Ejecutar migraciones

```bash
python manage.py migrate
```

---

## Verificar aplicación

```bash
python manage.py check
```

---

## Ejecutar servidor

```bash
python manage.py runserver
```

---

# 🔐 Variables de entorno

Ejemplo:

```bash
SECRET_KEY=
DEBUG=False

ALLOWED_HOSTS=localhost,127.0.0.1
BASE_URL=http://localhost:8000

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=

OPENAI_API_KEY=
```

Nunca se deben almacenar claves reales en el repositorio.

---

# 🧪 Validación

## Django

```bash
python manage.py check
```

Resultado actual:

```text
System check identified no issues (0 silenced).
```

---

## Dependencias

Instalar:

```bash
python -m pip install pip-audit
```

Ejecutar:

```bash
python -m pip_audit -r requirements.txt
```

Resultado actual:

```text
No known vulnerabilities found
```

---

## Tests

Actualmente el proyecto todavía no cuenta con una suite completa de tests automatizados.

La incorporación de tests forma parte del roadmap.

---

# 📦 Preparación para despliegue

El repositorio incluye:

```text
build.sh
Procfile
```

`build.sh` ejecuta:

```bash
pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate
```

El `Procfile` utiliza Gunicorn:

```text
web: gunicorn config.wsgi:application --workers 2 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT
```

Estos archivos proporcionan una base para el despliegue.

La configuración completa de producción todavía se encuentra en desarrollo.

---

# 🔄 Flujo de mejora

El proyecto sigue un enfoque incremental:

```text
Identificar problema
        │
        ▼
Implementar cambio
        │
        ▼
Probar localmente
        │
        ▼
Validar Django
        │
        ▼
Auditar
        │
        ▼
Git diff
        │
        ▼
Commit
        │
        ▼
Push
```

Este enfoque permite trabajar sobre la aplicación de forma similar a un ciclo real de mantenimiento.

---

# 🗺️ Roadmap

## Seguridad

- finalizar hardening del flujo de cancelación;
- eliminar excepciones CSRF innecesarias;
- validar contenido real de imágenes;
- aplicar todos los password validators de Django;
- rate limiting en login;
- rate limiting persistente;
- secure cookies;
- HTTPS;
- security headers.

## Testing

- unit tests;
- integration tests;
- tests de autorización;
- tests de reservas;
- tests de concurrencia;
- tests de seguridad.

## Base de datos

- PostgreSQL;
- configuración mediante `DATABASE_URL`.

## DevOps

- Docker;
- Docker Compose;
- GitHub Actions;
- Dependabot;
- `pip-audit` automático;
- CI/CD;
- gestión de secretos.

## Observabilidad

- logging estructurado;
- health checks;
- métricas;
- Prometheus;
- Grafana;
- OpenTelemetry.

---

# 🚧 Estado del proyecto

Actualmente:

```text
✅ Sistema de reservas funcional
✅ Gestión multi-dentista
✅ Panel privado
✅ Gestión de pacientes
✅ Agenda configurable
✅ Calendario
✅ Disponibilidad dinámica
✅ Prevención de doble reserva
✅ Notificaciones por email
✅ Recordatorios mediante Management Command
✅ Personalización de perfiles
✅ Variables de entorno
✅ Auditoría de dependencias
✅ Django system checks

🔄 Hardening de seguridad
🔄 Testing automatizado
🔄 PostgreSQL
🔄 CI/CD
🔄 Docker
🔄 Observabilidad
```

> El proyecto se encuentra en desarrollo y no se presenta todavía como una plataforma lista para gestionar información clínica real en producción.

---

# 💼 Enfoque de portafolio

Dental Booking SaaS también funciona como laboratorio práctico para desarrollar experiencia en:

```text
Backend
+
Linux
+
Git / GitHub
+
Security
+
DevOps
+
Automation
+
CI/CD
+
Containers
+
Cloud
+
Observability
```

El objetivo no es solamente desarrollar funcionalidades.

Cada iteración busca incluir:

```text
Implementación
+
Validación
+
Seguridad
+
Documentación
+
Versionado
```

---

## Autor

**Jonathan Ramirez**

Proyecto desarrollado como parte de un portafolio técnico orientado a **Cloud, DevOps y seguridad de aplicaciones**.
