L=~/arbitres/file/m31_halo_tournant_v2/run.log; d=$(date +%s); t0=$(grep Sync-Point $L | tail -1 | sed 's/.*Time: \([0-9.e-]*\),.*/\1/')
sleep 900; t1=$(grep Sync-Point $L | tail -1 | sed 's/.*Time: \([0-9.e-]*\),.*/\1/')
python3 -c "r=($t1-$t0)/900; print(f'{($t1-$t0)*0.9778*1000:.0f} Ma en 15 min ; reste {(1.53406-$t1)/r/3600:.1f} h pour ce tir')"
