# Reprise des tirs Andromède du 19/11 avec le bulbe et les adoucissements d'Andromède (conversion corrigée).
B=/mnt/c/dev/univers-arbitres/pipeline/arbitres/barre; G=/mnt/c/tmp/analyse-architecture/galaxies
CFG=Config_m31.sh bash $B/tir_complet.sh m31_halo_tournant_v2 $G/v16/andromede_barre_halo_tournant.npz --npz-sortie=/mnt/c/tmp/arbitres/andromede_1M_halo_tournant_corrige.npz
CFG=Config_m31.sh bash $B/tir_complet.sh m31_temoin_v2 $G/v16/andromede_barre.npz --npz-sortie=/mnt/c/tmp/arbitres/andromede_1M_temoin_corrige.npz
