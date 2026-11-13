# Range l'appli PC « Univers » dans C:\dev\Univers-PC et pose un raccourci sur le Bureau.
# À lancer après la fabrication (natif/README.md) et la conversion des étoiles (pipeline/natif/etoiles.py).
# N'ouvre aucune fenêtre. Usage : pwsh natif/installer.ps1 [-Build C:\tmp\natif\build] [-Donnees C:\tmp\natif\donnees]
param([string]$Build = 'C:\tmp\natif\build', [string]$Donnees = 'C:\tmp\natif\donnees', [string]$Cible = 'C:\dev\Univers-PC', [string]$Ephem = 'C:\tmp\natif\nasa\de440.bsp', [string]$Gaia = 'C:\tmp\natif\gaia')
$ErrorActionPreference = 'Stop'
function Copier-SiChange([string]$Source, [string]$Destination) {
    $src = Get-Item $Source
    $dst = Get-Item $Destination -ErrorAction SilentlyContinue
    if ($dst -and $dst.Length -eq $src.Length -and $dst.LastWriteTimeUtc -ge $src.LastWriteTimeUtc) { return }
    # Lien dur plutôt que copie (même disque) : une seule fois la place sur le disque (Marc, 12/11/2026 : garder de la place).
    $tmp = "$Destination.lien"
    try {
        if (Test-Path $tmp) { Remove-Item $tmp -Force }
        try { New-Item -ItemType HardLink -Path $tmp -Target $src.FullName -ErrorAction Stop | Out-Null; Move-Item $tmp $Destination -Force }
        catch { if (Test-Path $tmp) { Remove-Item $tmp -Force }; Copy-Item $src.FullName $Destination -Force }
    }
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
foreach ($f in 'etoiles.bin', 'etoiles.json', 'etoiles_noms.tsv', 'etoiles_sans_vr.txt', 'galaxies.bin', 'galaxies_noms.tsv', 'galaxies_cf4.tsv', 'ondes_gravitationnelles.tsv', 'chaos_futur_60ma.bin', 'gaia_tuiles.idx', 'gaia_tuiles_centres.bin', 'traceurs_bras.tsv', 'asteroides.bin', 'asteroides_noms.txt', 'planetes.tsv', 'lunes.tsv', 'orbites_planetes.bin', 'sondes.bin') { if (Test-Path "$Donnees\$f") { Copier-SiChange "$Donnees\$f" "$Cible\$f" } }
# Éphémérides de la NASA (JPL DE440), téléchargées du NAIF : 114 Mo, lues telles quelles par le simulateur.
if (Test-Path "$Ephem") { Copier-SiChange "$Ephem" "$Cible\de440.bsp" }
# Éphémérides des lunes (NAIF), si elles ont été téléchargées à côté de celles des planètes.
foreach ($f in 'mar099s.bsp', 'jup365.bsp', 'sat441.bsp', 'nep097.bsp', 'plu060.bsp', 'ura184_part-3.bsp', 'ura116xl.bsp', 'sat415.bsp', 'nep104.bsp', 'nep105.bsp', 'jup347.bsp', 'jup348.bsp', 'jup349.bsp', 'sat455.bsp', 'sat456.bsp', 'sat457.bsp', 'sat459.bsp') {
    $src = Join-Path (Split-Path $Ephem) $f
    if (Test-Path $src) { Copier-SiChange $src "$Cible\$f" }
}
# Calcul de la fusion avec Andromède (centres des galaxies, traceurs, étoiles affichées), s'il est là.
if (Test-Path "$Donnees\fusion-toutes\fusion_centres.bin") { New-Item -ItemType Directory -Force "$Cible\fusion-toutes" | Out-Null; Get-ChildItem "$Donnees\fusion-toutes" -File | Where-Object { $_.Extension -ne '.npz' } | ForEach-Object { Copier-SiChange $_.FullName "$Cible\fusion-toutes\$($_.Name)" } }
if (Test-Path "$Donnees\voie-lactee-seule\fusion_centres.bin") { New-Item -ItemType Directory -Force "$Cible\voie-lactee-seule" | Out-Null; Get-ChildItem "$Donnees\voie-lactee-seule" -File | Where-Object { $_.Extension -ne '.npz' } | ForEach-Object { Copier-SiChange $_.FullName "$Cible\voie-lactee-seule\$($_.Name)" } }
if (Test-Path "$Donnees\fusion-3m") { New-Item -ItemType Directory -Force "$Cible\fusion-3m" | Out-Null; Get-ChildItem "$Donnees\fusion-3m" -File | ForEach-Object { Copier-SiChange $_.FullName "$Cible\fusion-3m\$($_.Name)" } }
if (Test-Path "$Donnees\clones_groupe_local.bin") { Copier-SiChange "$Donnees\clones_groupe_local.bin" "$Cible\clones_groupe_local.bin" }
New-Item -ItemType Directory -Force "$Cible\avancement" | Out-Null      # les calculs de fond y écrivent où ils en sont
if (Test-Path "$Donnees\fusion") { New-Item -ItemType Directory -Force "$Cible\fusion" | Out-Null; Get-ChildItem "$Donnees\fusion" -File | ForEach-Object { Copier-SiChange $_.FullName "$Cible\fusion\$($_.Name)" } }
# Étoiles Gaia et Voie lactée (fil « Voie lactée et étoiles Gaia »), si les fichiers ont été préparés.
Get-ChildItem "$Donnees\ciel_*.bin", "$Donnees\sources_*.bin" -ErrorAction SilentlyContinue | ForEach-Object { Copier-SiChange $_.FullName "$Cible\$($_.Name)" }      # cartes du ciel dans d'autres lumières
# Tuiles fines des cartes, lues en flux sur le Drive : seuls le chemin (tuiles_dossier.txt) et les index restent sur le PC.
if (Test-Path "$Donnees\tuiles_dossier.txt") { Copier-SiChange "$Donnees\tuiles_dossier.txt" "$Cible\tuiles_dossier.txt" }
Get-ChildItem "$Donnees\tuiles" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    New-Item -ItemType Directory -Force "$Cible\tuiles\$($_.Name)" | Out-Null
    Get-ChildItem $_.FullName -Filter *.idx -File | ForEach-Object { Copier-SiChange $_.FullName "$Cible\tuiles\$($_.Directory.Name)\$($_.Name)" }
}
# Vraies photos des galaxies voisines (pipeline/natif/galaxies_images.py), si elles ont été préparées.
if (Test-Path "$Donnees\galaxies-images\galaxies_images.tsv") { Get-ChildItem "$Donnees\galaxies-images" -File | ForEach-Object { Copier-SiChange $_.FullName "$Cible\$($_.Name)" } }
foreach ($f in 'gaia.bin', 'gaia_b.bin', 'gaia_agrege.bin', 'voie_lactee.bin') { if (Test-Path "$Gaia\$f") { Copier-SiChange "$Gaia\$f" "$Cible\$f" } }
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
