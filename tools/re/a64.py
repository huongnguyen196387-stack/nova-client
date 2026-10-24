import mmap, struct, re, sys
P='/mnt/user-data/uploads/libminecraftpe.so'
f=open(P,'rb'); mm=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
# file offset == vaddr in .text/.rodata for this lib (verified: text 0x64c63c0 both)
def R(n,sf=1,sp=False):
    if n==31: return ('sp' if sp else ('xzr' if sf else 'wzr'))
    return ('x' if sf else 'w')+str(n)
def sx(v,b): return v-(1<<b) if v&(1<<(b-1)) else v
def cstr(va):
    try:
        e=mm.find(b'\0',va,va+80)
        s=mm[va:e]
        if 3<=len(s)<=70 and all(32<=c<127 for c in s): return s.decode()
    except Exception: pass
class D:
    def __init__(s): s.adrp={}
    def dis(s,pc,w):
        sf=w>>31
        if (w&0x9F000000)==0x90000000:
            immlo=(w>>29)&3; immhi=(w>>5)&0x7FFFF; imm=sx((immhi<<2)|immlo,21)
            t=((pc>>12)+imm)<<12; rd=w&31; s.adrp[rd]=t; return f'adrp {R(rd)}, {t:#x}'
        if (w&0x9F000000)==0x10000000:
            immlo=(w>>29)&3; immhi=(w>>5)&0x7FFFF; imm=sx((immhi<<2)|immlo,21); return f'adr {R(w&31)}, {pc+imm:#x}'
        if (w&0x1F000000)==0x11000000:
            op='sub' if (w>>30)&1 else 'add'; S=(w>>29)&1; sh=(w>>22)&1; imm=((w>>10)&0xFFF)<<(12 if sh else 0)
            rd,rn=w&31,(w>>5)&31
            ann=''
            if op=='add' and not S and rn in s.adrp:
                t=s.adrp[rn]+imm; c=cstr(t); ann=f'   ; -> {t:#x}'+(f' "{c}"' if c else ''); s.adrp[rd]=t
            if S and rd==31: return f'cmp{"" if op=="sub" else "n"} {R(rn,sf,True)}, #{imm:#x}'
            return f'{op}{"s" if S else ""} {R(rd,sf,not S)}, {R(rn,sf,True)}, #{imm:#x}{ann}'
        if (w&0x7F800000)==0x52800000 or (w&0x7F800000)==0x72800000 or (w&0x7F800000)==0x12800000:
            opc=(w>>29)&3; hw=(w>>21)&3; imm=(w>>5)&0xFFFF; rd=w&31
            nm={0:'movn',2:'movz',3:'movk'}.get(opc,'mov?'); return f'{nm} {R(rd,sf)}, #{imm:#x}'+(f', lsl #{hw*16}' if hw else '')
        if (w&0x1F200000)==0x0A000000 or (w&0x1F000000)==0x0B000000 and False:
            opc=(w>>29)&3; N=(w>>21)&1; rm=(w>>16)&31; rn=(w>>5)&31; rd=w&31; imm6=(w>>10)&63
            if opc==1 and rn==31 and not N and not imm6: return f'mov {R(rd,sf)}, {R(rm,sf)}'
            nm=['and','orr','eor','ands'][opc]; return f'{nm} {R(rd,sf)}, {R(rn,sf)}, {R(rm,sf)}'
        if (w&0x1F200000)==0x0B000000:
            op='sub' if (w>>30)&1 else 'add'; S=(w>>29)&1; rm=(w>>16)&31; rn=(w>>5)&31; rd=w&31
            if S and rd==31: return f'{"cmp" if op=="sub" else "cmn"} {R(rn,sf)}, {R(rm,sf)}'
            return f'{op}{"s" if S else ""} {R(rd,sf)}, {R(rn,sf)}, {R(rm,sf)}'
        if (w&0x3B000000)==0x39000000:
            size=w>>30; V=(w>>26)&1; opc=(w>>22)&3; imm=((w>>10)&0xFFF)<<size; rn=(w>>5)&31; rt=w&31
            ld=opc&1; 
            if V: reg=('b','h','s','d')[size]+str(rt) if size<4 else f'q{rt}'; 
            else: reg=R(rt,1 if size==3 else 0)
            nm=('ldr' if ld else 'str')+('' if V or size>=2 else ('b' if size==0 else 'h'))
            ann=''
            if rn in s.adrp:
                t=s.adrp[rn]+imm; ann=f'   ; [{t:#x}]'
            return f'{nm} {reg}, [{R(rn,1,True)}, #{imm:#x}]{ann}'
        if (w&0x3B200C00) in (0x38000000,0x38000C00,0x38000400) and (w&0x3B000000)==0x38000000:
            size=w>>30; V=(w>>26)&1; opc=(w>>22)&3; imm=sx((w>>12)&0x1FF,9); rn=(w>>5)&31; rt=w&31; ld=opc&1; k=(w>>10)&3
            reg=(('b','h','s','d')[size]+str(rt)) if V and size<4 else R(rt,1 if size==3 else 0)
            nm=('ldr' if ld else 'str') if k else ('ldur' if ld else 'stur')
            return f'{nm} {reg}, [{R(rn,1,True)}, #{imm}]'+(' !' if k==3 else (' post' if k==1 else ''))
        if (w&0x3B200C00)==0x38200800:
            return f'ldr/str reg-offset {w:#010x}'
        if (w&0x3E000000)==0x28000000:
            opc=w>>30; V=(w>>26)&1; L=(w>>22)&1; imm=sx((w>>15)&0x7F,7)<<(2+(opc if not V else opc)); rt2=(w>>10)&31; rn=(w>>5)&31; rt=w&31
            sz=(opc==2)
            return f'{"ldp" if L else "stp"} {R(rt,sz)}, {R(rt2,sz)}, [{R(rn,1,True)}, #{imm}]'
        if (w&0x7C000000)==0x14000000:
            imm=sx(w&0x3FFFFFF,26)*4; return f'{"bl" if w>>31 else "b"} {pc+imm:#x}'
        if (w&0xFFFFFC1F) in (0xD61F0000,0xD63F0000,0xD65F0000):
            k={0xD61F0000:'br',0xD63F0000:'blr',0xD65F0000:'ret'}[w&0xFFFFFC1F]; return f'{k} {R((w>>5)&31)}' if k!='ret' else 'ret'
        if (w&0x7E000000)==0x34000000:
            return f'{"cbnz" if (w>>24)&1 else "cbz"} {R(w&31,sf)}, {pc+sx((w>>5)&0x7FFFF,19)*4:#x}'
        if (w&0x7E000000)==0x36000000:
            return f'{"tbnz" if (w>>24)&1 else "tbz"} {R(w&31)}, #{((w>>19)&31)|((w>>31)<<5)}, {pc+sx((w>>5)&0x3FFF,14)*4:#x}'
        if (w&0xFF000010)==0x54000000:
            c=['eq','ne','cs','cc','mi','pl','vs','vc','hi','ls','ge','lt','gt','le','al','nv'][w&15]; return f'b.{c} {pc+sx((w>>5)&0x7FFFF,19)*4:#x}'
        if w==0xD503201F: return 'nop'
        if (w&0x7F800000)==0x53000000 or (w&0x7F800000)==0x13000000:
            return f'{"ubfm" if (w>>29)&3==2 else "sbfm"} {R(w&31,sf)}, {R((w>>5)&31,sf)}, #{(w>>16)&63}, #{(w>>10)&63}'
        if (w&0xFF20FC00)==0x1E202800 or (w&0xFFE0FC00)==0x1E201800: return f'fp-arith {w:#010x}'
        return f'.word {w:#010x}'
def dump(a,b):
    d=D()
    for pc in range(a,b,4):
        w=struct.unpack_from('<I',mm,pc)[0]
        print(f'{pc:#x}: {d.dis(pc,w)}')
if __name__=='__main__':
    dump(int(sys.argv[1],16),int(sys.argv[2],16))
