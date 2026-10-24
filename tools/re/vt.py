import mmap,struct,numpy as np,sys
sys.path.insert(0,'/tmp')
import a64 as DIS
mm=DIS.mm
shoff,=struct.unpack_from('<Q',mm,0x28); shentsize,shnum,shstr=struct.unpack_from('<HHH',mm,0x3A)
secs=[struct.unpack_from('<IIQQQQIIQQ',mm,shoff+i*shentsize) for i in range(shnum)]
nm=mm[secs[shstr][4]:secs[shstr][4]+secs[shstr][5]]
S={nm[s[0]:nm.index(b'\0',s[0])].decode():(s[3],s[4],s[5]) for s in secs}
a,o,sz=S['.rela.dyn']
rel=np.frombuffer(mm[o:o+sz],dtype='<u8').reshape(-1,3)
rel=rel[rel[:,1]==1027]            # R_AARCH64_RELATIVE
order=np.argsort(rel[:,0]); rel=rel[order]
def slot(addr):
    i=np.searchsorted(rel[:,0],addr)
    return int(rel[i,2]) if i<len(rel) and rel[i,0]==addr else None
def vtable(va,n):
    return [slot(va+8*i) for i in range(n)]
def body(fn,maxn=10):
    d=DIS.D(); out=[]
    for k in range(maxn):
        pc=fn+4*k; w=struct.unpack_from('<I',mm,pc)[0]; t=d.dis(pc,w); out.append(f'    {pc:#x}: {t}')
        if t.startswith('ret') or t.startswith('b '): break
    return out
if __name__=='__main__':
    va=int(sys.argv[1],16); n=int(sys.argv[2])
    for i,fn in enumerate(vtable(va,n)):
        print(f'[{i}] slot {va+8*i:#x} -> {fn:#x}' if fn else f'[{i}] None')
        if fn: print('\n'.join(body(fn,int(sys.argv[3]) if len(sys.argv)>3 else 8)))
