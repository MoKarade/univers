while pgrep -f file_m31_corrige.sh > /dev/null; do sleep 60; done
for n in m31_halo_tournant_v2 m31_temoin_v2; do echo "== $n"; [ -f ~/arbitres/file/$n/mesures.json ] && python3 /mnt/c/dev/univers-arbitres/pipeline/arbitres/barre/bilan.py ~/arbitres/file/$n/mesures.json || { echo absent; tail -3 ~/arbitres/file/$n/run.log; }; done
