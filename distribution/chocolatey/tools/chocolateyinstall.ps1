$ErrorActionPreference = 'Stop'

$toolsDir = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$packageName = 'pyshell'
$url64 = 'https://github.com/yogvidwankhede/PyShell/releases/download/v1.1.2/pyshell.exe'
$exePath = Join-Path $toolsDir 'pyshell.exe'

# Download the binary from GitHub
Get-ChocolateyWebFile -PackageName $packageName -FileFullPath $exePath -Url64bit $url64 `
  -Checksum 'E6231EC02451A8FAB6AFA686FB64C44D0EBF733599D91ED9EA8A77B463C3AEA7' `
  -ChecksumType 'sha256'

# Optionally add to PATH (for this user)
Install-ChocolateyPath "$toolsDir" 'User'

# Create a Start Menu shortcut
Install-ChocolateyShortcut -ShortcutFilePath "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\PyShell.lnk" -TargetPath $exePath

Write-Host "PyShell installed successfully! Launch it anytime by running 'pyshell.exe' in PowerShell or CMD."
