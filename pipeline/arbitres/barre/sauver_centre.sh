# Arrête le doublon du tir centre (relancé par erreur à 14 h 14) et regroupe les instantanés du premier tir complet.
kill 18936 19927 19958 2>/dev/null; kill 42954 2>/dev/null
for i in $(seq 1 30); do pgrep -x Gadget4-barre > /dev/null || break; sleep 2; done
echo "gadget restants : $(pgrep -c -x Gadget4-barre)"
D=~/arbitres/file/centre_v13_halo_tournant; P=$D/premier_tir; mkdir -p $P
cd $D/output
for f in bak-snapshot_*.hdf5; do ln -f $f $P/${f#bak-}; done
for i in $(seq 24 60); do f=$(printf snapshot_%03d.hdf5 $i); ln -f $f $P/$f; done
ls $P | wc -l
