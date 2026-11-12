#!/usr/bin/env python3
"""Trajectoires réelles des sondes -> sondes.bin pour l'appli PC (étape E3).

Source : JPL Horizons (https://ssd.jpl.nasa.gov/api/horizons.api), trajectoires reconstruites puis prolongées par le
JPL. Pour chaque sonde : position et vitesse par rapport au Soleil (centre 500@10), écliptique J2000, km et km/s,
une valeur par jour, du premier jour disponible après le lancement jusqu'au dernier jour fourni avant 2100.
Rien n'est calculé ici : entre deux valeurs, l'appli interpole (polynôme d'Hermite sur position et vitesse).

Pendant un survol de planète la trajectoire tourne en quelques heures : autour de chaque survol (4 jours avant et après),
une valeur toutes les 10 minutes est ajoutée (mesuré : avec une valeur par jour, l'écart atteignait 168 000 km pour
Voyager 1 à Jupiter).

Sortie sondes.bin : « UNIVSON2 », nombre de sondes (entier 64 bits) ; puis pour chaque sonde : nom (32 octets, UTF-8,
complété par des zéros), nombre de tronçons (entier 64 bits) ; puis pour chaque tronçon (le premier couvre tout le vol,
les suivants sont les survols) : jour julien de la première valeur (réel 64 bits), pas en jours (réel 64 bits), nombre
de valeurs n (entier 64 bits), puis n × 6 réels 64 bits (x, y, z en km ; vx, vy, vz en km/s).
Usage : python sondes.py <dossier de sortie>
"""
import os, re, struct, sys, urllib.parse, urllib.request

# nom à l'écran, code Horizons, date de début demandée (le lendemain du lancement), date de fin demandée
SONDES = [('Voyager 1', '-31', '1977-09-06', '2100-01-01'), ('Voyager 2', '-32', '1977-08-21', '2100-01-01'),
          ('Pioneer 10', '-23', '1972-03-04', '2100-01-01'), ('Pioneer 11', '-24', '1973-04-07', '2100-01-01'),
          ('New Horizons', '-98', '2006-01-20', '2100-01-01')]
PAS_JOURS = 1
# Survols : jour julien du passage au plus près (dates publiées par la NASA, à la journée près ; la fenêtre est large).
SURVOLS = {'Voyager 1': [2443938.0, 2444556.5], 'Voyager 2': [2444064.5, 2444843.0, 2446455.2, 2447763.6], 'Pioneer 10': [2442021.5],
           'Pioneer 11': [2442385.5, 2444118.0], 'New Horizons': [2454160.0, 2457217.0]}


def demander(code, debut, fin, pas=None):
    q = {'format': 'text', 'COMMAND': f"'{code}'", 'OBJ_DATA': 'NO', 'MAKE_EPHEM': 'YES', 'EPHEM_TYPE': 'VECTORS', 'CENTER': "'500@10'",
         'REF_PLANE': 'ECLIPTIC', 'REF_SYSTEM': 'ICRF', 'OUT_UNITS': 'KM-S', 'VEC_TABLE': '2', 'CSV_FORMAT': 'YES',
         'START_TIME': f"'{debut}'", 'STOP_TIME': f"'{fin}'", 'STEP_SIZE': f"'{pas or str(PAS_JOURS) + 'd'}'"}
    return urllib.request.urlopen('https://ssd.jpl.nasa.gov/api/horizons.api?' + urllib.parse.urlencode(q), timeout=300).read().decode('utf-8', 'replace')


def lire(txt):
    m = re.search(r'\$\$SOE(.*?)\$\$EOE', txt, re.S)
    if not m: return None
    rows = []
    for line in m.group(1).strip().split('\n'):
        c = [x.strip() for x in line.split(',')]
        rows.append((float(c[0]), [float(x) for x in c[2:8]]))
    return rows


def main():
    sortie = sys.argv[1]
    blocs = []
    for nom, code, debut, fin in SONDES:
        txt = demander(code, debut, fin)
        rows = lire(txt)
        if rows is None:
            # Horizons refuse une plage qui dépasse sa trajectoire et dit jusqu'où elle va : on reprend ses bornes.
            a = re.search(r'prior to A\.D\. (\d{4}-[A-Z]{3}-\d{2})', txt); b = re.search(r'after A\.D\. (\d{4}-[A-Z]{3}-\d{2})', txt)
            if a: debut = a.group(1)
            if b: fin = b.group(1)
            rows = lire(demander(code, debut, fin))
        if not rows: raise SystemExit(f'{nom} : pas de trajectoire exploitable\n{txt[-600:]}')
        pas = rows[1][0] - rows[0][0]
        assert all(abs((rows[k + 1][0] - rows[k][0]) - pas) < 1e-6 for k in range(len(rows) - 1)), 'pas irrégulier'
        troncons = [(rows[0][0], pas, rows)]
        for jd in SURVOLS[nom]:
            dense = lire(demander(code, f'JD{jd - 4}', f'JD{jd + 4}', '10m'))
            if not dense: raise SystemExit(f'{nom} : survol du jour julien {jd} sans réponse')
            troncons.append((dense[0][0], dense[1][0] - dense[0][0], dense))
        blocs.append((nom, troncons))
        print(f'{nom:13s} : {len(rows)} jours, du jour julien {rows[0][0]} au {rows[-1][0]} ; {len(troncons) - 1} survols détaillés')
    with open(os.path.join(sortie, 'sondes.bin'), 'wb') as f:
        f.write(b'UNIVSON2' + struct.pack('<q', len(blocs)))
        for nom, troncons in blocs:
            f.write(nom.encode('utf-8').ljust(32, b'\0') + struct.pack('<q', len(troncons)))
            for jd0, pas, rows in troncons:
                f.write(struct.pack('<ddq', jd0, pas, len(rows)))
                for _, v in rows: f.write(struct.pack('<6d', *v))
    print(os.path.getsize(os.path.join(sortie, 'sondes.bin')) / 1e6, 'Mo')


if __name__ == '__main__':
    main()
