const filtrosIncidencias = document.getElementById('filtrosIncidencias');
const formaNuevaIncidencia = document.getElementById('formNuevaIncidencia');
const tablaIncidencias = document.getElementById('tablaIncidencias');
const detalleIncidencia = document.getElementById('detalleIncidencia');
const equipoNuevaIncidencia = document.getElementById('equipoNuevaIncidencia');
const paginaAnteriorIncidencias = document.getElementById('paginaAnteriorIncidencias');
const paginaSiguienteIncidencias = document.getElementById('paginaSiguienteIncidencias');
const descargarIncidenciasExcel = document.getElementById('descargarIncidenciasExcel');
const limpiarIncidencias = document.getElementById('limpiarIncidencias');

let paginaActual = 1;
let totalPaginas = 1;
let incidenciaSeleccionada = null;

async function fetchJson(url, opciones = {}) {
  const respuesta = await fetch(url, opciones);
  const texto = await respuesta.text();
  if (!texto) return null;
  const datos = JSON.parse(texto);
  if (!respuesta.ok) throw new Error(datos?.mensaje || 'La solicitud falló.');
  return datos;
}

function obtenerFiltrosIncidencias() {
  return {
    equipo: document.getElementById('filtroIncidenciaEquipo').value.trim(),
    estado: document.getElementById('filtroIncidenciaEstado').value,
    gravedad: document.getElementById('filtroIncidenciaGravedad').value,
    desde: document.getElementById('filtroIncidenciaDesde').value,
    hasta: document.getElementById('filtroIncidenciaHasta').value,
  };
}

function buildQueryString(filtros, pagina = paginaActual, porPagina = 20) {
  const params = new URLSearchParams();
  Object.entries(filtros).forEach(([clave, valor]) => {
    if (valor) params.set(clave, String(valor));
  });
  params.set('pagina', String(pagina));
  params.set('por_pagina', String(porPagina));
  return params.toString();
}

async function cargarEquiposSelector() {
  const equipos = await fetchJson('/api/admin/estado');
  const seleccionInicial = new URLSearchParams(window.location.search).get('equipo');
  const codigos = [...new Set((equipos || []).map((equipo) => equipo.codigo).filter(Boolean))].sort();
  equipoNuevaIncidencia.innerHTML = '<option value="">Seleccione un equipo</option>' + codigos.map((codigo) => `<option value="${codigo}">${codigo}</option>`).join('');
  const equipoInicial = codigos.includes(seleccionInicial) ? seleccionInicial : '';
  if (equipoInicial) {
    equipoNuevaIncidencia.value = equipoInicial;
  }
}

async function cargarIncidencias() {
  const filtros = obtenerFiltrosIncidencias();
  const datos = await fetchJson(`/api/incidencias?${buildQueryString(filtros)}`);
  const items = Array.isArray(datos?.items) ? datos.items : [];
  totalPaginas = Math.max(1, Number(datos?.total_paginas || 1));
  paginaActual = Number(datos?.pagina || 1);

  tablaIncidencias.innerHTML = '';
  if (!items.length) {
    tablaIncidencias.innerHTML = '<tr><td colspan="6">No hay incidencias con los filtros actuales.</td></tr>';
    detalleIncidencia.innerHTML = '<h2>Detalle de la incidencia</h2><p class="detail-empty">Seleccioná una incidencia para ver su detalle.</p>';
    return;
  }

  items.forEach((incidencia) => {
    const fila = document.createElement('tr');
    fila.innerHTML = `
      <td>${incidencia.equipo || '—'}</td>
      <td>${incidencia.severidad || '—'}</td>
      <td>${incidencia.estado || '—'}</td>
      <td>${incidencia.fecha_hora_reporte || '—'}</td>
      <td>${incidencia.responsable_probable?.alumno || 'Sin alumno'}</td>
      <td><button type="button" class="button button--secondary" data-id="${incidencia.id}">Ver detalle</button></td>
    `;
    fila.querySelector('button').addEventListener('click', async () => {
      incidenciaSeleccionada = incidencia;
      const detalle = await fetchJson(`/api/incidencias/${incidencia.id}`);
      renderDetalleIncidencia(detalle);
    });
    tablaIncidencias.appendChild(fila);
  });
}

function renderDetalleIncidencia(detalle) {
  const responsable = detalle?.responsable_probable;
  const sesionesPrevias = Array.isArray(detalle?.sesiones_previas) ? detalle.sesiones_previas : [];
  const sesionesHtml = sesionesPrevias.length ? sesionesPrevias.map((sesion) => `
    <li>
      <strong>${sesion.alumno || 'Sin alumno'}</strong> · ${sesion.grado || '—'}° ${sesion.seccion || '—'} ·
      ${sesion.inicio || '—'} a ${sesion.fin || '—'}
    </li>
  `).join('') : '<li>No hubo sesiones previas antes del reporte.</li>';

  detalleIncidencia.innerHTML = `
    <h2>Detalle de la incidencia</h2>
    <div class="detail-card">
      <div class="detail-row">
        <span>Equipo</span>
        <strong>${detalle.equipo || '—'}</strong>
      </div>
      <div class="detail-row">
        <span>Descripción</span>
        <strong>${detalle.descripcion || '—'}</strong>
      </div>
      <div class="detail-row">
        <span>Severidad</span>
        <strong>${detalle.severidad || '—'}</strong>
      </div>
      <div class="detail-row">
        <span>Estado</span>
        <strong>${detalle.estado || '—'}</strong>
      </div>
      <div class="detail-row">
        <span>Responsable probable</span>
        <strong>${responsable ? `${responsable.alumno || 'Sin alumno'} · ${responsable.grado || '—'}° ${responsable.seccion || '—'} (${responsable.inicio || '—'} a ${responsable.fin || '—'})` : 'Sin datos'}</strong>
      </div>
      <div class="detail-row">
        <span>Solución</span>
        <strong>${detalle.solucion || 'Sin solución aún'}</strong>
      </div>
      <div class="detail-row">
        <span>Sesiones previas del equipo</span>
        <ul>${sesionesHtml}</ul>
      </div>
      <div class="detail-actions">
        <button type="button" class="button button--secondary" data-estado="en_revision">Marcar en revisión</button>
        <button type="button" class="button button--primary" data-estado="resuelta">Marcar resuelta</button>
      </div>
    </div>
  `;

  const botonRevision = detalleIncidencia.querySelector('[data-estado="en_revision"]');
  const botonResuelta = detalleIncidencia.querySelector('[data-estado="resuelta"]');
  botonRevision.addEventListener('click', () => actualizarEstadoIncidencia(detalle.id, 'en_revision'));
  botonResuelta.addEventListener('click', () => {
    const solucion = window.prompt('Ingresá la solución aplicada:', detalle.solucion || '');
    if (solucion === null) return;
    actualizarEstadoIncidencia(detalle.id, 'resuelta', solucion.trim());
  });
}

async function actualizarEstadoIncidencia(id, estado, solucion = '') {
  try {
    await fetchJson(`/api/incidencias/${id}/estado`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ estado, solucion }),
    });
    window.alert('Estado actualizado.');
    await cargarIncidencias();
  } catch (error) {
    window.alert(error.message || 'No se pudo actualizar la incidencia.');
  }
}

filtrosIncidencias.addEventListener('submit', async (evento) => {
  evento.preventDefault();
  paginaActual = 1;
  await cargarIncidencias();
});

limpiarIncidencias.addEventListener('click', () => {
  document.getElementById('filtroIncidenciaEquipo').value = '';
  document.getElementById('filtroIncidenciaEstado').value = '';
  document.getElementById('filtroIncidenciaGravedad').value = '';
  document.getElementById('filtroIncidenciaDesde').value = '';
  document.getElementById('filtroIncidenciaHasta').value = '';
  paginaActual = 1;
  cargarIncidencias();
});

paginaAnteriorIncidencias.addEventListener('click', async () => {
  if (paginaActual > 1) {
    paginaActual -= 1;
    await cargarIncidencias();
  }
});

paginaSiguienteIncidencias.addEventListener('click', async () => {
  if (paginaActual < totalPaginas) {
    paginaActual += 1;
    await cargarIncidencias();
  }
});

descargarIncidenciasExcel.addEventListener('click', () => {
  const filtros = obtenerFiltrosIncidencias();
  const params = new URLSearchParams();
  Object.entries(filtros).forEach(([clave, valor]) => {
    if (valor) params.set(clave, String(valor));
  });
  const url = `/api/reportes/incidencias.xlsx?${params.toString()}`;
  window.open(url, '_blank');
});

formaNuevaIncidencia.addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const equipo = equipoNuevaIncidencia.value;
  const descripcion = document.getElementById('descripcionNuevaIncidencia').value.trim();
  const severidad = document.getElementById('gravedadNuevaIncidencia').value;

  if (!equipo || !descripcion) {
    window.alert('Debe indicar equipo y descripción.');
    return;
  }

  try {
    await fetchJson('/api/incidencias', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ equipo, descripcion, gravedad: severidad }),
    });
    window.alert('Incidencia guardada correctamente.');
    formaNuevaIncidencia.reset();
    await cargarIncidencias();
  } catch (error) {
    window.alert(error.message || 'No se pudo guardar la incidencia.');
  }
});

(async function iniciar() {
  await cargarEquiposSelector();
  await cargarIncidencias();
})();
