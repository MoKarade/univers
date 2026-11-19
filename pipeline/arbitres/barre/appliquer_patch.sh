# Ajoute la barre guide à GADGET-4 (src/gravity/grav_external.cc) et déclare l'option. Idempotent.
set -e
cd ~/arbitres/gadget4
grep -q EXTERNALGRAVITY_GUIDEBAR src/gravity/grav_external.cc && { echo "déjà appliqué"; exit 0; }
python3 - <<'PY'
import os
p = 'src/gravity/grav_external.cc'
s = open(p).read()
bloc = open(os.path.expanduser('/mnt/c/dev/univers-arbitres/pipeline/arbitres/barre/guide_barre.patch.cc')).read()
ancre = '#endif\n    }\n}\n'
assert s.count(ancre) == 1
s = s.replace(ancre, '#endif\n' + bloc + '    }\n}\n')
open(p, 'w').write(s)
t = 'Template-Config.sh'
s = open(t).read()
s = s.replace('#EXTERNALGRAVITY_STATICHQ', '#EXTERNALGRAVITY_GUIDEBAR                     # rotating Long-Murali guide bar (Univers arbitration)\n#EXTERNALGRAVITY_STATICHQ', 1)
open(t, 'w').write(s)
d = 'documentation/04_config-options.md'
s = open(d).read()
s = s.replace('**EXTERNALGRAVITY_STATICHQ**', '**EXTERNALGRAVITY_GUIDEBAR**\n\nRotating Long-Murali guide bar used for the Univers arbitration run.\n\n-------\n\n**EXTERNALGRAVITY_STATICHQ**', 1)
open(d, 'w').write(s)
PY
git diff --stat
