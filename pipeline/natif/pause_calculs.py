#!/usr/bin/env python3
"""Met en pause (suspend, sans tuer) ou reprend les calculs de fond du fil physique, pour laisser le PC à Marc quand il
joue. Rien n'est perdu : chaque processus reprend exactement où il était.
Processus visés (reconnus à leur ligne de commande) : calcul.py (fusion, Voie lactée seule), clones_etoiles.py et
precalcul_clones.exe (horizon des étoiles), chaos_systeme_solaire.exe.
Usage : python pause_calculs.py pause | reprise | etat
"""
import ctypes, subprocess, sys

MOTIFS = ('calcul.py', 'clones_etoiles.py', 'precalcul_clones', 'chaos_systeme_solaire')


def processus():
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
                          "Get-CimInstance Win32_Process | ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }"],
                         capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout
    res = []
    for l in out.splitlines():
        pid, _, cmd = l.partition('\t')
        if pid.strip().isdigit() and any(m in cmd for m in MOTIFS) and 'pause_calculs' not in cmd and 'bash.exe' not in cmd:
            res.append((int(pid), cmd.strip()[:120]))
    return res


def agir(pid, reprendre):
    ntdll, k32 = ctypes.WinDLL('ntdll'), ctypes.WinDLL('kernel32')
    h = k32.OpenProcess(0x0800, False, pid)      # PROCESS_SUSPEND_RESUME
    if not h: return False
    r = (ntdll.NtResumeProcess if reprendre else ntdll.NtSuspendProcess)(h)
    k32.CloseHandle(h)
    return r == 0


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'etat'
    for pid, cmd in processus():
        if action == 'etat': print(pid, cmd)
        else: print(('repris' if action == 'reprise' else 'en pause') if agir(pid, action == 'reprise') else 'ÉCHEC', pid, cmd)


if __name__ == '__main__':
    main()
