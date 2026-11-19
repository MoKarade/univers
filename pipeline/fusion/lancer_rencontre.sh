#!/usr/bin/env bash
# Lance le grand calcul du Groupe local (plan B+) en deux temps, sans fenêtre, et le reprend s'il a été coupé :
#   1. « passe » : d'il y a 1 Ga à aujourd'hui, à pleine finesse ; contrôle de l'arrivée ;
#   (si UNIVERS_CONTRAT est donné : plan du disque calé et étoiles visibles de la Voie lactée tirées de la masse)
#   2. « futur » : d'aujourd'hui à +10 Ga, avec les étoiles visibles ; écrit le film.
# Usage : bash lancer_rencontre.sh [dossier de sortie]      (relancer la même commande reprend là où le calcul s'est arrêté)
# Le calcul se met en pause tout seul quand un autre programme occupe la carte graphique (l'appli de Marc, un jeu).
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
PY=/c/tmp/venv-cupy/Scripts/python.exe
PYU="$PY"      # même python que les calculs : celui de AppData\Local est invisible depuis le terminal de l'appli Claude (dossier virtualisé, constaté le 19/11)
G=C:/tmp/analyse-architecture/galaxies
GAL="${UNIVERS_GALAXIES:-$G/plein}"      # dossier des cinq galaxies de départ
ETAT="${UNIVERS_ETAT:-$G/etat_combine.json}"      # places et vitesses de départ des cinq galaxies (sortie des tirs de réglage)
GAZ=""; [ "${UNIVERS_GAZ:-0}" = "1" ] && GAZ="--gaz=1"      # gaz, naissances d'étoiles, retour de masse (gaz_galaxie.py)
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
      "$PY" -u rencontre.py passe "$GAL" "$S" --etat="$ETAT" $GAZ --releve-ma=50 >> "$S/journal.txt" 2>&1 || { echo "ECHEC du passe" >> "$S/journal.txt"; exit 1; }
      mv "$S/aujourdhui.npz" "$S/passage1.npz"
    fi
    cp "$S/passage1.npz" "$S/aujourdhui.npz"
    "$PY" -u rencontre.py barre "$S" --traceurs="$TR" >> "$S/journal.txt" 2>&1 || { echo "ECHEC de la mesure de la barre" >> "$S/journal.txt"; exit 1; }
    rm -f "$S/aujourdhui.npz" "$S/reprise.npz"
    "$PY" -c "import json,sys; b=json.load(open(sys.argv[1]+'/barre.json',encoding='utf-8')); print(','.join(f\"{n}:{v['tourner_de']}\" for n,v in b.items()))" "$S" > "$S/angles.txt"
    mv "$S/barre.json" "$S/barre_passage1.json"
  fi
  echo "=== passe avec la barre calée : $(cat "$S/angles.txt") ($(date '+%d/%m %H:%M'))" >> "$S/journal.txt"
  "$PY" -u rencontre.py passe "$GAL" "$S" --etat="$ETAT" $GAZ --releve-ma=50 --angles="$(cat "$S/angles.txt")" >> "$S/journal.txt" 2>&1 || { echo "ECHEC du passe" >> "$S/journal.txt"; exit 1; }
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
# Plan du disque de la Voie lactée remis sur le plan mesuré (caler_plan.py), puis étoiles visibles de la Voie lactée tirées de
# la masse du calcul (pipeline/natif/etoiles_visibles_masse.py) : le film part ainsi d'un état du calcul, sans sursaut.
if [ -n "${UNIVERS_CONTRAT:-}" ]; then
  if [ ! -f "$S/aujourdhui_brut.npz" ]; then
    "$PY" -u caler_plan.py "$S" >> "$S/journal.txt" 2>&1 || { echo "ECHEC du calage du plan" >> "$S/journal.txt"; exit 1; }
  fi
  if [ ! -f "$S/etoiles/vl_etoiles.bin" ]; then
    mkdir -p "$S/etoiles"
    "$PYU" ../natif/etoiles_visibles_masse.py "$UNIVERS_CONTRAT" "$S/aujourdhui.npz" C:/tmp/natif/gaia/gaia.bin,C:/tmp/natif/gaia/gaia_b.bin C:/tmp/natif/donnees/etoiles.bin C:/tmp/natif/gaia/gaia_agrege.bin "$S/etoiles" >> "$S/journal.txt" 2>&1 || { echo "ECHEC des étoiles visibles" >> "$S/journal.txt"; exit 1; }
    if [ -n "${UNIVERS_CONTRATS_VOISINES:-}" ]; then      # voisines posées sur leur masse aussi (etoiles_visibles_voisines_masse.py)
      "$PYU" ../natif/etoiles_visibles_voisines_masse.py "$UNIVERS_CONTRATS_VOISINES" "$S/aujourdhui.npz" "$GAL" "$S/etoiles" >> "$S/journal.txt" 2>&1 || { echo "ECHEC des étoiles visibles des voisines" >> "$S/journal.txt"; exit 1; }
    else
      for n in andromede triangle grand_nuage petit_nuage; do cp "$TR/etoiles_visibles_$n.npz" "$S/etoiles/"; done
    fi
  fi
  TR="$S/etoiles"
fi
echo "=== futur : d'aujourd'hui à +10 Ga ($(date '+%d/%m %H:%M'))" >> "$S/journal.txt"
"$PY" -u rencontre.py futur "$S" "${UNIVERS_FIN_GA:-10.0}" $GAZ --traceurs="$TR" --releve-ma=10 --champ=2 >> "$S/journal.txt" 2>&1
echo "=== fin ($(date '+%d/%m %H:%M')), code $?" >> "$S/journal.txt"
rm -f "$VERROU"
