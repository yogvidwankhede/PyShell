$ErrorActionPreference = 'Stop'
$toolsDir = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$packageName = 'pyshell'
$url64 = 'https://github.com/yogvidwankhede/PyShell/releases/download/v1.1.0/pyshell.exe'

$packageArgs = @{
  packageName   = $packageName
  unzipLocation = $toolsDir
  fileType      = 'exe'
  url64bit      = $url64
  softwareName  = 'PyShell*'
  checksum64    = 'E6231EC02451A8FAB6AFA686FB64C44D0EBF733599D91ED9EA8A77B463C3AEA7'
  checksumType64= 'sha256'
  silentArgs    = "/S"
  validExitCodes= @(0)
}

Install-ChocolateyPackage @packageArgs

# Add to PATH
Install-ChocolateyPath "$toolsDir" 'User'