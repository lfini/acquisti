#!/usr/bin/python3
'''
get.py - importa da sisifo un intero anno di dati o un range di date


Uso:
    python get.py anno [pratica1] [pratica2]

'''

import sys
import subprocess

REMOTE = 'acquisti@sisifo'

def execute(fromd, tod):
    'lancia comando rsync'
    cmd = ['rsync', '-vrpz', fromd, tod]
    print('Comando:', ' '.join(cmd))
    subprocess.run(cmd, check=True)

#pylint: disable=C0103
if '-h' in sys.argv:
    print(__doc__)
    sys.exit()
if len(sys.argv) < 2 or len(sys.argv) > 4:
    print('\nErrore argomenti\n')
    print(__doc__)
    sys.exit()

if len(sys.argv) == 2:
    fromdir = f'{REMOTE}:v5/data/{sys.argv[1]}'
    todir = 'data/'
    execute(fromdir, todir)
    sys.exit()
if len(sys.argv) == 3:
    prat = f'{sys.argv[1]}_{int(sys.argv[2]):06d}'
    fromdir = f'{REMOTE}:v5/data/{sys.argv[1]}/{prat}'
    todir = f'data/{sys.argv[1]}/'
    execute(fromdir, todir)
    sys.exit()

start = int(sys.argv[2])
try:
    end = int(sys.argv[3])+1
except ValueError:
    end = 1000000

for pratn in range(start, end):
    prat = f'{sys.argv[1]}_{pratn:06d}'
    fromdir = f'{REMOTE}:v5/data/{sys.argv[1]}/{prat}'
    todir = f'data/{sys.argv[1]}/'
    try:
        execute(fromdir, todir)
    except subprocess.CalledProcessError:
        print(f"Errore esecuzione rsync alla pratica: {prat}")
        break
