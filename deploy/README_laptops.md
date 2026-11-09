# Configuración de las laptops del AIP

## Instalación en una laptop de prueba

1. Confirme que el servidor Flask está encendido y accesible desde la laptop. Revise que las IP de los equipos en `aip.db` sean correctas.
2. Edite `config.txt` y deje una sola URL, por ejemplo `http://192.168.1.48:5000/registro`. Cambie la dirección por la IP fija real del servidor.
3. Copie toda la carpeta `deploy` a la laptop.
4. Inicie sesión con una cuenta Windows administradora, abra PowerShell como administrador, cambie a esa carpeta y ejecute:

   ```powershell
   .\instalar_inicio.ps1
   ```

5. Si Windows bloquea la ejecución por la política local, consulte la política con el administrador de la red. No cambie la política global del colegio para instalar este acceso directo.
6. Cierre sesión y entre con la cuenta estándar del alumnado. Debe abrirse el registro en pantalla completa. Pruebe el registro y “Terminé”.
7. Para retirar el acceso en esa laptop, abra PowerShell como administrador en `deploy` y ejecute `.\desinstalar_inicio.ps1`.

No ejecute los scripts en el servidor ni en los 48 equipos antes de validar primero una laptop. El instalador solo crea/actualiza el acceso directo común y la carpeta de perfil aislado; no instala programas ni cambia la base de datos.

## Qué hacen los scripts

### `instalar_inicio.ps1`, en el orden de sus bloques

- `$ErrorActionPreference = 'Stop'` hace que un error detenga la instalación, en vez de continuar con un acceso incompleto.
- El bloque de identidad comprueba que PowerShell se haya abierto como administrador; se necesita para escribir en el inicio común de Windows.
- El bloque de configuración lee `config.txt`, recorta espacios y valida que contenga una URL absoluta `http` o `https`. No admite comillas en la URL para evitar romper los argumentos del acceso directo.
- El bloque de rutas usa `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp`, visible para todos los usuarios, y reserva `C:\ProgramData\AIP\PerfilKiosco` para el perfil separado del navegador.
- El bloque de búsqueda localiza primero Microsoft Edge y después Google Chrome en las ubicaciones habituales de `Program Files`. Si no encuentra ninguno, termina con un error claro.
- `New-Item -Force` crea el perfil si hace falta y puede repetirse. `icacls` concede al grupo integrado `Usuarios` permiso de modificar ese perfil; el script verifica su código de salida.
- `--kiosk` abre la URL en pantalla completa. Si el navegador es Edge, `--edge-kiosk-type=fullscreen` selecciona su tipo de kiosco de pantalla completa. `--user-data-dir` separa cookies, pestañas y extensiones del perfil habitual. `--no-first-run` evita la pantalla inicial del navegador.
- El bloque COM de `WScript.Shell` crea o actualiza siempre el mismo `Registro AIP.lnk`. Esta es la parte idempotente: volver a instalar no duplica el acceso.
- Las últimas líneas muestran la ruta, el navegador, la URL y el perfil utilizados.

### `desinstalar_inicio.ps1`, en el orden de sus bloques

- Detiene el proceso si hay errores y verifica la elevación administrativa.
- Calcula las mismas rutas fijas que el instalador.
- Elimina solo `Registro AIP.lnk` de inicio común si existe.
- Elimina únicamente `C:\ProgramData\AIP\PerfilKiosco` si existe. El navegador debe estar cerrado para que Windows no mantenga archivos del perfil abiertos.

## Aplicación a los 48 equipos

Después de probar una laptop, copie la carpeta `deploy` mediante Veyon o una carpeta compartida. En cada equipo, ejecútela una vez desde PowerShell elevado. Es posible automatizar la copia con las herramientas administrativas disponibles, pero el script no ejecuta remotamente nada ni modifica Veyon.

## Cambiar la IP del servidor

Edite la única línea de `config.txt` en la copia que se instalará y ejecute de nuevo `instalar_inicio.ps1` en cada equipo. El acceso directo existente se actualiza con la nueva dirección.

## Servidor apagado o inaccesible

Si la página ya estaba abierta cuando se pierde la conexión, muestra **“Servidor no disponible, reintentando...”** y vuelve a intentar cada 10 segundos. Cuando el servidor responde, recupera los datos reales; no sustituye los datos reales por alumnos ficticios.

Si el servidor ya está apagado antes de que Edge/Chrome navegue a `/registro`, Windows no puede descargar ni el HTML ni JavaScript del servidor; el navegador mostrará su página de error de conexión y la aplicación no puede mostrar su propio mensaje. Para evitarlo, encienda el servidor antes de iniciar las laptops o use una página de contingencia alojada localmente (eso requeriría aprobar un cambio de arquitectura).

## Alcance y limitaciones del modo kiosco

El acceso abre el navegador de pantalla completa, pero no convierte por sí solo Windows en un kiosco bloqueado:

- `Alt+F4` puede cerrar el navegador; `Ctrl+Alt+Del` sigue bajo control de Windows.
- Un usuario puede intentar abrir otro navegador o programa mediante accesos directos, explorador, administrador de tareas u otros caminos permitidos por la configuración local.
- Las opciones y atajos exactos dependen de la versión/políticas de Edge o Chrome. El perfil compartido evita mezclar los perfiles personales, pero no es una frontera de seguridad entre usuarios estándar del mismo equipo.

Sin software adicional, reduzca el riesgo manteniendo al alumnado en una cuenta estándar sin permisos de instalación, quitando accesos directos innecesarios, habilitando las políticas locales/de grupo del navegador y Windows que permitan solo las aplicaciones requeridas, bloqueando cambios de configuración y usando Veyon para supervisar. Si la edición de Windows lo permite, evalúe el modo Quiosco/Acceso asignado integrado de Windows con el administrador de red. Estas medidas deben probarse antes de aplicarlas a todo el laboratorio; el acceso directo por sí solo no impide salir del kiosco.
