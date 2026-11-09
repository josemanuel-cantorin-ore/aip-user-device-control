const gridEquipos = document.getElementById('gridEquipos');
const detalleEquipo = document.getElementById('detalleEquipo');
const totalOcupados = document.getElementById('totalOcupados');
const totalLibres = document.getElementById('totalLibres');
const totalSinSenal = document.getElementById('totalSinSenal');
const totalMantenimiento = document.getElementById('totalMantenimiento');
const estadoServidor = document.getElementById('estadoServidor');
const ultimaActualizacion = document.getElementById('ultimaActualizacion');
const buscadorEquipo = document.getElementById('busquedaEquipo');
const filtroGrado = document.getElementById('filtroGrado');
const filtroSeccion = document.getElementById('filtroSeccion');
const cerrarTodas = document.getElementById('cerrarTodas');
const abrirIncidencia = document.getElementById('abrirIncidencia');
const formIncidenciaWrap = document.getElementById('formIncidenciaWrap');
const equipoIncidencia = document.getElementById('equipoIncidencia');
const formIncidencia = document.getElementById('formIncidencia');
const sesionAdmin = document.getElementById('sesionAdmin');
const cerrarSesionAdmin = document.getElementById('cerrarSesionAdmin');
const enlaceBitacora = document.getElementById('enlaceBitacora');
const formCambiarPassword = document.getElementById('formCambiarPassword');
const mensajePassword = document.getElementById('mensajePassword');

let equipos = [];
let equipoSeleccionado = null;

async function fetchJson(url, opciones = {}) {
  const respuesta = await fetch(url, opciones);
  if (respuesta.status === 401) {
    window.location.replace('/login.html');
    throw new Error('La sesión expiró. Inicie sesión nuevamente.');
  }
  const texto = await respuesta.text();

  if (!texto) {
    return null;
  }

  const datos = JSON.parse(texto);

  if (!respuesta.ok) {
    throw new Error(typeof datos?.mensaje === 'string' ? datos.mensaje : 'La solicitud falló.');
  }

  return datos;
}

async function cargarSesionAdmin() {
  const datos = await fetchJson('/api/sesion_admin');
  if (!datos?.autenticado) {
    window.location.replace('/login.html');
    return;
  }

  sesionAdmin.textContent = `${datos.usuario.nombre_completo} (${datos.usuario.rol})`;
  cerrarTodas.hidden = datos.usuario.rol !== 'admin';
  enlaceBitacora.hidden = datos.usuario.rol !== 'admin';
}

cerrarSesionAdmin.addEventListener('click', async () => {
  try {
    await fetchJson('/api/logout', { method: 'POST' });
    window.location.replace('/login.html');
  } catch (error) {
    window.alert(error.message || 'No se pudo cerrar la sesión.');
  }
});

formCambiarPassword.addEventListener('submit', async (evento) => {
  evento.preventDefault();
  mensajePassword.textContent = '';
  try {
    const datos = await fetchJson('/api/cambiar_password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contrasena_actual: document.getElementById('contrasenaActual').value,
        contrasena_nueva: document.getElementById('contrasenaNueva').value,
      }),
    });
    formCambiarPassword.reset();
    mensajePassword.textContent = datos.mensaje;
  } catch (error) {
    mensajePassword.textContent = error.message || 'No se pudo actualizar la contraseña.';
  }
});

function normalizarEstado(estado) {
  if (!estado) return 'libre';
  if (estado === 'sin señal') return 'sin_señal';
  if (estado === 'sin_señal') return 'sin_señal';
  return estado;
}

function obtenerEstadoVisual(equipo) {
  const equipoEstado = String(equipo.equipo_estado || 'activo').trim().toLowerCase();
  if (equipoEstado === 'mantenimiento' || equipoEstado === 'baja') {
    return equipoEstado;
  }
  return normalizarEstado(equipo.estado);
}

function estadoTexto(estado) {
  if (estado === 'ocupado') return 'Ocupado';
  if (estado === 'libre') return 'Libre';
  if (estado === 'sin_señal') return 'Sin señal';
  if (estado === 'mantenimiento') return 'Mantenimiento';
  if (estado === 'baja') return 'Baja';
  return 'Libre';
}

function nombreCorto(nombre) {
  return (nombre || '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .join(' ');
}

function parsearFechaHora(fecha) {
  if (!fecha) return null;

  const valor = String(fecha).trim();
  if (!valor) return null;

  const conT = valor.includes('T') ? valor : valor.replace(' ', 'T');
  const variantes = [];

  if (!/[zZ]|[+-]\d{2}:\d{2}$/.test(conT)) {
    variantes.push(`${conT}Z`);
  }
  variantes.push(conT);

  for (const variante of variantes) {
    const fechaDate = new Date(variante);
    if (!Number.isNaN(fechaDate.getTime())) {
      return fechaDate;
    }
  }

  const fechaLocal = new Date(valor);
  if (!Number.isNaN(fechaLocal.getTime())) {
    return fechaLocal;
  }

  return null;
}

function formatTiempoTranscurrido(fechaInicio) {
  if (!fechaInicio) return '—';

  const inicio = parsearFechaHora(fechaInicio);
  if (!inicio) {
    return '—';
  }

  const diferenciaMs = Date.now() - inicio.getTime();
  if (diferenciaMs < 0) {
    return '0 min';
  }

  const totalMinutos = Math.max(0, Math.floor(diferenciaMs / 60000));
  const horas = Math.floor(totalMinutos / 60);
  const minutos = totalMinutos % 60;

  if (horas > 0) {
    return `${horas} h ${minutos} min`;
  }

  return `${minutos} min`;
}

function obtenerEstadisticas() {
  const ocupados = equipos.filter((equipo) => obtenerEstadoVisual(equipo) === 'ocupado').length;
  const libres = equipos.filter((equipo) => obtenerEstadoVisual(equipo) === 'libre').length;
  const sinSenal = equipos.filter((equipo) => obtenerEstadoVisual(equipo) === 'sin_señal').length;
  const mantenimiento = equipos.filter((equipo) => ['mantenimiento', 'baja'].includes(obtenerEstadoVisual(equipo))).length;

  totalOcupados.textContent = ocupados;
  totalLibres.textContent = libres;
  totalSinSenal.textContent = sinSenal;
  totalMantenimiento.textContent = mantenimiento;
}

function obtenerEquiposFiltrados() {
  const termino = (buscadorEquipo?.value || '').trim().toLowerCase();
  const gradoActual = filtroGrado?.value || 'todos';
  const seccionActual = filtroSeccion?.value || 'todos';

  return equipos.filter((equipo) => {
    const coincideBusqueda = !termino || `${equipo.codigo} ${equipo.alumno}`.toLowerCase().includes(termino);
    const coincideGrado = gradoActual === 'todos' || String(equipo.grado) === String(gradoActual);
    const coincideSeccion = seccionActual === 'todos' || String(equipo.seccion).toUpperCase() === String(seccionActual).toUpperCase();

    return coincideBusqueda && coincideGrado && coincideSeccion;
  });
}

function parseUbicacion(ubicacion) {
  if (!ubicacion) {
    return { fila: null, puesto: null };
  }

  const match = ubicacion.match(/fila\s*(\d+)\s*[-,\s]*puesto\s*(\d+)/i);
  if (match) {
    return { fila: Number(match[1]), puesto: Number(match[2]) };
  }

  const matchSimple = ubicacion.match(/(\d+)\s*[-,\s]*(\d+)/);
  if (matchSimple) {
    return { fila: Number(matchSimple[1]), puesto: Number(matchSimple[2]) };
  }

  return { fila: null, puesto: null };
}

function obtenerDimensionMapa(items) {
  const filas = [];
  const puestos = [];

  items.forEach((equipo) => {
    const ubicacion = parseUbicacion(equipo.ubicacion);
    if (ubicacion.fila && ubicacion.puesto) {
      filas.push(ubicacion.fila);
      puestos.push(ubicacion.puesto);
    }
  });

  const filaMax = Math.max(1, ...filas, 6);
  const puestoMax = Math.max(1, ...puestos, 8);

  return {
    filas: filaMax,
    columnas: puestoMax,
  };
}

function renderEquipos() {
  const equiposVisibles = obtenerEquiposFiltrados();
  gridEquipos.innerHTML = '';

  if (!equiposVisibles.length) {
    gridEquipos.innerHTML = '<div class="detail-empty">No hay equipos con ese filtro.</div>';
    return;
  }

  const { columnas } = obtenerDimensionMapa(equiposVisibles);
  gridEquipos.style.gridTemplateColumns = `repeat(${columnas}, minmax(90px, 1fr))`;

  equiposVisibles.forEach((equipo) => {
    const visualState = obtenerEstadoVisual(equipo);
    const nombre = visualState === 'ocupado' ? nombreCorto(equipo.alumno) : estadoTexto(visualState);
    const coincideBusqueda = !!(buscadorEquipo?.value || '').trim() && `${equipo.codigo} ${equipo.alumno}`.toLowerCase().includes((buscadorEquipo.value || '').trim().toLowerCase());
    const card = document.createElement('button');
    card.type = 'button';
    card.className = `equipment-card equipment-card--${visualState}${equipoSeleccionado && equipoSeleccionado.codigo === equipo.codigo ? ' is-selected' : ''}${coincideBusqueda ? ' is-highlighted' : ''}`;
    card.setAttribute('data-codigo', equipo.codigo);

    card.innerHTML = `
      <span class="equipment-card__code">${equipo.codigo}</span>
      <span class="equipment-card__name">${nombre}</span>
    `;

    card.addEventListener('click', () => {
      equipoSeleccionado = equipo;
      mostrarDetalle(equipo);
      renderEquipos();
    });

    gridEquipos.appendChild(card);
  });
}

function mostrarDetalle(equipo) {
  if (!equipo) {
    detalleEquipo.innerHTML = '<h2>Detalle del equipo</h2><p class="detail-empty">Seleccioná un equipo para ver su estado.</p>';
    return;
  }

  const visualState = obtenerEstadoVisual(equipo);
  const esOcupado = visualState === 'ocupado';
  const tiempoTranscurrido = esOcupado ? formatTiempoTranscurrido(equipo.horaInicio) : '—';
  const fechaHoraInicio = esOcupado && equipo.horaInicio ? parsearFechaHora(equipo.horaInicio) : null;
  const detalleHora = fechaHoraInicio ? fechaHoraInicio.toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }) : '—';
  const detalleGrado = esOcupado && equipo.grado && equipo.grado !== '—' && equipo.seccion && equipo.seccion !== '—' ? `${equipo.grado}.º ${equipo.seccion}` : '—';
  const botonLabel = visualState === 'ocupado' || visualState === 'sin_señal' ? 'Cerrar sesión' : 'Sin sesión abierta';

  detalleEquipo.innerHTML = `
    <h2>${equipo.codigo}</h2>
    <div class="detail-card">
      <div class="detail-row">
        <span>Estado</span>
        <strong>${estadoTexto(visualState)}</strong>
      </div>
      <div class="detail-row">
        <span>Alumno</span>
        <strong>${esOcupado ? equipo.alumno : 'Sin alumno'}</strong>
      </div>
      <div class="detail-row">
        <span>Grado y sección</span>
        <strong>${detalleGrado}</strong>
      </div>
      <div class="detail-row">
        <span>Hora de inicio</span>
        <strong>${detalleHora}</strong>
      </div>
      <div class="detail-row">
        <span>Tiempo transcurrido</span>
        <strong>${tiempoTranscurrido}</strong>
      </div>
      <div class="detail-actions">
        <button class="button button--secondary" type="button" data-action="cerrar-equipo" ${visualState === 'ocupado' || visualState === 'sin_señal' ? '' : 'disabled'}>${botonLabel}</button>
        <button class="button button--secondary" type="button" data-action="historial-equipo">Historial</button>
        <button class="button button--primary" type="button" data-action="incidencia-equipo">Reportar incidencia</button>
      </div>
    </div>
  `;

  const botonCerrarEquipo = detalleEquipo.querySelector('[data-action="cerrar-equipo"]');
  if (botonCerrarEquipo && !botonCerrarEquipo.disabled) {
    botonCerrarEquipo.addEventListener('click', () => cerrarEquipoSeleccionado(equipo.codigo));
  }

  const botonHistorialEquipo = detalleEquipo.querySelector('[data-action="historial-equipo"]');
  if (botonHistorialEquipo) {
    botonHistorialEquipo.addEventListener('click', () => {
      window.location.href = `/historial.html?equipo=${encodeURIComponent(equipo.codigo)}`;
    });
  }

  const botonIncidenciaEquipo = detalleEquipo.querySelector('[data-action="incidencia-equipo"]');
  if (botonIncidenciaEquipo) {
    botonIncidenciaEquipo.addEventListener('click', () => {
      window.location.href = `/incidencias.html?equipo=${encodeURIComponent(equipo.codigo)}`;
    });
  }
}

function inicializarSelectorIncidencias() {
  if (!equipoIncidencia) return;
  equipoIncidencia.innerHTML = equipos
    .map((equipo) => `<option value="${equipo.codigo}">${equipo.codigo}</option>`)
    .join('');
}

function inicializarFiltros() {
  const grados = [...new Set(equipos
    .map((equipo) => Number(equipo.grado))
    .filter((grado) => Number.isInteger(grado)))].sort((a, b) => a - b);

  const secciones = [...new Set(equipos
    .map((equipo) => String(equipo.seccion))
    .filter((seccion) => seccion && seccion !== '—'))].sort();

  filtroGrado.innerHTML = '<option value="todos">Todos</option>' + grados.map((grado) => `<option value="${grado}">${grado}</option>`).join('');
  filtroSeccion.innerHTML = '<option value="todos">Todas</option>' + secciones.map((seccion) => `<option value="${seccion}">${seccion}</option>`).join('');
}

function prepararEquipoDesdeApi(item) {
  return {
    id: item.id,
    codigo: item.codigo,
    estado: normalizarEstado(item.estado),
    equipo_estado: item.equipo_estado || 'activo',
    alumno: item.alumno || 'Sin alumno',
    grado: item.grado || '—',
    seccion: item.seccion || '—',
    horaInicio: item.horaInicio || null,
    ip: item.ip,
    ubicacion: item.ubicacion,
    nombreHost: item.nombre_host,
    tipo: item.tipo,
  };
}

async function cargarEstadoAula({ mostrarAviso = true } = {}) {
  try {
    const datos = await fetchJson('/api/admin/estado');
    if (!Array.isArray(datos)) {
      throw new Error('La respuesta del servidor no es válida.');
    }

    equipos = datos.map(prepararEquipoDesdeApi);
    obtenerEstadisticas();
    inicializarSelectorIncidencias();
    inicializarFiltros();
    renderEquipos();

    const ahora = new Date();
    ultimaActualizacion.textContent = ahora.toLocaleTimeString('es-AR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });

    estadoServidor.textContent = 'Servidor conectado';
    estadoServidor.classList.remove('is-error');

    if (!equipoSeleccionado) {
      mostrarDetalle(null);
      return;
    }

    const equipoActualizado = equipos.find((equipo) => equipo.codigo === equipoSeleccionado.codigo);
    equipoSeleccionado = equipoActualizado || null;
    mostrarDetalle(equipoSeleccionado);
  } catch (error) {
    console.error(error);
    estadoServidor.textContent = 'Sin conexión con el servidor';
    estadoServidor.classList.add('is-error');

    if (mostrarAviso) {
      detalleEquipo.innerHTML = '<h2>Detalle del equipo</h2><p class="detail-empty">No se pudo obtener el estado actual del aula. Reintentando en segundo plano.</p>';
    }
  }
}

async function cerrarEquipoSeleccionado(codigoEquipo) {
  try {
    const confirmar = window.confirm(`¿Seguro que querés cerrar la sesión de ${codigoEquipo}?`);
    if (!confirmar) return;

    const datos = await fetchJson(`/api/admin/cerrar/${encodeURIComponent(codigoEquipo)}`, { method: 'POST' });
    window.alert(datos?.mensaje || `Se cerró ${codigoEquipo}.`);
    await cargarEstadoAula();
  } catch (error) {
    window.alert(error.message || 'No se pudo cerrar la sesión del equipo.');
  }
}

cerrarTodas.addEventListener('click', async () => {
  const confirmar = window.confirm('¿Seguro que querés cerrar todas las sesiones activas?');
  if (!confirmar) return;

  try {
    const datos = await fetchJson('/api/admin/cerrar_todas', { method: 'POST' });
    window.alert(datos?.mensaje || 'Se cerraron todas las sesiones.');
    await cargarEstadoAula();
  } catch (error) {
    window.alert(error.message || 'No se pudieron cerrar todas las sesiones.');
  }
});

abrirIncidencia.addEventListener('click', () => {
  const equipoDestino = equipoSeleccionado ? equipoSeleccionado.codigo : '';
  const destino = equipoDestino ? `/incidencias.html?equipo=${encodeURIComponent(equipoDestino)}` : '/incidencias.html';
  window.location.href = destino;
});

formIncidencia.addEventListener('submit', async (event) => {
  event.preventDefault();
  const equipo = equipoIncidencia.value;
  const descripcion = document.getElementById('descripcionIncidencia').value.trim();
  const gravedad = document.getElementById('gravedadIncidencia').value;

  if (!descripcion) {
    window.alert('Escribí una descripción de la incidencia antes de guardar.');
    return;
  }

  try {
    const datos = await fetchJson('/api/incidencias', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ equipo, descripcion, gravedad }),
    });
    window.alert(datos?.mensaje || `Incidencia registrada: ${equipo} - ${gravedad} - ${descripcion}`);
    formIncidencia.reset();
    formIncidenciaWrap.classList.add('hidden');
  } catch (error) {
    window.alert(error.message || 'No se pudo guardar la incidencia.');
  }
});

buscadorEquipo.addEventListener('input', () => {
  renderEquipos();
});

filtroGrado.addEventListener('change', () => {
  renderEquipos();
});

filtroSeccion.addEventListener('change', () => {
  renderEquipos();
});

obtenerEstadisticas();
renderEquipos();
mostrarDetalle(null);
cargarSesionAdmin().catch((error) => {
  console.error(error);
  window.location.replace('/login.html');
});
cargarEstadoAula();
setInterval(() => cargarEstadoAula({ mostrarAviso: false }), 8000);
setInterval(() => {
  if (equipoSeleccionado) {
    mostrarDetalle(equipoSeleccionado);
  }
}, 1000);
