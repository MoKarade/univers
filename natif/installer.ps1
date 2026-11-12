# Range l'appli PC « Univers » dans C:\dev\Univers-PC et pose un raccourci sur le Bureau.
# À lancer après la fabrication (natif/README.md) et la conversion des étoiles (pipeline/natif/etoiles.py).
# N'ouvre aucune fenêtre. Usage : pwsh natif/installer.ps1 [-Build C:\tmp\natif\build] [-Donnees C:\tmp\natif\donnees]
param([string]$Build = 'C:\tmp\natif\build', [string]$Donnees = 'C:\tmp\natif\donnees', [string]$Cible = 'C:\dev\Univers-PC')
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force $Cible, "$Cible\spv" | Out-Null
Copy-Item "$Build\univers.exe", "$Build\UniversPC.exe" $Cible -Force
Copy-Item "$Build\spv\etoiles.*.spv", "$Build\spv\ecran.*.spv" "$Cible\spv" -Force
Copy-Item "$Donnees\etoiles.bin", "$Donnees\etoiles.json" $Cible -Force
# Vue de départ : la ceinture d'Orion (étoile nommée de la page), si elle est dans le catalogue.
$meta = Get-Content "$Cible\etoiles.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$orion = $meta.nommees | Where-Object { $_.n -like 'Alnilam*' } | Select-Object -First 1
$regarde = if ($orion) { $orion.i } else { 0 }
$bureau = [Environment]::GetFolderPath('Desktop')
$lnk = (New-Object -ComObject WScript.Shell).CreateShortcut("$bureau\Univers PC.lnk")
$lnk.TargetPath = "$Cible\UniversPC.exe"
$lnk.Arguments = "`"$Cible\etoiles.bin`" --fenetre --regarde $regarde"
$lnk.WorkingDirectory = $Cible
$lnk.WindowStyle = 1      # fenêtre normale (UniversPC.exe n'a pas de console)
$lnk.Description = 'Univers : les étoiles de la page, sur le PC'
$lnk.Save()
"Installé dans $Cible ; raccourci : $bureau\Univers PC.lnk (vue de départ : étoile $regarde)"
