$ErrorActionPreference = 'Stop'

# Comprueba que el script se ejecute elevado, necesario para modificar el inicio común.
$identidad = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identidad)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Ejecute este script como administrador.'
}

# Lee la URL del archivo vecino y valida que sea una dirección HTTP o HTTPS.
$rutaConfig = Join-Path $PSScriptRoot 'config.txt'
if (-not (Test-Path -LiteralPath $rutaConfig -PathType Leaf)) {
    throw "No existe el archivo de configuración: $rutaConfig"
}
$url = (Get-Content -LiteralPath $rutaConfig -Raw).Trim()
$uri = $null
if (-not [Uri]::TryCreate($url, [UriKind]::Absolute, [ref]$uri) -or
    $uri.Scheme -notin @('http', 'https') -or
    $url.Contains('"')) {
    throw 'config.txt debe contener una URL HTTP o HTTPS válida, en una sola línea.'
}

# Usa el inicio común de Windows y una carpeta de perfil propia de este sistema.
$inicioComun = Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs\StartUp'
$perfilKiosco = Join-Path $env:ProgramData 'AIP\PerfilKiosco'
$accesoDirecto = Join-Path $inicioComun 'Registro AIP.lnk'
if (-not (Test-Path -LiteralPath $inicioComun -PathType Container)) {
    throw "No se encontró la carpeta de inicio común: $inicioComun"
}

# Busca Edge primero; si no está instalado, intenta usar Chrome.
$programFilesX86 = [Environment]::GetEnvironmentVariable('ProgramFiles(x86)')
$rutasNavegadores = @()
if ($env:ProgramFiles) {
    $rutasNavegadores += (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe')
    $rutasNavegadores += (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe')
}
if ($programFilesX86) {
    $rutasNavegadores += (Join-Path $programFilesX86 'Microsoft\Edge\Application\msedge.exe')
    $rutasNavegadores += (Join-Path $programFilesX86 'Google\Chrome\Application\chrome.exe')
}
$navegador = $rutasNavegadores | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -First 1
if (-not $navegador) {
    throw 'No se encontró Microsoft Edge ni Google Chrome en las ubicaciones habituales.'
}

# Crea un perfil aislado compartido por los usuarios estándar del equipo.
New-Item -ItemType Directory -Path $perfilKiosco -Force | Out-Null
& icacls.exe $perfilKiosco /grant '*S-1-5-32-545:(OI)(CI)M' /T /C | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudieron conceder permisos de modificación del perfil al grupo Usuarios.'
}

# Configura modo kiosco de pantalla completa para Edge o Chrome.
$argumentos = '--kiosk "{0}" --user-data-dir="{1}" --no-first-run' -f $url, $perfilKiosco
if ([IO.Path]::GetFileName($navegador) -ieq 'msedge.exe') {
    $argumentos += ' --edge-kiosk-type=fullscreen'
}

# Reescribe siempre el mismo acceso directo: el script es idempotente.
$shell = New-Object -ComObject WScript.Shell
$atajo = $shell.CreateShortcut($accesoDirecto)
$atajo.TargetPath = $navegador
$atajo.Arguments = $argumentos
$atajo.WorkingDirectory = Split-Path -Parent $navegador
$atajo.Description = 'Abrir el registro del Aula de Innovación Pedagógica'
$atajo.IconLocation = "$navegador,0"
$atajo.Save()

Write-Host "Acceso directo creado o actualizado: $accesoDirecto"
Write-Host "Navegador: $navegador"
Write-Host "URL del registro: $url"
Write-Host "Perfil aislado: $perfilKiosco"
Write-Host 'Se abrirá al iniciar sesión cualquier usuario de este equipo.'
