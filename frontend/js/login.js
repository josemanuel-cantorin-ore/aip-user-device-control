const formLogin = document.getElementById('formLogin');
const mensajeLogin = document.getElementById('mensajeLogin');
const botonLogin = document.getElementById('botonLogin');

formLogin.addEventListener('submit', async (evento) => {
  evento.preventDefault();
  mensajeLogin.textContent = '';
  botonLogin.disabled = true;

  try {
    const respuesta = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        usuario: document.getElementById('usuario').value.trim(),
        contrasena: document.getElementById('contrasena').value,
      }),
    });
    const datos = await respuesta.json();
    if (!respuesta.ok) {
      mensajeLogin.textContent = datos.mensaje || 'Usuario o contraseña incorrectos';
      return;
    }
    window.location.replace('/admin.html');
  } catch (error) {
    mensajeLogin.textContent = 'No se pudo contactar al servidor. Intente nuevamente.';
  } finally {
    botonLogin.disabled = false;
  }
});
