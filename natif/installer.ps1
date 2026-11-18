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
# Galaxies de forme mesurée (pipeline/natif/galaxies_formes.py) : leur fichier et le catalogue où leurs points sont marqués.
if (Test-Path "$Donnees\galaxies-formes\galaxies_formes.bin") { Copier-SiChange "$Donnees\galaxies-formes\galaxies_formes.bin" "$Cible\galaxies_formes.bin"; Copier-SiChange "$Donnees\galaxies-formes\galaxies.bin" "$Cible\galaxies.bin"; Copier-SiChange "$Donnees\galaxies-formes\galaxies_formes_noms.tsv" "$Cible\galaxies_formes_noms.tsv" } elseif (Test-Path "$Donnees\galaxies.bin") { Copier-SiChange "$Donnees\galaxies.bin" "$Cible\galaxies.bin" }
foreach ($f in 'etoiles.bin', 'etoiles.json', 'etoiles_noms.tsv', 'etoiles_sans_vr.txt', 'galaxies_noms.tsv', 'galaxies_cf4.tsv', 'ondes_gravitationnelles.tsv', 'chaos_futur_60ma.bin', 'gaia_tuiles.idx', 'gaia_tuiles_centres.bin', 'traceurs_bras.tsv', 'asteroides.bin', 'asteroides_noms.txt', 'planetes.tsv', 'lunes.tsv', 'orbites_planetes.bin', 'sondes.bin') { if (Test-Path "$Donnees\$f") { Copier-SiChange "$Donnees\$f" "$Cible\$f" } }
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
# Centres de référence des galaxies du Groupe local (pipeline/natif/centres_bin.py), s'ils ont été préparés.
if (Test-Path "$Donnees\vieillissement.tsv") { Copier-SiChange "$Donnees\vieillissement.tsv" "$Cible\vieillissement.tsv" }
if (Test-Path "$Donnees\centres_reference.bin") { Copier-SiChange "$Donnees\centres_reference.bin" "$Cible\centres_reference.bin" }
# Étoiles visibles du modèle de la Voie lactée (pipeline/natif/etoiles_visibles.py), si elles ont été préparées.
if (Test-Path "$Donnees\etoiles-visibles\voisines_etoiles.bin") { Copier-SiChange "$Donnees\etoiles-visibles\voisines_etoiles.bin" "$Cible\voisines_etoiles.bin" }
if (Test-Path "$Donnees\etoiles-visibles\vl_etoiles.bin") { Copier-SiChange "$Donnees\etoiles-visibles\vl_etoiles.bin" "$Cible\vl_etoiles.bin" }
# Film du Groupe local (natif/src/film_etoiles.h) : l'ordre des étoiles de l'appli dans le film, et le dossier du film
# (une ligne ; le film lui-même, des dizaines de Go, reste où le calcul l'écrit).
if (Test-Path "$Donnees\etoiles-visibles\vl_etoiles.ordre") { Copier-SiChange "$Donnees\etoiles-visibles\vl_etoiles.ordre" "$Cible\vl_etoiles.ordre" }
if (Test-Path "$Donnees\etoiles-visibles\voisines_etoiles.ordre") { Copier-SiChange "$Donnees\etoiles-visibles\voisines_etoiles.ordre" "$Cible\voisines_etoiles.ordre" }
# Lumière entière des étoiles visibles (pipeline/natif/ordre_film.py, revue F1) : Gaia cède au film loin d'aujourd'hui
if (Test-Path "$Donnees\etoiles-visibles\vl_etoiles.lum") { Copier-SiChange "$Donnees\etoiles-visibles\vl_etoiles.lum" "$Cible\vl_etoiles.lum" }
if (Test-Path "$Donnees\etoiles-visibles\voisines_etoiles.lum") { Copier-SiChange "$Donnees\etoiles-visibles\voisines_etoiles.lum" "$Cible\voisines_etoiles.lum" }
if (Test-Path "$Donnees\film_dossier.txt") { Copy-Item "$Donnees\film_dossier.txt" "$Cible\film_dossier.txt" -Force }
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
