# Veilleur du grand calcul du Groupe local. A lancer dans un terminal, une fois :
#   & C:\tmp\analyse-architecture\univers\pipeline\fusion\veilleur_calcul.ps1
# Il attend que la carte graphique soit libre (pas de jeu, pas d'appli Univers ouverte), lance le calcul, et le relance
# depuis sa derniere sauvegarde chaque fois qu'il s'est retire pour laisser la carte. Il s'arrete quand le film est fini.
# N'ouvre aucune fenetre. Arret : Ctrl-C dans ce terminal.
param([string]$sortie = 'C:/tmp/natif/groupe-local', [string]$galaxies = '', [string]$traceurs = '', [string]$contrat = '', [string]$voisines = '', [string]$etat = '', [string]$fin = '', [switch]$gaz, [string]$gazMode = '', [string]$maree = '', [string]$efficacite = '', [string]$film = '', [string]$gaia = '', [string]$naines = '', [string]$centraux = '', [string]$pasRencontre = '', [string]$sauvegarde = '')
if ($pasRencontre) { $env:UNIVERS_PAS_RENCONTRE_MA = $pasRencontre }      # pas de gravite pendant les rencontres (Ma), rencontre.py
if ($sauvegarde) { $env:UNIVERS_SAUVEGARDE_MA = $sauvegarde }
if ($efficacite) { $env:UNIVERS_EFFICACITE = $efficacite }
if ($film) { $env:UNIVERS_FILM = $film }
if ($gaia) { $env:UNIVERS_GAIA = $gaia }
if ($naines) { $env:UNIVERS_NAINES = $naines }
if ($centraux) { $env:UNIVERS_CENTRAUX = $centraux }
if ($gazMode) { $env:UNIVERS_GAZ = $gazMode }
if ($maree) { $env:UNIVERS_MAREE = $maree }
if ($voisines) { $env:UNIVERS_CONTRATS_VOISINES = $voisines }
if ($etat) { $env:UNIVERS_ETAT = $etat }
if ($fin) { $env:UNIVERS_FIN_GA = $fin }
if ($gaz) { $env:UNIVERS_GAZ = '1' }
if ($contrat) { $env:UNIVERS_CONTRAT = $contrat }
if ($traceurs) { $env:UNIVERS_TRACEURS = $traceurs }
if ($galaxies) { $env:UNIVERS_GALAXIES = $galaxies }
$bash = 'C:\Program Files\Git\bin\bash.exe'
$lanceur = 'C:/tmp/analyse-architecture/univers/pipeline/fusion/lancer_rencontre.sh'
$env:UNIVERS_CEDER = '1'

function Carte-Libre {
    # Libre = aucun programme de Marc sur la carte (jeu, appli Univers) : même règle que le calcul (carte.py). Le taux
    # d'occupation ne sert plus : le bureau seul le fait varier de 20 à 40 %.
    & C:/tmp/venv-cupy/Scripts/python.exe (Join-Path $PSScriptRoot "carte.py") *> $null
    return ($LASTEXITCODE -eq 0)
}

while ($true) {
    if (Select-String -Path "$sortie/journal.txt" -Pattern 'film termin' -Quiet -ErrorAction SilentlyContinue) { Write-Host "$(Get-Date -Format 'dd/MM HH:mm') film termine : le veilleur s'arrete."; break }
    $libre = 0
    while ($libre -lt 3) {      # trois minutes de suite de carte libre
        if (Carte-Libre) { $libre++ } else { $libre = 0 }
        Start-Sleep -Seconds 60
    }
    Write-Host "$(Get-Date -Format 'dd/MM HH:mm') carte libre : le calcul repart de sa derniere sauvegarde."
    Remove-Item "$sortie/lanceur.pid" -ErrorAction SilentlyContinue      # ce veilleur est le seul a lancer le calcul : un verrou reste d'un arret est perime
    & $bash $lanceur $sortie
    if ($LASTEXITCODE -eq 4) { Write-Host "$(Get-Date -Format 'dd/MM HH:mm') reprise refusee : le code n'est plus celui du film (voir journal.txt et film/code.json). Le veilleur s'arrete."; break }
    Write-Host "$(Get-Date -Format 'dd/MM HH:mm') le calcul s'est arrete (carte prise, ou fin). Attente."
}
