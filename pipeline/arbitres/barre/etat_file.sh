date; echo "gadget en cours: $(pgrep -c -x Gadget4-barre)"
for d in ~/arbitres/barre-v16-halo ~/arbitres/file/*; do echo "== $d"; grep Sync-Point $d/run.log | tail -1 | cut -c1-50; grep -c "endrun called" $d/run.log; ls $d/mesures.json 2>/dev/null; stat -c %y $d/run.log; done
