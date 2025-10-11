$ErrorActionPreference = 'Stop'
$toolsDir = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$shortcutPath = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\PyShell.lnk"

# Remove PATH entry added during install
Uninstall-ChocolateyPath "$toolsDir" 'User'

# Remove Start Menu shortcut if it exists
if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath -Force
    Write-Host "Removed Start Menu shortcut for PyShell."
}

Write-Host "PyShell has been uninstalled successfully."
