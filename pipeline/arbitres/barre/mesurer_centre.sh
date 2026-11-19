D=~/arbitres/file/centre_v13_halo_tournant; B=/mnt/c/dev/univers-arbitres/pipeline/arbitres/barre
ls -la --time-style=+%H:%M $D/premier_tir | awk 'NR>1{print $6}' | sort | uniq -c | sort -k2 | head -3; ls -la --time-style=+%H:%M $D/premier_tir | awk 'NR>1{print $6}' | sort | tail -1
cd $D && nice -n 15 python3 $B/mesurer.py premier_tir mesures.json > mesures.log 2>&1 && cp mesures.json $B/mesures_centre_v13_halo_tournant.json && python3 $B/bilan.py mesures.json
echo "gadget : $(pgrep -c -x Gadget4-barre)"; ls ~/arbitres/file/
