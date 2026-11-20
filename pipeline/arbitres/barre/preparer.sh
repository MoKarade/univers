# Prépare un tir : compile GADGET-4 (gravité seule + barre guide), convertit le départ, écrit param.txt et sorties.txt.
# Usage : [CFG=Config_m31.sh] bash preparer.sh <dossier> <depart.npz> <durée Ga> <limite CPU s> [--sous-echantillon=N] [--halo-tourne=f]
# CFG : Config.sh (barre guide de la Voie lactée, par défaut) ou Config_m31.sh (barre guide d'Andromède).
set -eo pipefail
D=$1; NPZ=$2; DUREE=$3; TLIM=$4; shift 4; OPT="$*"
B=/mnt/c/dev/univers-arbitres/pipeline/arbitres/barre
CFG=${CFG:-Config.sh}; EXE=Gadget4-${CFG%.sh}
export PATH=~/arbitres/bin:$PATH
cd ~/arbitres/gadget4
make -j8 CONFIG=$B/$CFG BUILD_DIR=build-${CFG%.sh} EXEC=$EXE HDF5_INCL="-I/usr/include/hdf5/serial" HDF5_LIBS="-L/usr/lib/x86_64-linux-gnu/hdf5/serial -lhdf5 -lz" 2>&1 | tail -1
mkdir -p $D/output && cd $D
cp ~/arbitres/gadget4/$EXE Gadget4-barre
python3 $B/npz_vers_gadget.py $NPZ depart.hdf5 $OPT
TMAX=$(python3 -c "print(round($DUREE/0.9778, 6))")
sed "s|__IC__|depart|; s|__TLIM__|$TLIM|; s|__TMAX__|$TMAX|" $B/param_modele.txt > param.txt
# Adoucissements : ceux du .npz, un par type (adoucissements.txt écrit par la conversion), remplacent ceux du modèle
python3 - <<'PY'
e = dict(l.split() for l in open('adoucissements.txt'))
defaut = min(e.values(), key=float)
lignes = [l for l in open('param.txt') if not l.startswith('Softening')]
for t in range(6):
    lignes.append(f'SofteningComovingClass{t}     {e.get(str(t), defaut)}' + chr(10))
    lignes.append(f'SofteningMaxPhysClass{t}      {e.get(str(t), defaut)}' + chr(10))
    lignes.append(f'SofteningClassOfPartType{t}    {t}' + chr(10))
open('param.txt', 'w').writelines(lignes)
PY
grep -E "^SofteningComoving" param.txt
# Sorties : toutes les 50 Ma, plus une 10 Ma après chacune (vitesse de la barre sans ambiguïté de demi-tour)
python3 -c "
T=0.9778; n=int(round($DUREE/0.05))
ts=sorted(set([k*0.05/T for k in range(n+1)]+[(k*0.05+0.01)/T for k in range(n)]))
open('sorties.txt','w').write('\n'.join('%.8f'%t for t in ts)+'\n')"
wc -l sorties.txt
