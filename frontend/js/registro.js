const gradoSelect = document.getElementById('grado');
const seccionSelect = document.getElementById('seccion');
const buscadorAlumno = document.getElementById('buscadorAlumno');
const resultadosAlumno = document.getElementById('resultadosAlumno');
const contadorAlumnos = document.getElementById('contadorAlumnos');
const alumnoSeleccionado = document.getElementById('alumnoSeleccionado');
const alumnoIdInput = document.getElementById('alumno_id');
const formRegistro = document.getElementById('formRegistro');
const mensaje = document.getElementById('mensajeConfirmacion');
const equipoDetectado = document.getElementById('equipoDetectado');
const botonTermine = document.getElementById('botonTermine');
const urlParams = new URLSearchParams(window.location.search);
const ipSimulada = urlParams.get('ip');
const SIN_SENAL_SEGUNDOS = 120;
const CIERRE_AUTOMATICO_SEGUNDOS = 600;
const POLLING_ESTADO_MS = 20000;
const REINTENTO_SERVIDOR_MS = 10000;
let intervaloLatido = null;
let intervaloEstado = null;
let intervaloReintentoServidor = null;
let sesionActivaEnEstaPestana = false;

const tarjetaSesion = document.createElement('div');
tarjetaSesion.id = 'tarjetaSesion';
tarjetaSesion.className = 'session-card hidden';
tarjetaSesion.hidden = true;
tarjetaSesion.innerHTML = `
  <div class="session-card__header">Equipo registrado</div>
  <div class="session-card__body">
    <p><strong>Equipo:</strong> <span id="tarjetaEquipoCodigo">—</span></p>
    <p><strong>Alumno:</strong> <span id="tarjetaAlumnoNombre">—</span></p>
    <p><strong>Grado:</strong> <span id="tarjetaAlumnoGrado">—</span></p>
    <p><strong>Sección:</strong> <span id="tarjetaAlumnoSeccion">—</span></p>
    <p><strong>Hora de inicio:</strong> <span id="tarjetaHoraInicio">—</span></p>
    <p class="session-card__mensaje">Este equipo ya está registrado</p>
  </div>
  <button id="botonTermineTarjeta" type="button" class="button button--secondary">Terminé</button>
`;

const panelRegistro = formRegistro.parentNode;
panelRegistro.insertBefore(tarjetaSesion, formRegistro);
const botonTermineTarjeta = document.getElementById('botonTermineTarjeta');

function conIpSimulada(url) {
  if (!ipSimulada) {
    return url;
  }

  const urlObj = new URL(url, window.location.origin);
  urlObj.searchParams.set('ip', ipSimulada);
  return urlObj.toString();
}

function mostrarMensaje(texto, tipo = 'info') {
  mensaje.textContent = texto;
  mensaje.classList.add('is-visible');
  mensaje.style.background = tipo === 'error' ? '#fde8e8' : '#edfdf3';
  mensaje.style.color = tipo === 'error' ? '#8a1d2d' : '#13613d';
  mensaje.style.borderColor = tipo === 'error' ? '#f7bcc7' : '#bfe8cb';
}

function mostrarServidorNoDisponible() {
  mostrarMensaje('Servidor no disponible, reintentando...', 'error');
  if (!sesionActivaEnEstaPestana) {
    formRegistro.querySelectorAll('select, input, button').forEach((elemento) => {
      elemento.disabled = true;
    });
  }
  if (intervaloReintentoServidor) {
    return;
  }

  intervaloReintentoServidor = window.setInterval(async () => {
    const equipoDisponible = await cargarEquipo();
    const gradosDisponibles = await cargarGrados();
    if (!equipoDisponible || !gradosDisponibles) {
      mostrarMensaje('Servidor no disponible, reintentando...', 'error');
      return;
    }

    window.clearInterval(intervaloReintentoServidor);
    intervaloReintentoServidor = null;
    if (mensaje.textContent === 'Servidor no disponible, reintentando...') {
      mostrarMensaje('Conexión restablecida.');
    }
  }, REINTENTO_SERVIDOR_MS);
}

function ocultarFormularioRegistro() {
  aplicarEstadoFormulario(false);
  tarjetaSesion.hidden = false;
  tarjetaSesion.classList.remove('hidden');
  tarjetaSesion.style.display = 'block';
  botonTermineTarjeta.hidden = false;
  botonTermine.classList.add('hidden');
}

function aplicarEstadoFormulario(visible) {
  formRegistro.hidden = !visible;
  formRegistro.style.display = visible ? 'grid' : 'none';
  formRegistro.querySelectorAll('select, input, button').forEach((elemento) => {
    if (!visible && elemento.id !== 'botonTermine') {
      elemento.disabled = true;
      return;
    }

    if (elemento.id === 'pin') {
      elemento.disabled = !visible;
      return;
    }

    if (elemento.tagName === 'BUTTON' && elemento.type === 'submit') {
      elemento.disabled = !visible;
      return;
    }

    elemento.disabled = !visible;
  });
}

function mostrarFormularioRegistro() {
  aplicarEstadoFormulario(true);
  tarjetaSesion.hidden = true;
  tarjetaSesion.classList.add('hidden');
  tarjetaSesion.style.display = 'none';
  botonTermine.classList.add('hidden');
  botonTermineTarjeta.hidden = true;
  formRegistro.reset();
  gradoSelect.value = '';
  seccionSelect.innerHTML = '<option value="">Primero elegí grado</option>';
  seccionSelect.disabled = true;
  resetSeleccionAlumno();
  vaciarResultados();
  document.getElementById('pin').value = '';
}

function actualizarTarjetaSesion(datos = {}) {
  const equipoCodigo = datos.codigo || equipoDetectado.textContent || '—';
  const alumnoNombre = datos.alumno || '—';
  const grado = datos.grado ? `${datos.grado}.º` : '—';
  const seccion = datos.seccion || '—';
  const horaInicio = datos.hora_inicio ? new Date(datos.hora_inicio).toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }) : '—';

  document.getElementById('tarjetaEquipoCodigo').textContent = equipoCodigo;
  document.getElementById('tarjetaAlumnoNombre').textContent = alumnoNombre;
  document.getElementById('tarjetaAlumnoGrado').textContent = grado;
  document.getElementById('tarjetaAlumnoSeccion').textContent = seccion;
  document.getElementById('tarjetaHoraInicio').textContent = horaInicio;
}

function bloquearFormularioRegistrado(nombre, curso) {
  formRegistro.querySelectorAll('select, input, button').forEach((elemento) => {
    if (elemento.id === 'botonTermine') {
      elemento.disabled = false;
      return;
    }

    if (elemento.id === 'pin') {
      elemento.disabled = true;
      return;
    }

    if (elemento.tagName === 'BUTTON' && elemento.type === 'submit') {
      elemento.disabled = true;
      return;
    }

    elemento.disabled = true;
  });

  alumnoSeleccionado.hidden = false;
  alumnoSeleccionado.textContent = `${nombre} • ${curso}`;
  gradoSelect.value = '';
  seccionSelect.innerHTML = '<option value="">Primero elegí grado</option>';
  seccionSelect.disabled = true;
  buscadorAlumno.value = '';
  vaciarResultados();
}

async function enviarLatido() {
  try {
    const respuesta = await fetch(conIpSimulada('/api/latido'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!respuesta.ok) {
      const datos = await respuesta.json().catch(() => ({}));
      console.warn(datos.mensaje || 'No se pudo registrar el latido.');
      return;
    }
  } catch (error) {
    console.warn('No se pudo enviar el latido:', error);
  }
}

function iniciarLatido() {
  if (intervaloLatido) {
    return;
  }

  sesionActivaEnEstaPestana = true;
  enviarLatido();
  intervaloLatido = window.setInterval(() => {
    if (sesionActivaEnEstaPestana) {
      enviarLatido();
    }
  }, 30000);
}

function detenerLatido() {
  sesionActivaEnEstaPestana = false;
  if (intervaloLatido) {
    window.clearInterval(intervaloLatido);
    intervaloLatido = null;
  }
}

function iniciarPollingEstado() {
  if (intervaloEstado) {
    return;
  }

  intervaloEstado = window.setInterval(async () => {
    try {
      const datos = await fetchJson(conIpSimulada('/api/estado_equipo'));
      if (!datos || !datos.ocupado) {
        mostrarFormularioRegistro();
        detenerLatido();
        if (intervaloEstado) {
          window.clearInterval(intervaloEstado);
          intervaloEstado = null;
        }
        return;
      }

      actualizarTarjetaSesion(datos);
      equipoDetectado.textContent = datos.codigo || equipoDetectado.textContent;
    } catch (error) {
      console.warn('No se pudo consultar el estado del equipo:', error);
    }
  }, POLLING_ESTADO_MS);
}

function detenerPollingEstado() {
  if (intervaloEstado) {
    window.clearInterval(intervaloEstado);
    intervaloEstado = null;
  }
}

async function fetchJson(url, opciones = {}) {
  let respuesta;
  try {
    respuesta = await fetch(url, opciones);
  } catch (error) {
    mostrarServidorNoDisponible();
    throw error;
  }

  const texto = await respuesta.text();
  if (!texto) {
    if (!respuesta.ok) {
      throw new Error('La respuesta del servidor no contiene datos.');
    }
    return null;
  }

  let datos;
  try {
    datos = JSON.parse(texto);
  } catch (error) {
    throw new Error('La respuesta del servidor no es válida.');
  }

  if (!respuesta.ok) {
    const mensaje = typeof datos?.mensaje === 'string' ? datos.mensaje : 'La solicitud falló.';
    throw new Error(mensaje);
  }

  return datos;
}

function vaciarResultados() {
  resultadosAlumno.innerHTML = '<p class="resultados-alumno__vacio">Elegí grado y sección para ver la lista de alumnos.</p>';
  contadorAlumnos.textContent = '0';
}

function resetSeleccionAlumno() {
  alumnoIdInput.value = '';
  alumnoSeleccionado.hidden = true;
  alumnoSeleccionado.textContent = '';
}

function seleccionarAlumno(id, nombreCompleto) {
  alumnoIdInput.value = String(id);
  alumnoSeleccionado.hidden = false;
  alumnoSeleccionado.textContent = `Seleccionado: ${nombreCompleto}`;
  mostrarMensaje(`Alumno seleccionado: ${nombreCompleto}`);

  const filas = resultadosAlumno.querySelectorAll('.alumno-row');
  filas.forEach((fila) => {
    fila.classList.toggle('is-selected', Number(fila.dataset.id) === Number(id));
  });
}

function renderizarResultados(alumnos) {
  contadorAlumnos.textContent = String(alumnos.length);

  if (!alumnos.length) {
    resultadosAlumno.innerHTML = '<p class="resultados-alumno__vacio">No hay coincidencias para esta búsqueda.</p>';
    return;
  }

  const alumnoSeleccionadoId = alumnoIdInput.value ? Number(alumnoIdInput.value) : null;

  resultadosAlumno.innerHTML = `
    <table class="alumno-table">
      <thead>
        <tr>
          <th>Alumno</th>
          <th>Curso</th>
        </tr>
      </thead>
      <tbody>
        ${alumnos
          .map((alumno) => {
            const activo = Number(alumnoSeleccionadoId) === Number(alumno.id);
            return `
              <tr class="alumno-row ${activo ? 'is-selected' : ''}" data-id="${alumno.id}" data-alumno="${alumno.nombre_completo}">
                <td>${alumno.nombre_completo}</td>
                <td>${alumno.grado}.º ${alumno.seccion}</td>
              </tr>
            `;
          })
          .join('')}
      </tbody>
    </table>
  `;

  resultadosAlumno.querySelectorAll('.alumno-row').forEach((fila) => {
    fila.addEventListener('click', () => {
      const alumnoId = fila.dataset.id;
      const alumnoNombre = fila.dataset.alumno;
      seleccionarAlumno(alumnoId, alumnoNombre);
    });
  });
}

async function cargarEquipo() {
  try {
    const datos = await fetchJson(conIpSimulada('/api/equipo'));
    const estadoEquipo = await fetchJson(conIpSimulada('/api/estado_equipo'));

    if (!datos || !datos.codigo) {
      equipoDetectado.textContent = 'Sin equipo';
      mostrarMensaje(datos?.mensaje || 'Este equipo no está registrado. Avisa al docente.', 'error');
      formRegistro.querySelectorAll('select, input, button').forEach((elemento) => {
        if (elemento.id !== 'pin') {
          elemento.disabled = true;
        }
      });
      return true;
    }

    equipoDetectado.textContent = datos.codigo;

    if (estadoEquipo?.ocupado || estadoEquipo?.registrado) {
      const nombre = estadoEquipo.alumno || 'Alumno';
      const curso = estadoEquipo.curso || `${estadoEquipo.grado || ''}.º ${estadoEquipo.seccion || ''}`;
      actualizarTarjetaSesion({
        codigo: datos.codigo,
        alumno: nombre,
        grado: estadoEquipo.grado,
        seccion: estadoEquipo.seccion,
        hora_inicio: estadoEquipo.hora_inicio
      });
      mostrarMensaje(`Este equipo ya está registrado por ${nombre} (${curso}).`, 'info');
      ocultarFormularioRegistro();
      bloquearFormularioRegistrado(nombre, curso);
      iniciarLatido();
      iniciarPollingEstado();
      return true;
    }

    mostrarFormularioRegistro();
    formRegistro.querySelectorAll('select, button').forEach((elemento) => {
      elemento.disabled = false;
    });
    formRegistro.querySelectorAll('input').forEach((elemento) => {
      if (elemento.id !== 'pin') {
        elemento.disabled = false;
      }
    });
    return true;
  } catch (error) {
    equipoDetectado.textContent = 'Sin conexión';
    mostrarServidorNoDisponible();
    return false;
  }
}

async function cargarGrados() {
  try {
    const grados = await fetchJson(conIpSimulada('/api/grados'));

    if (!Array.isArray(grados)) {
      throw new Error('La respuesta del servidor no incluye grados válidos.');
    }

    gradoSelect.innerHTML = '<option value="">Seleccioná</option>';

    grados.forEach((grado) => {
      const option = document.createElement('option');
      option.value = String(grado);
      option.textContent = `${grado}.º`;
      gradoSelect.appendChild(option);
    });
    return true;
  } catch (error) {
    mostrarServidorNoDisponible();
    return false;
  }
}

function limpiarAlumnos() {
  resetSeleccionAlumno();
  buscadorAlumno.value = '';
  vaciarResultados();
}

async function actualizarSecciones() {
  const grado = Number(gradoSelect.value);
  seccionSelect.innerHTML = '<option value="">Seleccioná</option>';
  seccionSelect.disabled = true;
  limpiarAlumnos();

  if (!grado) {
    return;
  }

  try {
    const secciones = await fetchJson(conIpSimulada(`/api/secciones/${grado}`));

    if (!Array.isArray(secciones)) {
      throw new Error('La respuesta del servidor no incluye secciones válidas.');
    }

    seccionSelect.innerHTML = '<option value="">Seleccioná</option>';
    secciones.forEach((seccion) => {
      const option = document.createElement('option');
      option.value = seccion;
      option.textContent = seccion;
      seccionSelect.appendChild(option);
    });

    seccionSelect.disabled = false;
  } catch (error) {
    mostrarMensaje(error.message || 'No se pudieron cargar las secciones.', 'error');
  }
}

async function actualizarAlumnos() {
  const grado = Number(gradoSelect.value);
  const seccion = seccionSelect.value;

  limpiarAlumnos();

  if (!grado || !seccion) {
    return;
  }

  try {
    const alumnos = await fetchJson(conIpSimulada(`/api/alumnos/${grado}/${seccion}`));

    if (!Array.isArray(alumnos)) {
      throw new Error('La respuesta del servidor no incluye alumnos válidos.');
    }

    renderizarResultados(alumnos);
    mostrarMensaje(`Mostrando ${alumnos.length} alumnos en ${grado}.º ${seccion}.`);
  } catch (error) {
    mostrarMensaje(error.message || 'No se pudieron cargar los alumnos.', 'error');
  }
}

async function buscarAlumnosPorNombre() {
  const grado = Number(gradoSelect.value);
  const seccion = seccionSelect.value;
  const termino = buscadorAlumno.value.trim();

  if (!grado || !seccion) {
    vaciarResultados();
    mostrarMensaje('Elegí primero un grado y una sección.', 'error');
    return;
  }

  try {
    const alumnos = await fetchJson(conIpSimulada(`/api/alumnos/${grado}/${seccion}`));

    if (!Array.isArray(alumnos)) {
      throw new Error('La respuesta del servidor no incluye alumnos válidos.');
    }

    const filtrados = !termino
      ? alumnos
      : alumnos.filter((alumno) => {
          const nombreCompleto = `${alumno.nombres} ${alumno.apellidos}`.toLowerCase();
          return nombreCompleto.includes(termino.toLowerCase());
        });

    renderizarResultados(filtrados);

    if (!filtrados.length) {
      resetSeleccionAlumno();
      mostrarMensaje('No encontré alumnos con ese nombre en esta sección.', 'error');
      return;
    }

    mostrarMensaje(`Encontré ${filtrados.length} alumno${filtrados.length === 1 ? '' : 's'} en ${grado}.º ${seccion}.`);
  } catch (error) {
    mostrarMensaje(error.message || 'No se pudo buscar el alumno.', 'error');
  }
}

formRegistro.addEventListener('submit', async (event) => {
  event.preventDefault();

  const alumnoId = alumnoIdInput.value;
  const pin = document.getElementById('pin').value.trim();

  if (!alumnoId) {
    mostrarMensaje('Seleccioná un alumno de la tabla antes de registrar.', 'error');
    return;
  }

  try {
    const respuesta = await fetch(conIpSimulada('/api/registrar'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ alumno_id: Number(alumnoId), pin })
    });

    const datos = await respuesta.json();

    if (!respuesta.ok) {
      mostrarMensaje(datos.mensaje || 'No se pudo registrar la sesión.', 'error');
      return;
    }

    const nombreAlumno = alumnoSeleccionado.textContent.replace('Seleccionado: ', '').trim() || 'Alumno';
    const gradoActual = gradoSelect.value || '—';
    const seccionActual = seccionSelect.value || '—';
    actualizarTarjetaSesion({
      codigo: equipoDetectado.textContent,
      alumno: nombreAlumno,
      grado: gradoActual,
      seccion: seccionActual,
      hora_inicio: new Date().toISOString()
    });
    ocultarFormularioRegistro();
    mostrarMensaje(datos.mensaje || `Registrado en ${equipoDetectado.textContent}. ¡Buen trabajo!`);
    iniciarLatido();
    iniciarPollingEstado();
    formRegistro.reset();
    gradoSelect.value = '';
    seccionSelect.innerHTML = '<option value="">Primero elegí grado</option>';
    seccionSelect.disabled = true;
    resetSeleccionAlumno();
    vaciarResultados();
  } catch (error) {
    mostrarMensaje('No se pudo registrar. Intentá de nuevo.', 'error');
  }
});

async function cerrarSesionActual() {
  try {
    const respuesta = await fetch(conIpSimulada('/api/cerrar_alumno'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    const datos = await respuesta.json().catch(() => ({}));
    if (!respuesta.ok && !datos.ok) {
      mostrarMensaje(datos.mensaje || 'No se pudo cerrar la sesión.', 'error');
      return;
    }

    mostrarMensaje(datos.mensaje || 'Sesión cerrada correctamente.');
    mostrarFormularioRegistro();
    detenerLatido();
    detenerPollingEstado();
  } catch (error) {
    mostrarMensaje('No se pudo cerrar la sesión. Intentá de nuevo.', 'error');
  }
}

botonTermine.addEventListener('click', cerrarSesionActual);
botonTermineTarjeta.addEventListener('click', cerrarSesionActual);

gradoSelect.addEventListener('change', actualizarSecciones);
seccionSelect.addEventListener('change', actualizarAlumnos);
buscadorAlumno.addEventListener('input', buscarAlumnosPorNombre);
document.addEventListener('visibilitychange', () => {
  if (sesionActivaEnEstaPestana) {
    enviarLatido();
  }
});

(async function iniciarRegistro() {
  const equipoDisponible = await cargarEquipo();
  const gradosDisponibles = await cargarGrados();
  if (!equipoDisponible || !gradosDisponibles) {
    mostrarServidorNoDisponible();
  }
})();
