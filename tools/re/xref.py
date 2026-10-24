import mmap, re, struct, sys, numpy as np
P='/mnt/user-data/uploads/libminecraftpe.so'
f=open(P,'rb'); mm=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
# section table
shoff,=struct.unpack_from('<Q',mm,0x28); shentsize,shnum,shstr=struct.unpack_from('<HHH',mm,0x3A)
secs=[struct.unpack_from('<IIQQQQIIQQ',mm,shoff+i*shentsize) for i in range(shnum)]
nm=mm[secs[shstr][4]:secs[shstr][4]+secs[shstr][5]]
S={nm[s[0]:nm.index(b'\0',s[0])].decode():(s[3],s[4],s[5]) for s in secs}
ta,to,ts=S['.text']; print('text',hex(ta),hex(to),hex(ts)); print('rodata',[hex(x) for x in S['.rodata']])
def off2va(o):
    for n,(a,fo,sz) in S.items():
        if fo<=o<fo+sz and a: return a+(o-fo)
words=np.frombuffer(mm[to:to+ts],dtype='<u4')
# eh_frame_hdr -> function starts
ha,ho,hs=S['.eh_frame_hdr']
ver,epe,fce,tee=struct.unpack_from('<BBBB',mm,ho)
assert fce==0x03 and tee==0x3B, (hex(fce),hex(tee))
cnt,=struct.unpack_from('<I',mm,ho+8)
tab=np.frombuffer(mm[ho+12:ho+12+cnt*8],dtype='<i4').reshape(-1,2)
starts=np.sort((tab[:,0].astype(np.int64)+ha))
print('functions in eh_frame:',len(starts))
def func_of(va):
    i=np.searchsorted(starts,va,side='right')-1
    return int(starts[i]), int(starts[i+1]) if i+1<len(starts) else None
def find_str(s):
    pat=b'\0'+s.encode()+b'\0'
    res=[]; 
    for m in re.finditer(re.escape(pat),mm): res.append(m.start()+1)
    return res
def xrefs(sva):
    page=sva&~0xFFF; lo=sva&0xFFF
    idx=np.nonzero((words&0x9F000000)==0x90000000)[0]
    w=words[idx].astype(np.int64)
    immlo=(w>>29)&3; immhi=(w>>5)&0x7FFFF; imm=(immhi<<2)|immlo
    imm=np.where(imm&0x100000,imm-(1<<21),imm)
    pc=ta+idx.astype(np.int64)*4
    tgt=((pc>>12)+imm)<<12
    cand=idx[tgt==page]
    out=[]
    for i in cand:
        if i+1>=len(words): continue
        rd=int(words[i])&31; n=int(words[i+1])
        if (n&0xFF800000)==0x91000000 and ((n>>5)&31)==rd and ((n>>10)&0xFFF)==lo:
            out.append(ta+int(i)*4)
    return out
for key in sys.argv[1:]:
    hits=find_str(key)
    print(f'\n== "{key}"  string at', [hex(off2va(h)) for h in hits])
    for h in hits:
        va=off2va(h)
        xs=xrefs(va)
        print('  xrefs:',[hex(x) for x in xs])
        for x in xs:
            a,b=func_of(x); print(f'   in function {hex(a)} (size {hex(b-a) if b else "?"})')
