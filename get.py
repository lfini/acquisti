#!/usr/bin/python3
'''
getdata.py - importa da sisifo un intero anno di dati o una singola pratica


Uso:
    python getdata.py anno [pratica]

'''

REMOTE = 'acquisti@sisifo'

import sys
import subprocess

if len(sys.argv) < 2 or '-h' in sys.argv:
    print('\nErrore argomenti\n')
    print(__doc__)
    sys.exit()

if len(sys.argv) == 2:
    fromdir = f'{REMOTE}:v5/data/{sys.argv[1]}'
    todir = 'data/'
else:
    prat = f'{sys.argv[1]}_{int(sys.argv[2]):06d}'
    fromdir = f'{REMOTE}:v5/data/{sys.argv[1]}/{prat}'
    todir = f'data/{sys.argv[1]}/'

cmd = ['rsync', '-vrpz', fromdir, todir]
print('Comando:', ' '.join(cmd))
subprocess.run(cmd)
