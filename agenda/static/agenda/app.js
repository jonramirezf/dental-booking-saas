let fechaSeleccionada = null;
let horaSeleccionada = null;

const hoy = new Date();
const mes = (hoy.getMonth() + 1).toString().padStart(2, '0');
const anio = hoy.getFullYear();

fetch(`/api/${slug}/dias/`)
.then(res => res.json())
.then(data => {
    const diasDiv = document.getElementById('dias');
    diasDiv.innerHTML = '';

    Object.entries(data.dias).forEach(([dia, estado]) => {

        // mostramos todos menos pasado
        if (estado !== 'pasado') {

            const btn = document.createElement('button');
            btn.innerText = dia;

            if (estado !== 'disponible') {
                btn.style.opacity = "0.4";
            }

            btn.onclick = () => {

                document.querySelectorAll('.dias button')
                    .forEach(b => b.classList.remove('activo'));

                btn.classList.add('activo');

                fechaSeleccionada = `${anio}-${mes}-${dia.padStart(2,'0')}`;

                cargarHorarios();
            };

            diasDiv.appendChild(btn);
        }
    });
});

function cargarHorarios() {

    fetch(`/api/${slug}/horarios/?fecha=${fechaSeleccionada}`)
    .then(res => res.json())
    .then(data => {

        const div = document.getElementById('horarios');
        div.innerHTML = '';

        data.horarios.forEach(h => {

            const btn = document.createElement('button');
            btn.innerText = h;

            btn.onclick = () => {

                document.querySelectorAll('.horarios button')
                    .forEach(b => b.classList.remove('activo'));

                btn.classList.add('activo');
                horaSeleccionada = h;
            };

            div.appendChild(btn);
        });
    });
}

function reservar() {

    const nombre = document.getElementById('nombre').value;
    const email = document.getElementById('email').value;

    fetch(`/api/${slug}/reservar/`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            nombre,
            email,
            fecha: fechaSeleccionada,
            hora: horaSeleccionada
        })
    })
    .then(res => res.json())
    .then(data => {
        alert(data.ok ? "Reserva creada" : "Error");
    });
}