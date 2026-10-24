import sys,struct,numpy as np
sys.path.insert(0,'/tmp')
import a64
mm=a64.mm
ta=to=0x64c63c0; ts=0xc44aa6c
words=np.frombuffer(mm[to:to+ts],dtype='<u4')
# function starts from eh_frame_hdr
shoff,=struct.unpack_from('<Q',mm,0x28); se,sn,ss=struct.unpack_from('<HHH',mm,0x3A)
secs=[struct.unpack_from('<IIQQQQIIQQ',mm,shoff+i*se) for i in range(sn)]
nm=mm[secs[ss][4]:secs[ss][4]+secs[ss][5]]
S={nm[s[0]:nm.index(b'\0',s[0])].decode():(s[3],s[4],s[5]) for s in secs}
ha,hoff,hs=S['.eh_frame_hdr']; cnt,=struct.unpack_from('<I',mm,hoff+8)
tab=np.frombuffer(mm[hoff+12:hoff+12+cnt*8],dtype='<i4').reshape(-1,2)
starts=np.sort(tab[:,0].astype(np.int64)+ha)
def fn(va):
    i=np.searchsorted(starts,va,side='right')-1; return int(starts[i]),(int(starts[i+1])-int(starts[i]))
idv=int(sys.argv[1],0)
# movz wN,#id  (sf=0): 0x52800000 | id<<5 | rd
cands=np.nonzero(((words&0xFFE0001F)==(0x52800000|0)) | True)[0]
mask=(words&0xFFFFE000)==(0x52800000|((idv&0xFFFF)<<5)&0xFFFFE000) if False else None
target=(0x52800000|(idv<<5))
hits=np.nonzero((words&0xFFFFFFE0)==target)[0]
print(f'movz w?,#{idv:#x}: {len(hits)} hits')
seen={}
for h in hits:
    pc=ta+int(h)*4; f,sz=fn(pc); seen.setdefault(f,[]).append(pc)
print('distinct functions:',len(seen))
for f,pcs in list(seen.items())[:int(sys.argv[3]) if len(sys.argv)>3 else 12]:
    print(f'  fn {f:#x} size {fn(f)[1]:#x}  hits at {[hex(p) for p in pcs]}')
