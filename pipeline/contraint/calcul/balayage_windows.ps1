# Balayage des graines, côté Windows : fabrique les départs contraints (vitesses CF4 + densité 2MRS) graine par graine.
# Le côté WSL (balayage_wsl.sh) les prend au fur et à mesure et lance GADGET-4.
# Pause : tant que le jeu de Marc (cod.exe) tourne, on n'en fabrique pas de nouveau et on pose resultats\pause.txt.
# Usage : & .\pipeline\contraint\calcul\balayage_windows.ps1 PREMIERE DERNIERE
param([int]$Premiere = 2, [int]$Derniere = 21, [string]$Prefixe = 'rcj')
$ErrorActionPreference = 'Stop'
$dossier = Split-Path -Parent $PSScriptRoot
Set-Location $dossier
# Le venv et les données brutes ont été créés depuis l'appli Claude, dont AppData\Local est redirigé (paquet MSIX) :
# hors de l'appli, ils sont sous Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local. [Certain, constaté le 19/11]
$redirige = 'C:\Users\marcr\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local'
if (-not (Test-Path (Join-Path $env:LOCALAPPDATA 'univers-venv')) -and (Test-Path (Join-Path $redirige 'univers-venv'))) {
    $env:LOCALAPPDATA = $redirige
}
$python = Join-Path $env:LOCALAPPDATA 'univers-venv\Scripts\python.exe'
$env:PYTHONIOENCODING = 'utf-8'
$env:MONOPOLE = '1'; $env:PAS_D = '4'; $env:R_D = '40'; $env:SIGMA_D = '0.25'; $env:PREFIXE = 'rcj'          # nom des fichiers de realisations_jointes (toujours rcj_<g>.npz)
# Vierge imposée (δ_L = 1,8 dans 13 Mpc/h) : mesuré le 19/11, sans elle aucun amas ne se forme ; avec, rcv1 donne
# 1,3e15 M☉ à 5,3 Mpc de sa place (mesure : ~1,2e15).
$env:VIERGE_DL = '1.8'
New-Item -ItemType Directory -Force 'resultats' | Out-Null
for ($g = $Premiere; $g -le $Derniere; $g++) {
    while (Get-Process -Name 'cod' -ErrorAction SilentlyContinue) {
        Set-Content 'resultats\pause.txt' 'jeu en cours'
        Start-Sleep -Seconds 60
    }
    Remove-Item 'resultats\pause.txt' -ErrorAction SilentlyContinue
    # au plus 3 départs d'avance sur le côté WSL (place sur le disque)
    while ((Get-ChildItem "resultats\${Prefixe}_*_genetic_128.npy" -ErrorAction SilentlyContinue).Count -ge 3) { Start-Sleep -Seconds 30 }
    $sortie = "resultats\${Prefixe}_${g}_genetic_128.npy"
    if (Test-Path $sortie) { continue }
    & $python realisations_jointes.py $g | Out-File -Append -Encoding utf8 'resultats\balayage_windows.log'
    & $python exporter_genetic.py $g 128 | Out-File -Append -Encoding utf8 'resultats\balayage_windows.log'
    if ($Prefixe -ne 'rcj') { Move-Item -Force "resultats\rcj_${g}_genetic_128.npy" $sortie }
    Remove-Item "resultats\rcj_${g}.npz" -ErrorAction SilentlyContinue     # refaisable à l'identique depuis la graine
    "$(Get-Date -Format s) graine $g prête" | Out-File -Append -Encoding utf8 'resultats\balayage_windows.log'
}
"$(Get-Date -Format s) fini $Premiere..$Derniere" | Out-File -Append -Encoding utf8 'resultats\balayage_windows.log'
