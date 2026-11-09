const filtrosBitacora = document.getElementById('filtrosBitacora');
const filtroUsuario = document.getElementById('filtroUsuario');
const usuariosBitacora = document.getElementById('usuariosBitacora');
const filtroAccion = document.getElementById('filtroAccion');
const filtroDesde = document.getElementById('filtroDesde');
const filtroHasta = document.getElementById('filtroHasta');
const tablaBitacora = document.getElementById('tablaBitacora');
const estadoBitacora = document.getElementById('estadoBitacora');
const resumenBitacora = document.getElementById('resumenBitacora');
const paginaAnterior = document.getElementById('paginaAnteriorBitacora');
const paginaSiguiente = document.getElementById('paginaSiguienteBitacora');

let paginaActual = 1;
let totalPaginas = 0;
const porPagina = 25;

async function fetchJson(url) {
  const respuesta = await fetch(url);
  const datos = await respuesta.json();
  if (respuesta.status === 401) {
    window.location.replace('/login.html');
    throw new Error('La sesión expiró.');
  }
  if (respuesta.status === 403) {
    window.location.replace('/admin.html');
    throw new Error('La bitácora está disponible solo para administradores.');
  }
  if (!respuesta.ok) {
    throw new Error(datos.mensaje || 'No se pudo completar la solicitud.');
  }
  return datos;
}

function construirParametros() {
  const parametros = new URLSearchParams();
  if (filtroUsuario.value.trim()) parametros.set('usuario', filtroUsuario.value.trim());
  if (filtroAccion.value) parametros.set('accion', filtroAccion.value);
  if (filtroDesde.value) parametros.set('desde', filtroDesde.value);
  if (filtroHasta.value) parametros.set('hasta', filtroHasta.value);
  parametros.set('pagina', String(paginaActual));
  parametros.set('por_pagina', String(porPagina));
  return parametros.toString();
}

function agregarCelda(fila, valor) {
  const celda = document.createElement('td');
  celda.textContent = valor === null || valor === undefined || valor === '' ? '—' : String(valor);
  fila.appendChild(celda);
}

function renderizarFilas(items) {
  tablaBitacora.replaceChildren();
  if (!items.length) {
    const fila = document.createElement('tr');
    const celda = document.createElement('td');
    celda.colSpan = 6;
    celda.textContent = 'No hay acciones para los filtros seleccionados.';
    fila.appendChild(celda);
    tablaBitacora.appendChild(fila);
    return;
  }

  items.forEach((item) => {
    const fila = document.createElement('tr');
    agregarCelda(fila, item.fecha_hora);
    agregarCelda(fila, item.nombre_completo || item.usuario || 'No autenticado');
    agregarCelda(fila, item.accion);
    agregarCelda(fila, item.registro_id ? `${item.tabla_afectada} #${item.registro_id}` : item.tabla_afectada);
    agregarCelda(fila, item.detalle);
    agregarCelda(fila, item.ip_origen);
    tablaBitacora.appendChild(fila);
  });
}

async function cargarUsuarios() {
  const usuarios = await fetchJson('/api/bitacora/usuarios');
  usuarios.forEach((usuario) => {
    const opcion = document.createElement('option');
    opcion.value = usuario.usuario;
    opcion.label = usuario.nombre_completo;
    usuariosBitacora.appendChild(opcion);
  });
}

async function cargarBitacora() {
  estadoBitacora.textContent = 'Cargando bitácora...';
  try {
    const datos = await fetchJson(`/api/bitacora?${construirParametros()}`);
    renderizarFilas(datos.items);
    totalPaginas = datos.total_paginas;
    paginaActual = datos.pagina;
    resumenBitacora.textContent = `Página ${paginaActual} de ${totalPaginas || 1} · ${datos.total} registros`;
    estadoBitacora.textContent = '';
    paginaAnterior.disabled = paginaActual <= 1;
    paginaSiguiente.disabled = paginaActual >= totalPaginas;
  } catch (error) {
    estadoBitacora.textContent = error.message || 'No se pudo cargar la bitácora.';
  }
}

filtrosBitacora.addEventListener('submit', (evento) => {
  evento.preventDefault();
  paginaActual = 1;
  cargarBitacora();
});

document.getElementById('limpiarBitacora').addEventListener('click', () => {
  filtrosBitacora.reset();
  paginaActual = 1;
  cargarBitacora();
});

paginaAnterior.addEventListener('click', () => {
  if (paginaActual > 1) {
    paginaActual -= 1;
    cargarBitacora();
  }
});

paginaSiguiente.addEventListener('click', () => {
  if (paginaActual < totalPaginas) {
    paginaActual += 1;
    cargarBitacora();
  }
});

(async function iniciarBitacora() {
  try {
    await cargarUsuarios();
    await cargarBitacora();
  } catch (error) {
    estadoBitacora.textContent = error.message || 'No se pudo iniciar la bitácora.';
  }
})();
