# Prépare un tir : compile GADGET-4 (gravité seule + barre guide), convertit le départ, écrit param.txt et sorties.txt.
# Usage : bash preparer.sh <dossier> <depart.npz> <durée Ga> <limite CPU s> [--sous-echantillon=N]
set -eo pipefail
D=$1; NPZ=$2; DUREE=$3; TLIM=$4; OPT=${5:-}
B=/mnt/c/dev/univers-arbitres/pipeline/arbitres/barre
export PATH=~/arbitres/bin:$PATH
cd ~/arbitres/gadget4
[ -x Gadget4-barre ] || make -j8 CONFIG=$B/Config.sh BUILD_DIR=build-barre EXEC=Gadget4-barre HDF5_INCL="-I/usr/include/hdf5/serial" HDF5_LIBS="-L/usr/lib/x86_64-linux-gnu/hdf5/serial -lhdf5 -lz" 2>&1 | tail -3
mkdir -p $D/output && cd $D
cp ~/arbitres/gadget4/Gadget4-barre .
python3 $B/npz_vers_gadget.py $NPZ depart.hdf5 $OPT
TMAX=$(python3 -c "print(round($DUREE/0.9778, 6))")
sed "s|__IC__|depart|; s|__TLIM__|$TLIM|; s|__TMAX__|$TMAX|" $B/param_modele.txt > param.txt
# Sorties : toutes les 50 Ma, plus une 10 Ma après chacune (vitesse de la barre sans ambiguïté de demi-tour)
python3 -c "
T=0.9778; n=int(round($DUREE/0.05))
ts=sorted(set([k*0.05/T for k in range(n+1)]+[(k*0.05+0.01)/T for k in range(n)]))
open('sorties.txt','w').write('\n'.join('%.8f'%t for t in ts)+'\n')"
wc -l sorties.txt
