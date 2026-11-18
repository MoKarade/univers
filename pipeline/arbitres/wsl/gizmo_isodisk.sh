#!/bin/bash
# Compile GIZMO public : hydro MFM + gravité + refroidissement + formation d'étoiles ; essai sur le disque isolé (isodisk).
# Préalable (une fois) : cp ../gizmo/cooling/TREECOOL ~/arbitres/gizmo-essai/ ; ajouter à isodisk.params : CritPhysDensity 100, SfEffPerFreeFall 1.0, TimeLimitCPU 60
set -e
cd ~/arbitres/gizmo
printf 'HYDRO_MESHLESS_FINITE_MASS\nADAPTIVE_GRAVSOFT_FORGAS\nCOOLING\nGALSF\nOUTPUT_IN_DOUBLEPRECISION\n' > Config.sh
make clean > /dev/null 2>&1 || true
make -j8 > build.log 2>&1 || { grep -E " error" build.log | head; exit 1; }
cd ~/arbitres/gizmo-essai
cp ../gizmo/GIZMO .
sed -i 's/^Softening_Type5 .*/Softening_Type5                    0.05/; s/^Softening_Type5_MaxPhysLimit .*/Softening_Type5_MaxPhysLimit       0.05/' isodisk.params
grep Softening_Type5 isodisk.params
rm -rf output && mkdir output
timeout 100 mpirun -np 4 ./GIZMO isodisk.params 0 > run.log 2>&1 || echo "rc=$?"
grep -E "ERROR" run.log | head -5 || true
grep -E "Sync-Point" run.log | tail -1
tail -2 run.log
ls output
tail -2 output/sfr.txt
