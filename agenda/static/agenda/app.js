/* ============================================================
   agenda/static/agenda/app.js  —  v2
   Sin cambios funcionales respecto a la versión anterior.
   slug se define en el HTML ANTES de este script.
   ============================================================ */

const MESES = [
  'Enero','Febrero','Marzo','Abril','Mayo','Junio',
  'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'
];
const DIAS_LARGO = ['domingo','lunes','martes','miércoles','jueves','viernes','sábado'];

let mesActual  = new Date().getMonth();
let anioActual = new Date().getFullYear();
let fechaSeleccionada = null;
let horaSeleccionada  = null;
let labelFechaActual  = '';

document.addEventListener('DOMContentLoaded', () => {
  cargarMes(anioActual, mesActual);
});

/* ── PASO 1 ── */
function cargarMes(anio, mes) {
  document.getElementById('cal-titulo').textContent = `${MESES[mes]} ${anio}`;
  const grid = document.getElementById('cal-grid');
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
  grid.innerHTML = '';

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

    const esHoy = (d === hoy.getDate() && mes === hoy.getMonth() && anio === hoy.getFullYear());
    if (esHoy) el.classList.add('hoy');

    const mesStr = (mes + 1).toString().padStart(2,'0');
    const dStr   = d.toString().padStart(2,'0');
    if (fechaSeleccionada === `${anio}-${mesStr}-${dStr}`) el.classList.add('selected');

    if (estado === 'disponible') {
      el.onclick = () => seleccionarDia(d, anio, mes, el);
    } else {
      el.disabled = true;
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
  if (nuevoAnio < hoy.getFullYear() ||
      (nuevoAnio === hoy.getFullYear() && nuevoMes < hoy.getMonth())) return;
  mesActual = nuevoMes; anioActual = nuevoAnio;
  cargarMes(anioActual, mesActual);
}

function seleccionarDia(dia, anio, mes, el) {
  document.querySelectorAll('.cal-day').forEach(b => b.classList.remove('selected'));
  el.classList.add('selected');
  const mesStr = (mes + 1).toString().padStart(2,'0');
  fechaSeleccionada = `${anio}-${mesStr}-${dia.toString().padStart(2,'0')}`;
  const nombreDia = DIAS_LARGO[new Date(anio, mes, dia).getDay()];
  labelFechaActual = `${nombreDia.charAt(0).toUpperCase() + nombreDia.slice(1)}, ${dia} de ${MESES[mes]}`;
  irPaso(2);
  cargarHorarios();
}

/* ── PASO 2 ── */
function cargarHorarios() {
  document.getElementById('label-fecha-horario').textContent = labelFechaActual.toUpperCase();
  const grid = document.getElementById('time-grid');
  grid.innerHTML = '<div class="cal-loading">Cargando…</div>';

  fetch(`/api/${slug}/horarios/?fecha=${fechaSeleccionada}`)
    .then(r => { if (!r.ok) throw r.status; return r.json(); })
    .then(data => {
      grid.innerHTML = '';
      const hs = data.horarios || [];
      if (!hs.length) {
        grid.innerHTML = '<div class="time-empty">Sin horarios disponibles para este día.</div>';
        return;
      }
      hs.forEach(h => {
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
  document.getElementById('summary-datetime').textContent = `${labelFechaActual} · ${hora}`;
  setTimeout(() => irPaso(3), 160);
}

/* ── PASO 3 ── */
function confirmarReserva() {
  const nombre = document.getElementById('f-nombre').value.trim();
  const email  = document.getElementById('f-email').value.trim();
  const tel    = document.getElementById('f-tel').value.trim();
  const errEl  = document.getElementById('field-error');
  const btn    = document.getElementById('btn-confirmar');

  errEl.classList.add('hidden');
  document.getElementById('f-nombre').classList.remove('error');
  document.getElementById('f-email').classList.remove('error');

  let err = '';
  if (!nombre) { document.getElementById('f-nombre').classList.add('error'); err = 'El nombre es requerido.'; }
  if (!email || !email.includes('@')) { document.getElementById('f-email').classList.add('error'); err = err || 'Ingresa un correo válido.'; }
  if (err) { errEl.textContent = err; errEl.classList.remove('hidden'); return; }

  btn.disabled = true;
  btn.textContent = 'Confirmando…';

  fetch(`/api/${slug}/reservar/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nombre, email, telefono: tel, fecha: fechaSeleccionada, hora: horaSeleccionada })
  })
  .then(r => r.json().then(data => ({ status: r.status, data })))
  .then(({ status, data }) => {
    btn.disabled = false;
    btn.textContent = 'Confirmar reserva';
    if (data.ok) {
      document.getElementById('confirm-detail').textContent = data.mensaje || '';
      irPaso(4);
    } else if (status === 409) {
      errEl.textContent = 'Este horario ya fue tomado. Por favor elige otro.';
      errEl.classList.remove('hidden');
      setTimeout(() => { irPaso(2); cargarHorarios(); }, 1800);
    } else {
      errEl.textContent = data.error || 'Ocurrió un error. Intenta de nuevo.';
      errEl.classList.remove('hidden');
    }
  })
  .catch(() => {
    btn.disabled = false;
    btn.textContent = 'Confirmar reserva';
    errEl.textContent = 'Error de conexión. Verifica tu internet.';
    errEl.classList.remove('hidden');
  });
}

/* ── STEPPER ── */
function irPaso(n) {
  [1,2,3,4].forEach(i => {
    document.getElementById(`paso-${i}`).classList.toggle('hidden', i !== n);
  });
  [1,2,3].forEach(i => {
    const st = document.getElementById(`st${i}`);
    st.classList.remove('active','done');
    if (i < n)       st.classList.add('done');
    else if (i === n) st.classList.add('active');
  });
  document.querySelector('.shell').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
