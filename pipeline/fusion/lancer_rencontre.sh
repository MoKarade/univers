#!/usr/bin/env bash
# Lance le grand calcul du Groupe local (plan B+) en deux temps, sans fenêtre, et le reprend s'il a été coupé :
#   1. « passe » : d'il y a 1 Ga à aujourd'hui, à pleine finesse ; contrôle de l'arrivée ;
#   2. « futur » : d'aujourd'hui à +10 Ga, avec les étoiles visibles ; écrit le film.
# Usage : bash lancer_rencontre.sh [dossier de sortie]      (relancer la même commande reprend là où le calcul s'est arrêté)
# Le calcul se met en pause tout seul quand un autre programme occupe la carte graphique (l'appli de Marc, un jeu).
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
PY=/c/tmp/venv-cupy/Scripts/python.exe
G=C:/tmp/analyse-architecture/galaxies
GAL="${UNIVERS_GALAXIES:-$G/plein}"      # dossier des cinq galaxies de départ
TR="${UNIVERS_TRACEURS:-C:/tmp/natif/donnees/etoiles-visibles}"      # dossier des étoiles visibles
S="${1:-C:/tmp/natif/groupe-local}"
export PYTHONIOENCODING=utf-8 UNIVERS_AVANCEMENT=C:/dev/Univers-PC/avancement
mkdir -p "$S"
cd "$ICI" || exit 1
VERROU="$S/lanceur.pid"
if [ -f "$VERROU" ] && kill -0 "$(cat "$VERROU")" 2>/dev/null; then echo "déjà en cours (processus $(cat "$VERROU"))"; exit 0; fi
echo $$ > "$VERROU"

if [ ! -f "$S/aujourdhui.npz" ]; then
  echo "=== passe : d'il y a 1 Ga à aujourd'hui ($(date '+%d/%m %H:%M'))" >> "$S/journal.txt"
  if [ ! -f "$S/angles.txt" ]; then
    # Premier passage : sert à savoir où pointe la barre de la masse aujourd'hui, pour la caler sur la barre mesurée.
    if [ ! -f "$S/passage1.npz" ]; then
      "$PY" -u rencontre.py passe "$GAL" "$S" --etat="$G/etat_combine.json" --releve-ma=50 >> "$S/journal.txt" 2>&1 || { echo "ECHEC du passe" >> "$S/journal.txt"; exit 1; }
      mv "$S/aujourdhui.npz" "$S/passage1.npz"
    fi
    cp "$S/passage1.npz" "$S/aujourdhui.npz"
    "$PY" -u rencontre.py barre "$S" --traceurs="$TR" >> "$S/journal.txt" 2>&1 || { echo "ECHEC de la mesure de la barre" >> "$S/journal.txt"; exit 1; }
    rm -f "$S/aujourdhui.npz" "$S/reprise.npz"
    "$PY" -c "import json,sys; b=json.load(open(sys.argv[1]+'/barre.json',encoding='utf-8')); print(','.join(f\"{n}:{v['tourner_de']}\" for n,v in b.items()))" "$S" > "$S/angles.txt"
    mv "$S/barre.json" "$S/barre_passage1.json"
  fi
  echo "=== passe avec la barre calée : $(cat "$S/angles.txt") ($(date '+%d/%m %H:%M'))" >> "$S/journal.txt"
  "$PY" -u rencontre.py passe "$GAL" "$S" --etat="$G/etat_combine.json" --releve-ma=50 --angles="$(cat "$S/angles.txt")" >> "$S/journal.txt" 2>&1 || { echo "ECHEC du passe" >> "$S/journal.txt"; exit 1; }
  "$PY" -u rencontre.py barre "$S" --traceurs="$TR" >> "$S/journal.txt" 2>&1
fi
# Contrôle de l'arrivée : on ne continue que si chaque galaxie est assez près de sa place mesurée.
"$PY" - "$S" >> "$S/journal.txt" 2>&1 <<'EOF' || { echo "ARRÊT : arrivée trop loin des mesures, le futur n'est pas lancé" >> "$S/journal.txt"; exit 2; }
import json, sys
e = json.load(open(sys.argv[1] + '/etat_corrige.json', encoding='utf-8'))['ecart_du_tir']
limites = dict(andromede=10, triangle=10, grand_nuage=12, petit_nuage=25)      # kpc
ok = all(e[n]['distance_kpc'] <= limites[n] for n in limites)
print('arrivée :', {n: (e[n]['distance_kpc'], e[n]['vitesse_kms']) for n in limites}, '->', 'bonne' if ok else 'TROP LOIN')
sys.exit(0 if ok else 1)
EOF
echo "=== futur : d'aujourd'hui à +10 Ga ($(date '+%d/%m %H:%M'))" >> "$S/journal.txt"
"$PY" -u rencontre.py futur "$S" 10.0 --traceurs="$TR" --releve-ma=10 --champ=2 >> "$S/journal.txt" 2>&1
echo "=== fin ($(date '+%d/%m %H:%M')), code $?" >> "$S/journal.txt"
rm -f "$VERROU"
