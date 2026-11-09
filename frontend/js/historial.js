const formHistorial = document.getElementById('filtrosHistorial');
const tablaHistorial = document.getElementById('tablaHistorial');
const descargaExcel = document.getElementById('descargarHistorialExcel');
const limpiarHistorial = document.getElementById('limpiarHistorial');
const anteriorHistorial = document.getElementById('paginaAnteriorHistorial');
const siguienteHistorial = document.getElementById('paginaSiguienteHistorial');
const filtroEquipo = document.getElementById('filtroEquipo');
const filtroAlumno = document.getElementById('filtroAlumno');
const sugerenciasEquipo = document.getElementById('sugerenciasEquipo');
const sugerenciasAlumno = document.getElementById('sugerenciasAlumno');

let paginaActual = 1;
let totalPaginas = 1;

async function fetchJson(url, opciones = {}) {
  const respuesta = await fetch(url, opciones);
  const texto = await respuesta.text();
  if (!texto) return null;
  const datos = JSON.parse(texto);
  if (!respuesta.ok) throw new Error(datos?.mensaje || 'La solicitud falló.');
  return datos;
}

function mostrarSugerencias(destino, items, tipo) {
  if (!items.length) {
    destino.innerHTML = '';
    destino.classList.add('hidden');
    return;
  }

  destino.innerHTML = items.map((item) => {
    if (tipo === 'equipo') {
      const codigo = item.codigo || item.equipo || 'Equipo';
      return `<button type="button" class="suggestion-item" data-valor="${codigo}">${codigo}</button>`;
    }

    const nombre = item.nombre_completo || [item.nombres, item.apellidos].filter(Boolean).join(' ') || 'Sin nombre';
    const codigoAlumno = item.codigo_alumno || item.codigo || '';
    const valor = codigoAlumno || nombre;
    return `<button type="button" class="suggestion-item" data-valor="${valor}" data-label="${nombre}">
      <span class="suggestion-item__nombre">${nombre}</span>
      <span class="suggestion-item__codigo">${codigoAlumno ? `• ${codigoAlumno}` : ''}</span>
    </button>`;
  }).join('');

  destino.classList.remove('hidden');
  destino.querySelectorAll('.suggestion-item').forEach((boton) => {
    boton.addEventListener('click', async () => {
      const input = tipo === 'equipo' ? filtroEquipo : filtroAlumno;
      const valor = boton.dataset.valor || '';
      const label = boton.dataset.label || valor;
      input.value = valor;
      destino.classList.add('hidden');

      if (tipo === 'alumno') {
        input.title = label;
        await cargarHistorial();
      } else {
        filtroEquipo.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });
  });
}

async function buscarSugerenciasEquipo(termino) {
  const valor = (termino || '').trim();
  if (!valor) {
    sugerenciasEquipo.innerHTML = '';
    sugerenciasEquipo.classList.add('hidden');
    return;
  }

  try {
    const estado = await fetchJson('/api/admin/estado');
    const equipos = Array.isArray(estado) ? estado : (Array.isArray(estado?.equipos) ? estado.equipos : []);
    const lista = equipos.filter((equipo) => {
      const codigo = String(equipo?.codigo || '').toLowerCase();
      const alumno = String(equipo?.alumno || '').toLowerCase();
      const busqueda = valor.toLowerCase();
      return codigo.includes(busqueda) || alumno.includes(busqueda);
    }).slice(0, 8);
    mostrarSugerencias(sugerenciasEquipo, lista.map((equipo) => ({ codigo: equipo.codigo || equipo.equipo })), 'equipo');
  } catch (error) {
    sugerenciasEquipo.innerHTML = '';
    sugerenciasEquipo.classList.add('hidden');
  }
}

async function buscarSugerenciasAlumno(termino) {
  const valor = (termino || '').trim();
  if (!valor) {
    sugerenciasAlumno.innerHTML = '';
    sugerenciasAlumno.classList.add('hidden');
    return;
  }

  try {
    const datos = await fetchJson(`/api/alumnos/buscar?q=${encodeURIComponent(valor)}`);
    const lista = Array.isArray(datos) ? datos : [];
    mostrarSugerencias(sugerenciasAlumno, lista.slice(0, 8), 'alumno');
  } catch (error) {
    sugerenciasAlumno.innerHTML = '';
    sugerenciasAlumno.classList.add('hidden');
  }
}

function obtenerFiltros() {
  return {
    equipo: filtroEquipo.value.trim(),
    alumno: filtroAlumno.value.trim(),
    grado: document.getElementById('filtroGrado').value.trim(),
    seccion: document.getElementById('filtroSeccion').value,
    desde: document.getElementById('filtroDesde').value,
    hasta: document.getElementById('filtroHasta').value,
    tipo_cierre: document.getElementById('filtroTipoCierre').value,
    solo_abiertas: document.getElementById('filtroSoloAbiertas').value,
  };
}

function construirQueryString(filtros, pagina = paginaActual, porPagina = 20) {
  const params = new URLSearchParams();
  Object.entries(filtros).forEach(([clave, valor]) => {
    if (valor !== '' && valor !== null && valor !== undefined) {
      params.set(clave, String(valor));
    }
  });
  params.set('pagina', String(pagina));
  params.set('por_pagina', String(porPagina));
  return params.toString();
}

async function cargarHistorial() {
  const filtros = obtenerFiltros();
  const datos = await fetchJson(`/api/historial?${construirQueryString(filtros)}`);
  const items = Array.isArray(datos?.items) ? datos.items : [];
  totalPaginas = Number(datos?.total_paginas || 1);
  paginaActual = Number(datos?.pagina || 1);

  tablaHistorial.innerHTML = '';
  if (!items.length) {
    tablaHistorial.innerHTML = '<tr><td colspan="8">No hay sesiones para los filtros actuales.</td></tr>';
    return;
  }

  items.forEach((item) => {
    const fila = document.createElement('tr');
    fila.innerHTML = `
      <td>${item.equipo || '—'}</td>
      <td>${item.alumno || '—'}</td>
      <td>${item.grado ?? '—'}</td>
      <td>${item.seccion || '—'}</td>
      <td>${item.inicio || '—'}</td>
      <td>${item.fin || '—'}</td>
      <td>${item.duracion || '—'}</td>
      <td>${item.tipo_cierre || '—'}</td>
    `;
    tablaHistorial.appendChild(fila);
  });
}

filtroEquipo.addEventListener('input', () => {
  buscarSugerenciasEquipo(filtroEquipo.value);
});

filtroAlumno.addEventListener('input', () => {
  if (filtroAlumno.value.trim().length < 2) {
    sugerenciasAlumno.innerHTML = '';
    sugerenciasAlumno.classList.add('hidden');
    return;
  }
  buscarSugerenciasAlumno(filtroAlumno.value);
});

filtroEquipo.addEventListener('focus', () => {
  if (filtroEquipo.value.trim()) {
    buscarSugerenciasEquipo(filtroEquipo.value);
  }
});

filtroAlumno.addEventListener('focus', () => {
  if (filtroAlumno.value.trim().length >= 2) {
    buscarSugerenciasAlumno(filtroAlumno.value);
  }
});

document.addEventListener('click', (evento) => {
  if (!evento.target.closest('.suggestion-item') && !evento.target.closest('#filtroAlumno') && !evento.target.closest('#filtroEquipo')) {
    sugerenciasAlumno.classList.add('hidden');
    sugerenciasEquipo.classList.add('hidden');
  }
});

formHistorial.addEventListener('submit', async (evento) => {
  evento.preventDefault();
  paginaActual = 1;
  await cargarHistorial();
  sugerenciasAlumno.classList.add('hidden');
  sugerenciasEquipo.classList.add('hidden');
});

limpiarHistorial.addEventListener('click', () => {
  filtroEquipo.value = '';
  filtroAlumno.value = '';
  document.getElementById('filtroGrado').value = '';
  document.getElementById('filtroSeccion').value = '';
  document.getElementById('filtroDesde').value = '';
  document.getElementById('filtroHasta').value = '';
  document.getElementById('filtroTipoCierre').value = '';
  document.getElementById('filtroSoloAbiertas').value = '0';
  sugerenciasAlumno.innerHTML = '';
  sugerenciasEquipo.innerHTML = '';
  sugerenciasAlumno.classList.add('hidden');
  sugerenciasEquipo.classList.add('hidden');
  paginaActual = 1;
  cargarHistorial();
});

anteriorHistorial.addEventListener('click', async () => {
  if (paginaActual > 1) {
    paginaActual -= 1;
    await cargarHistorial();
  }
});

siguienteHistorial.addEventListener('click', async () => {
  if (paginaActual < totalPaginas) {
    paginaActual += 1;
    await cargarHistorial();
  }
});

descargaExcel.addEventListener('click', () => {
  const filtros = obtenerFiltros();
  const params = new URLSearchParams();
  Object.entries(filtros).forEach(([clave, valor]) => {
    if (valor !== '' && valor !== null && valor !== undefined) {
      params.set(clave, String(valor));
    }
  });
  window.open(`/api/reportes/historial.xlsx?${params.toString()}`, '_blank');
});

(async function iniciar() {
  const params = new URLSearchParams(window.location.search);
  const equipo = params.get('equipo');
  if (equipo) {
    document.getElementById('filtroEquipo').value = equipo;
  }
  await cargarHistorial();
})();
