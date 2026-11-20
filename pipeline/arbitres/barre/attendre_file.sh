while pgrep -f file_suite.sh > /dev/null; do sleep 60; done
for n in m31_temoin centre_v13_halo_tournant; do echo "== $n"; [ -f ~/arbitres/file/$n/mesures.json ] && python3 /mnt/c/dev/univers-arbitres/pipeline/arbitres/barre/bilan.py ~/arbitres/file/$n/mesures.json || echo absent; done
