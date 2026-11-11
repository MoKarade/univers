import requests, json, re
out = {}
for name, cmd in [('Cérès', '1;'), ('Vesta', '4;'), ('Pallas', '2;'), ('Pluton', '999'), ('Éris', '136199;'), ('Sedna', '90377;'), ('Makémaké', '136472;'), ('Mars', '499'), ('Jupiter', '599'), ('Lune', '301')]:
    p = {'format': 'text', 'COMMAND': f"'{cmd}'", 'OBJ_DATA': "'NO'", 'MAKE_EPHEM': "'YES'", 'EPHEM_TYPE': "'VECTORS'", 'CENTER': "'500@399'" if name == 'Lune' else "'500@10'", 'START_TIME': "'2026-11-10'", 'STOP_TIME': "'2026-11-11'", 'STEP_SIZE': "'1 d'", 'REF_PLANE': "'ECLIPTIC'", 'REF_SYSTEM': "'ICRF'", 'VEC_TABLE': "'1'", 'OUT_UNITS': "'AU-D'", 'CSV_FORMAT': "'YES'"}
    try:
        t = requests.get('https://ssd.jpl.nasa.gov/api/horizons.api', params=p, timeout=60).text
        m = re.search(r'\$\$SOE\s*(.*?)\$\$EOE', t, re.S); row = m.group(1).strip().split('\n')[0].split(',')
        out[name] = {'jd': float(row[0]), 'pos': [float(row[2]), float(row[3]), float(row[4])]}
    except Exception as e:
        out[name] = {'err': str(e)[:100], 'txt': t[:200] if 't' in dir() else ''}
json.dump(out, open('test/horizons.json', 'w'), ensure_ascii=False); print({k: ('ok' if 'pos' in v else v) for k, v in out.items()})
