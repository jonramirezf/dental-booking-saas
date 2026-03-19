/* =====================================================
   app.js  —  Dental SaaS Booking
   slug se define en el HTML ANTES de cargar este archivo:
   <script>const slug = "{{ slug }}";</script>
   ===================================================== */

const MESES = [
    'Enero','Febrero','Marzo','Abril','Mayo','Junio',
    'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'
];
const MESES_CORTO = [
    'ENE','FEB','MAR','ABR','MAY','JUN',
    'JUL','AGO','SEP','OCT','NOV','DIC'
];
const DIAS_LARGO = ['domingo','lunes','martes','miércoles','jueves','viernes','sábado'];

let mesActual  = new Date().getMonth();
let anioActual = new Date().getFullYear();
let fechaSeleccionada = null;   // "YYYY-MM-DD"
let horaSeleccionada  = null;   // "HH:MM"
let labelFechaActual  = '';     // texto legible

/* ── INIT ── */
document.addEventListener('DOMContentLoaded', () => {
    cargarMes(anioActual, mesActual);
});

/* ── PASO 1: CALENDARIO ── */

function cargarMes(anio, mes) {
    const titulo = document.getElementById('cal-titulo');
    const grid   = document.getElementById('cal-grid');
    titulo.textContent = `${MESES[mes]} ${anio}`;
    grid.innerHTML = '<div class="cal-loading">Cargando…</div>';

    fetch(`/api/${slug}/dias/?anio=${anio}&mes=${mes + 1}`)
        .then(r => { if (!r.ok) throw r.status; return r.json(); })
        .then(data => pintarCalendario(anio, mes, data.dias || {}))
        .catch(() => {
            grid.innerHTML = '<div class="cal-loading" style="color:#ef4444">Error al cargar. Recarga la página.</div>';
        });
}

function pintarCalendario(anio, mes, dias) {
    const grid = document.getElementById('cal-grid');
    const hoy  = new Date();
    const hoyD = hoy.getDate();
    const hoyM = hoy.getMonth();
    const hoyA = hoy.getFullYear();

    grid.innerHTML = '';

    /* offset: lunes=0 */
    let primerDia = new Date(anio, mes, 1).getDay();
    primerDia = primerDia === 0 ? 6 : primerDia - 1;

    for (let i = 0; i < primerDia; i++) {
        const v = document.createElement('div');
        v.className = 'cal-day empty';
        grid.appendChild(v);
    }

    const total = new Date(anio, mes + 1, 0).getDate();

    for (let d = 1; d <= total; d++) {
        const estado = dias[d] || 'sin_horario';
        const el = document.createElement('button');
        el.className = `cal-day ${estado}`;
        el.textContent = d;
        el.type = 'button';

        const esHoy = (d === hoyD && mes === hoyM && anio === hoyA);
        if (esHoy) el.classList.add('hoy');

        if (estado === 'disponible') {
            el.onclick = () => seleccionarDia(d, anio, mes, el);
        } else {
            el.disabled = true;
        }

        /* marcar si ya estaba seleccionado */
        const mesStr = (mes + 1).toString().padStart(2,'0');
        const dStr   = d.toString().padStart(2,'0');
        if (fechaSeleccionada === `${anio}-${mesStr}-${dStr}`) {
            el.classList.add('selected');
        }

        grid.appendChild(el);
    }
}

function cambiarMes(dir) {
    const hoy = new Date();
    let nuevoMes  = mesActual + dir;
    let nuevoAnio = anioActual;

    if (nuevoMes > 11) { nuevoMes = 0;  nuevoAnio++; }
    if (nuevoMes < 0)  { nuevoMes = 11; nuevoAnio--; }

    /* no retroceder a meses pasados */
    if (nuevoAnio < hoy.getFullYear() ||
        (nuevoAnio === hoy.getFullYear() && nuevoMes < hoy.getMonth())) return;

    mesActual  = nuevoMes;
    anioActual = nuevoAnio;
    cargarMes(anioActual, mesActual);
}

function seleccionarDia(dia, anio, mes, el) {
    document.querySelectorAll('.cal-day').forEach(b => b.classList.remove('selected'));
    el.classList.add('selected');

    const mesStr = (mes + 1).toString().padStart(2,'0');
    const dStr   = dia.toString().padStart(2,'0');
    fechaSeleccionada = `${anio}-${mesStr}-${dStr}`;

    const nombreDia = DIAS_LARGO[new Date(anio, mes, dia).getDay()];
    labelFechaActual = `${nombreDia.charAt(0).toUpperCase() + nombreDia.slice(1)}, ${dia} de ${MESES[mes]}`;

    irPaso(2);
    cargarHorarios();
}

/* ── PASO 2: HORARIOS ── */

function cargarHorarios() {
    const label = document.getElementById('label-fecha-horario');
    const grid  = document.getElementById('time-grid');

    label.textContent = labelFechaActual.toUpperCase();
    grid.innerHTML = '<div class="cal-loading">Cargando horarios…</div>';

    fetch(`/api/${slug}/horarios/?fecha=${fechaSeleccionada}`)
        .then(r => { if (!r.ok) throw r.status; return r.json(); })
        .then(data => {
            grid.innerHTML = '';
            const horarios = data.horarios || [];

            if (horarios.length === 0) {
                grid.innerHTML = '<div class="time-empty">No hay horarios disponibles para este día.</div>';
                return;
            }

            horarios.forEach(h => {
                const btn = document.createElement('button');
                btn.className = 'time-btn';
                btn.textContent = h;
                btn.type = 'button';
                btn.onclick = () => seleccionarHora(h, btn);
                grid.appendChild(btn);
            });
        })
        .catch(() => {
            grid.innerHTML = '<div class="time-empty" style="color:#ef4444">Error al cargar horarios.</div>';
        });
}

function seleccionarHora(hora, el) {
    document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('selected'));
    el.classList.add('selected');
    horaSeleccionada = hora;

    const dt = document.getElementById('summary-datetime');
    dt.textContent = `${labelFechaActual} · ${hora}`;

    setTimeout(() => irPaso(3), 160);
}

/* ── PASO 3: FORMULARIO ── */

function confirmarReserva() {
    const nombre = document.getElementById('f-nombre').value.trim();
    const email  = document.getElementById('f-email').value.trim();
    const tel    = document.getElementById('f-tel').value.trim();
    const errEl  = document.getElementById('field-error');
    const btn    = document.getElementById('btn-confirmar');

    /* limpiar errores */
    errEl.classList.add('hidden');
    document.getElementById('f-nombre').classList.remove('error');
    document.getElementById('f-email').classList.remove('error');

    let error = '';
    if (!nombre) {
        document.getElementById('f-nombre').classList.add('error');
        error = 'El nombre es requerido.';
    }
    if (!email || !email.includes('@')) {
        document.getElementById('f-email').classList.add('error');
        error = error || 'Ingresa un correo válido.';
    }
    if (error) { mostrarError(error); return; }

    btn.disabled = true;
    btn.textContent = 'Confirmando…';

    fetch(`/api/${slug}/reservar/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            nombre,
            email,
            telefono: tel,
            fecha: fechaSeleccionada,
            hora:  horaSeleccionada,
        })
    })
    .then(r => r.json().then(data => ({ status: r.status, data })))
    .then(({ status, data }) => {
        btn.disabled = false;
        btn.textContent = 'Confirmar reserva';

        if (data.ok) {
            document.getElementById('confirm-detail').textContent = data.mensaje || '';
            irPaso(4);
        } else if (status === 409) {
            mostrarError('Este horario ya fue tomado. Por favor elige otro.');
            setTimeout(() => { irPaso(2); cargarHorarios(); }, 1800);
        } else {
            mostrarError(data.error || 'Ocurrió un error. Intenta de nuevo.');
        }
    })
    .catch(() => {
        btn.disabled = false;
        btn.textContent = 'Confirmar reserva';
        mostrarError('Error de conexión. Verifica tu internet.');
    });
}

function mostrarError(texto) {
    const el = document.getElementById('field-error');
    el.textContent = texto;
    el.classList.remove('hidden');
}

/* ── STEPPER / NAVEGACIÓN ── */

function irPaso(n) {
    [1,2,3,4].forEach(i => {
        document.getElementById(`paso-${i}`).classList.toggle('hidden', i !== n);
    });

    /* actualizar stepper visual */
    [1,2,3].forEach(i => {
        const st = document.getElementById(`st${i}`);
        st.classList.remove('active','done');
        if (i < n)      st.classList.add('done');
        else if (i === n) st.classList.add('active');
    });

    /* scroll al top del shell */
    document.querySelector('.shell').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
