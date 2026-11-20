# Lance un script de la file des arbitres sous Ubuntu, détaché de la session Claude (processus à part, fenêtre cachée),
# avec son journal sur disque dans ~/arbitres/file/journaux/<nom>.log.
# Usage : pwsh -NoProfile -File lancer_detache.ps1 -Script file_m31_corrige.sh
param([Parameter(Mandatory = $true)][string]$Script)
$ErrorActionPreference = 'Stop'
$nom = [IO.Path]::GetFileNameWithoutExtension($Script)
$commande = "mkdir -p ~/arbitres/file/journaux && nohup bash /mnt/c/dev/univers-arbitres/pipeline/arbitres/barre/$Script > ~/arbitres/file/journaux/$nom.log 2>&1"
Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d', 'Ubuntu-24.04', '--', 'bash', '-lc', $commande) -WindowStyle Hidden
Write-Output "lancé détaché : $Script ; journal ~/arbitres/file/journaux/$nom.log"
