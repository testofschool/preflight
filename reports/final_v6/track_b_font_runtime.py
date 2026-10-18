"""Reproduce reference-family PDF font availability without installing system/user font files.
prepare: download official source pinned to commit, verify digest, instance three aliases.
register/unregister: CoreText SESSION scope (3), reversible; files stay under ignored build scratch.
"""
from pathlib import Path
import hashlib,json,sys,urllib.request,ctypes
ROOT=Path(__file__).resolve().parents[2];BUILD=ROOT/'reports/final_v6/track_b_build';BUILD.mkdir(exist_ok=True)
URL='https://raw.githubusercontent.com/google/fonts/bd8f81ddb5c74d5c8897b36ad88b440266245103/ofl/googlesansflex/GoogleSansFlex%5BROND%2Copsz%2Cslnt%2Cwdth%2Cwght%5D.ttf'
SHA='a9ac770798857d5e8ac593ced42b22e40a7c08cec98319f92b0eccc2783a77ba'
FONT=BUILD/'GoogleSansFlex-VF.ttf';D=BUILD/'fonts';D.mkdir(exist_ok=True)
if sys.argv[1]=='prepare':
 from fontTools.ttLib import TTFont
 from fontTools.varLib.instancer import instantiateVariableFont
 if not FONT.exists():FONT.write_bytes(urllib.request.urlopen(URL).read())
 assert hashlib.sha256(FONT.read_bytes()).hexdigest()==SHA,'font source hash mismatch'
 source=TTFont(FONT)
 for name,weight in [('Google Sans Flex',400),('Google Sans Flex Medium',500),('Google Sans Flex SemiBold',600)]:
  f=instantiateVariableFont(source,{'wght':weight,'wdth':100,'opsz':14,'slnt':0,'ROND':0},inplace=False)
  for n in f['name'].names:
   v={1:name,2:'Regular',4:name,6:name.replace(' ',''),16:name,17:'Regular'}.get(n.nameID)
   if v:n.string=v.encode(n.getEncoding())
  f.recalcTimestamp=False
  f['head'].modified={'GoogleSansFlex': 3875157501, 'GoogleSansFlexSemiBold': 3875157506, 'GoogleSansFlexMedium': 3875157503}[name.replace(' ','')]
  f.save(D/(name.replace(' ','')+'.ttf'))
 print('Prepared reference family aliases from verified official source.')
else:
 cf=ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation');ct=ctypes.CDLL('/System/Library/Frameworks/CoreText.framework/CoreText')
 cf.CFURLCreateFromFileSystemRepresentation.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_long,ctypes.c_bool];cf.CFURLCreateFromFileSystemRepresentation.restype=ctypes.c_void_p
 func=getattr(ct,'CTFontManagerUnregisterFontsForURL' if sys.argv[1]=='unregister' else 'CTFontManagerRegisterFontsForURL');func.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(ctypes.c_void_p)];func.restype=ctypes.c_bool
 result=[]
 for fp in sorted(D.glob('*.ttf')):
  b=str(fp.resolve()).encode();u=cf.CFURLCreateFromFileSystemRepresentation(None,b,len(b),False);err=ctypes.c_void_p();ok=func(u,3,ctypes.byref(err));result.append({'font':fp.name,'action':sys.argv[1],'scope':'session','success':bool(ok),'error_pointer':err.value})
 print(json.dumps(result,indent=2))
 if not result or any(not r['success'] for r in result):sys.exit(1)
