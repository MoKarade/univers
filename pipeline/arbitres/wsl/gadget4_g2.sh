#!/bin/bash
# Compile et lance GADGET-4, exemple G2-galaxy (galaxie isolée sans collisions), 4 processus MPI, ~1 minute.
set -eo pipefail
mkdir -p ~/arbitres/bin && ln -sf /usr/bin/python3 ~/arbitres/bin/python; export PATH=~/arbitres/bin:$PATH
cd ~/arbitres/gadget4
echo "SYSTYPE=\"Generic-gcc\"" > Makefile.systype
H5I="-I/usr/include/hdf5/serial"
H5L="-L/usr/lib/x86_64-linux-gnu/hdf5/serial -lhdf5 -lz"
make -j8 CONFIG=examples/G2-galaxy/Config.sh BUILD_DIR=build-g2 EXEC=Gadget4-g2 HDF5_INCL="$H5I" HDF5_LIBS="$H5L" 2>&1 | tail -15
mkdir -p ~/arbitres/essai-g2 && cd ~/arbitres/essai-g2
cp ~/arbitres/gadget4/Gadget4-g2 . && cp ~/arbitres/gadget4/examples/G2-galaxy/param.txt .
sed -i "s|^InitCondFile.*|InitCondFile        $HOME/arbitres/ics/ExampleICs/galaxy_littleendian.dat|" param.txt
sed -i "s|^TimeLimitCPU.*|TimeLimitCPU        60|" param.txt
timeout 90 mpirun -np 4 ./Gadget4-g2 param.txt > run.log 2>&1 || echo "code retour $?"
grep -iE "This is Gadget|Code was compiled|Sync-Point|TimeLimitCPU|stopping|error|ENDRUN" run.log | head -5; grep "Sync-Point" run.log | tail -2; tail -5 run.log
ls output | head
