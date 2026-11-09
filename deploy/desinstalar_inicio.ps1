$ErrorActionPreference = 'Stop'

# Comprueba que el script se ejecute elevado, necesario para borrar del inicio común.
$identidad = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identidad)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Ejecute este script como administrador.'
}

# Calcula las mismas rutas fijas que usa el instalador.
$inicioComun = Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs\StartUp'
$perfilKiosco = Join-Path $env:ProgramData 'AIP\PerfilKiosco'
$accesoDirecto = Join-Path $inicioComun 'Registro AIP.lnk'

# Elimina únicamente el acceso directo propio del sistema AIP.
if (Test-Path -LiteralPath $accesoDirecto -PathType Leaf) {
    Remove-Item -LiteralPath $accesoDirecto -Force
    Write-Host "Acceso directo eliminado: $accesoDirecto"
} else {
    Write-Host 'No había un acceso directo de AIP instalado.'
}

# Borra el perfil aislado de AIP si existe; no modifica otros perfiles del navegador.
if (Test-Path -LiteralPath $perfilKiosco -PathType Container) {
    Remove-Item -LiteralPath $perfilKiosco -Recurse -Force
    Write-Host "Perfil aislado eliminado: $perfilKiosco"
} else {
    Write-Host 'No había un perfil aislado de AIP.'
}
