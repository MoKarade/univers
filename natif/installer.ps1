# Range l'appli PC « Univers » dans C:\dev\Univers-PC et pose un raccourci sur le Bureau.
# À lancer après la fabrication (natif/README.md) et la conversion des étoiles (pipeline/natif/etoiles.py).
# N'ouvre aucune fenêtre. Usage : pwsh natif/installer.ps1 [-Build C:\tmp\natif\build] [-Donnees C:\tmp\natif\donnees]
param([string]$Build = 'C:\tmp\natif\build', [string]$Donnees = 'C:\tmp\natif\donnees', [string]$Cible = 'C:\dev\Univers-PC', [string]$Ephem = 'C:\tmp\natif\nasa\de440.bsp')
$ErrorActionPreference = 'Stop'
function Copier-SiChange([string]$Source, [string]$Destination) {
    $src = Get-Item $Source
    $dst = Get-Item $Destination -ErrorAction SilentlyContinue
    if ($dst -and $dst.Length -eq $src.Length -and $dst.LastWriteTimeUtc -ge $src.LastWriteTimeUtc) { return }
    try { Copy-Item $src.FullName $Destination -Force }
    catch { "ATTENTION : $($src.Name) n'a pas pu être mis à jour (simulateur ouvert) : relancer l'installation après l'avoir fermé." }
}

New-Item -ItemType Directory -Force $Cible, "$Cible\spv" | Out-Null
# Si le simulateur est ouvert, Windows refuse d'écraser son programme mais accepte de le renommer : l'ancien est mis
# de côté (il continue de tourner), le nouveau prend sa place et servira au prochain lancement. On ne ferme jamais l'appli de Marc.
foreach ($exe in 'univers.exe', 'UniversPC.exe') {
    try { Copy-Item "$Build\$exe" $Cible -Force }
    catch {
        $old = "$Cible\$exe.ancien-" + (Get-Date -Format 'HHmmss')
        Rename-Item "$Cible\$exe" $old
        Copy-Item "$Build\$exe" $Cible -Force
    }
}
Get-ChildItem $Cible -Filter '*.ancien-*' | ForEach-Object { try { Remove-Item $_.FullName -Force } catch {} }      # anciens programmes qui ne tournent plus
Copy-Item "$Build\spv\*.spv" "$Cible\spv" -Force
# Cartes de surface (Solar System Scope, CC BY 4.0), rangées avec les données.
if (Test-Path "$Donnees\textures") { New-Item -ItemType Directory -Force "$Cible\textures" | Out-Null; Get-ChildItem "$Donnees\textures" -File | ForEach-Object { Copier-SiChange $_.FullName "$Cible\textures\$($_.Name)" } }
# Données : copiées seulement si elles ont changé (taille ou date). Un fichier inchangé que le simulateur ouvert
# tient en mémoire n'est donc pas touché ; un fichier changé et tenu ouvert est signalé, sans arrêter l'installation.
foreach ($f in 'etoiles.bin', 'etoiles.json', 'etoiles_noms.tsv', 'galaxies.bin', 'galaxies_noms.tsv', 'asteroides.bin', 'asteroides_noms.txt', 'planetes.tsv') { Copier-SiChange "$Donnees\$f" "$Cible\$f" }
# Éphémérides de la NASA (JPL DE440), téléchargées du NAIF : 114 Mo, lues telles quelles par le simulateur.
if (Test-Path "$Ephem") { Copier-SiChange "$Ephem" "$Cible\de440.bsp" }
# Vue de départ : la ceinture d'Orion (étoile nommée de la page), si elle est dans le catalogue.
$meta = Get-Content "$Cible\etoiles.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$orion = $meta.nommees | Where-Object { $_.n -like 'Alnilam*' } | Select-Object -First 1
$regarde = if ($orion) { $orion.i } else { 0 }
$bureau = [Environment]::GetFolderPath('Desktop')
$lnk = (New-Object -ComObject WScript.Shell).CreateShortcut("$bureau\Univers PC.lnk")
$lnk.TargetPath = "$Cible\UniversPC.exe"
$lnk.Arguments = ""      # sans argument : le simulateur, avec les étoiles rangées à côté du programme
$lnk.WorkingDirectory = $Cible
$lnk.WindowStyle = 1      # fenêtre normale (UniversPC.exe n'a pas de console)
$lnk.Description = 'Univers : les étoiles de la page, sur le PC'
$lnk.Save()
"Installé dans $Cible ; raccourci : $bureau\Univers PC.lnk (vue de départ : étoile $regarde)"
