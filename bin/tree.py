'''
tree.py - disegna albero decisioni

Uso: 
      python tree.py
'''

from collections import defaultdict
import pygraphviz as pgv

import constants as cs

def solvenext(nextstp):
    'individua step successivi'
    branches = defaultdict(list)
    if isinstance(nextstp, dict):
        for mode, nxt in nextstp.items():
            branches[nxt].append(mode)
    else:
        branches[nextstp] = '*'
    return branches

class Tree:
    def __init__(self):
        self.nodes = []
        self.links = []

    def __str__(self):
        ret = [f'{n}\n' for n in self.nodes]
        return '\n'.join(ret)

    def add_node(self, node):
        self.nodes.append(node)

    def makelinks(self):
        for node in self.nodes:
            for stp in node.nextstep:
                self.links.append([node.value, stp])

class Node:
    def __init__(self, key):
        self.ident = key
        self.name = cs.TABELLA_PASSI[key][0]
        fnm = cs.TABELLA_PASSI[key][1][:1]
        self.docname = fnm[0] if fnm else ''
        self.commands = ', '.join(cs.TABELLA_PASSI[key][2])
        self.allegati = ', '.join(cs.TABELLA_PASSI[key][3])
        _follows = cs.TABELLA_PASSI[key][4]
        self.follows = {'': _follows} if isinstance(_follows, cs.CdP) else _follows

    def __str__(self):
        return self.name

def mytree():
    intkeys = [int(v) for v in cs.CdP]
    intkeys.sort()
    tree = pgv.AGraph(directed=True, strict=False)
    for key in cs.CdP:
        node = Node(key)
        tree.add_node(node)
        for mod, nnext in node.follows.items():
            tree.add_edge(node, str(Node(nnext)), label=mod)
    return tree

if __name__ == '__main__':
    tree = mytree()
    tree.layout('dot')
    tree.draw('tree.png')
    print('Generato grafico: tree.png')

