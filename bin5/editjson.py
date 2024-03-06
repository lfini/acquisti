"""
editjson.py

Finds json files whith given name and applies operations to the data.

Usage:

   python editjson.py <dir> <name> <op1> <op2> ...

   Example: python editjson.py . ugo.json "data[3]=7" "data.pop(0)"

   Note: the data structure read from JSON file is open with the name: data
         Usually the operations must be enclosed in quotes on the command line

"""


import os,sys
import json

def dodir(dd,nn,operations,dryrun):
    tree=os.walk('.')
    nn=nn.strip()
    for dp,dnames,fnames in tree:
        for fn in fnames:
            if fn != nn: continue
            path = os.path.join(dp,fn)
            with open(path) as fd:
                data=json.load(fd)
                errs=[]
                for op in operations:
                    stat=do_apply(data,op,dryrun)
                    if stat:
                        errs.append(stat)
            if errs:
                print("%d errors in file:" % len(errs),path)
                for e in errs:
                    print("  - ",e)
                a=input("OK to save [Y/N/Q]? ")
                a=a.upper()+' '
                if a[0]=='Q':
                    sys.exit()
                if a[0]=='Y' :
                    errs=[]
            if errs:
                print("Ignored file:",path)
            else:
                with open(path,'w') as fd:
                    json.dump(data,fd,indent=2)
                print("Done file",path)

def do_apply(data,op,dryrun):
    ret=''
    if dryrun:
        print("  Apply <",op,"> OK")
        return ret
    try:
        exec(op)
    except:
        ex=sys.exc_info()
        ret=str(ex[0])+': '+str(ex[1])
    return ret

def main():
    if len(sys.argv)<4:
        print(__doc__)
        sys.exit()
    if sys.argv[1]=='-n':
        if len(sys.argv)<5:
            print(__doc__)
            sys.exit()
        dryrun=True
        dd=sys.argv[2]
        nn=sys.argv[3]
        op=sys.argv[4:]
    else:
        dryrun=False
        dd=sys.argv[1]
        nn=sys.argv[2]
        op=sys.argv[3:]

    dodir(dd,nn,op,dryrun)


if __name__=='__main__': main()
