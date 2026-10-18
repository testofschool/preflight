"""Fill organizer PPTX by surgical OOXML edits; preserve template master/layout/theme/font resources.
No python-pptx. All added text/architecture objects remain editable. No image generation.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
from copy import deepcopy
import hashlib,json,collections,sys
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'docs/template/aibc_template.pptx'
# Historical failed-candidate builder. Never overwrite the restored selected v6 files.
if '--rebuild-failed-candidate' not in sys.argv:
 raise SystemExit('G failed and v6 is selected. This historical builder is disabled by default; do not run it for Track D.')
OUT=ROOT/'reports/final_v7/track_g_build/rebuilt_failed_v7.pptx'
REPORT=ROOT/'reports/final_v7'
N={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
REL='http://schemas.openxmlformats.org/package/2006/relationships'
EMU=914400
q=lambda p,x:'{'+N[p]+'}'+x

def el(p,tag,parent=None,**a):
 e=E.Element(q(p,tag),{k:str(v) for k,v in a.items()})
 if parent is not None: parent.append(e)
 return e

def xml(b):return E.fromstring(b)
def ser(e):return E.tostring(e,encoding='UTF-8',xml_declaration=True,standalone=True)

def rpr(parent,size=14,font='Google Sans Flex',color='202124',bold=False):
 r=el('a','rPr',parent,lang='en-US',sz=round(size*100),b='1' if bold else '0')
 f=el('a','solidFill',r);el('a','srgbClr',f,val=color)
 for t in ['latin','ea','cs','sym']:el('a',t,r,typeface=font)
 return r

def paragraph(body,text,size=14,font='Google Sans Flex',color='202124',bold=False,after=5,align='l'):
 p=el('a','p',body);pr=el('a','pPr',p,algn=align,marL=0,indent=0)
 ls=el('a','lnSpc',pr);el('a','spcPct',ls,val='108000')
 aft=el('a','spcAft',pr);el('a','spcPts',aft,val=round(after*100));el('a','buNone',pr)
 lines=text.split('\n')
 for i,line in enumerate(lines):
  if i:el('a','br',p)
  r=el('a','r',p);rpr(r,size,font,color,bold);el('a','t',r).text=line
 return p

def shape(slide,name,x,y,w,h,text='',size=14,font='Google Sans Flex',color='202124',fill=None,line=None,bold=False,align='l',margin=.03):
 st=slide.find('p:cSld/p:spTree',N);ids=[int(x) for x in slide.xpath('.//p:cNvPr/@id',namespaces=N)]
 s=el('p','sp',st);nv=el('p','nvSpPr',s);el('p','cNvPr',nv,id=max(ids+[0])+1,name=name);el('p','cNvSpPr',nv,txBox='1');el('p','nvPr',nv)
 sp=el('p','spPr',s);xf=el('a','xfrm',sp);el('a','off',xf,x=round(x*EMU),y=round(y*EMU));el('a','ext',xf,cx=round(w*EMU),cy=round(h*EMU))
 geom=el('a','prstGeom',sp,prst='rect');el('a','avLst',geom)
 if fill:el('a','srgbClr',el('a','solidFill',sp),val=fill)
 else:el('a','noFill',sp)
 ln=el('a','ln',sp,w='12700')
 if line:el('a','srgbClr',el('a','solidFill',ln),val=line)
 else:el('a','noFill',ln)
 tb=el('p','txBody',s);bp=el('a','bodyPr',tb,wrap='square',anchor='t',lIns=round(margin*EMU),rIns=round(margin*EMU),tIns=round(margin*EMU),bIns=round(margin*EMU));el('a','noAutofit',bp);el('a','lstStyle',tb)
 if isinstance(text,list):
  for p in text: paragraph(tb,**p)
 else:paragraph(tb,text,size,font,color,bold,align=align)
 return s

def connector(slide,name,x1,y1,x2,y2):
 st=slide.find('p:cSld/p:spTree',N);ids=[int(x) for x in slide.xpath('.//p:cNvPr/@id',namespaces=N)]
 s=el('p','cxnSp',st);nv=el('p','nvCxnSpPr',s);el('p','cNvPr',nv,id=max(ids+[0])+1,name=name);el('p','cNvCxnSpPr',nv);el('p','nvPr',nv)
 sp=el('p','spPr',s);xf=el('a','xfrm',sp);el('a','off',xf,x=round(min(x1,x2)*EMU),y=round(min(y1,y2)*EMU));el('a','ext',xf,cx=round(abs(x2-x1)*EMU),cy=round(abs(y2-y1)*EMU))
 if y2<y1:xf.set('flipV','1')
 if x2<x1:xf.set('flipH','1')
 geom=el('a','prstGeom',sp,prst='line');el('a','avLst',geom);ln=el('a','ln',sp,w='17000');el('a','srgbClr',el('a','solidFill',ln),val='5F6368');el('a','tailEnd',ln,type='triangle')
 return s

def picture(slide,slide_number,file,x,y,w,h,crop=None,name='Existing evidence image'):
 st=slide.find('p:cSld/p:spTree',N);ids=[int(x) for x in slide.xpath('.//p:cNvPr/@id',namespaces=N)]
 relname=f'ppt/slides/_rels/slide{slide_number}.xml.rels';r=xml(files[relname]);rids=[int(x[3:]) for x in r.xpath('//@Id') if x.startswith('rId')];rid='rId'+str(max(rids+[0])+1)
 asset='preflight_'+Path(file).name
 files['ppt/media/'+asset]=(ROOT/file).read_bytes()
 E.SubElement(r,'{'+REL+'}Relationship',Id=rid,Type=N['r']+'/image',Target='../media/'+asset);files[relname]=ser(r)
 s=el('p','pic',st);nv=el('p','nvPicPr',s);el('p','cNvPr',nv,id=max(ids+[0])+1,name=name,descr=str(file));el('p','cNvPicPr',nv);el('p','nvPr',nv)
 bf=el('p','blipFill',s);bl=el('a','blip',bf);bl.set(q('r','embed'),rid)
 if crop:
  l,t,rgt,b=crop;el('a','srcRect',bf,l=round(l/1920*100000),t=round(t/1080*100000),r=round((1920-rgt)/1920*100000),b=round((1080-b)/1080*100000))
 el('a','fillRect',el('a','stretch',bf));sp=el('p','spPr',s);xf=el('a','xfrm',sp);el('a','off',xf,x=round(x*EMU),y=round(y*EMU));el('a','ext',xf,cx=round(w*EMU),cy=round(h*EMU));el('a','avLst',el('a','prstGeom',sp,prst='rect'))
 return s

def existing_text_shape(slide):
 for s in slide.findall('p:cSld/p:spTree/p:sp',N):
  if s.xpath('.//a:t/text()',namespaces=N):return s
 raise Exception('no text')

def title_only(slide):
 s=existing_text_shape(slide);tb=s.find('p:txBody',N)
 ps=tb.findall('a:p',N)
 # Preserve original section title paragraph; remove instruction prompts below it.
 for p in ps[1:]:tb.remove(p)
 for br in ps[0].findall('a:br',N):ps[0].remove(br)
 return s

def p(text,size=14,bold=False,color='202124',after=6,font='Google Sans Flex'):
 return dict(text=text,size=size,bold=bold,color=color,after=after,font=font)

# v7 continues the proven v6 surgical OOXML workflow. No template resource roundtrip.
from PIL import Image
import re,posixpath
BUILD=REPORT/'track_g_build'; BUILD.mkdir(exist_ok=True)
FALLBACK=BUILD/'v6_fallback'
assert hashlib.sha256((FALLBACK/'Preflight_pitch_deck.pptx').read_bytes()).hexdigest()=='00850a0a470aae3dbbc579e6cd22ed63748e10c7da247e8c2b4441bd60503a4a'
assert hashlib.sha256((FALLBACK/'Preflight_pitch_deck.pdf').read_bytes()).hexdigest()=='7f056e614806efd563daee155bd8a0c0f194bbbec64edd6557e77c61a401aef0'
with ZipFile(FALLBACK/'Preflight_pitch_deck.pptx') as z: files={n:z.read(n) for n in z.namelist()}
baseline=dict(files)
with ZipFile(SRC) as z: template={n:z.read(n) for n in z.namelist()}
slides={i:xml(template[f'ppt/slides/slide{i}.xml']) for i in [3,4,5,6,8,9,11,12,13,14]}
slides[1]=xml(files['ppt/slides/slide1.xml'])
for i in slides:
 if i!=1:title_only(slides[i])
# Added closing page clones the original standard content page, keeping its master/layout.
slides[17]=xml(template['ppt/slides/slide3.xml']); title_only(slides[17])
for t in existing_text_shape(slides[17]).xpath('.//a:t',namespaces=N): t.text='Point–Reason–Example–Point'
files['ppt/slides/_rels/slide17.xml.rels']=template['ppt/slides/_rels/slide3.xml.rels']
# The new slide points to a cloned notes part. Its own slide relationship is fixed below.
nr=xml(files['ppt/slides/_rels/slide17.xml.rels'])
for rel in nr:
 if rel.get('Type','').endswith('/notesSlide'): rel.set('Target','../notesSlides/notesSlide17.xml')
files['ppt/slides/_rels/slide17.xml.rels']=ser(nr)
files['ppt/notesSlides/notesSlide17.xml']=template['ppt/notesSlides/notesSlide3.xml']
nr=xml(template['ppt/notesSlides/_rels/notesSlide3.xml.rels'])
for rel in nr:
 if rel.get('Type','').endswith('/slide'):rel.set('Target','../slides/slide17.xml')
files['ppt/notesSlides/_rels/notesSlide17.xml.rels']=ser(nr)

assets=[]
def crop_asset(source,name,box=None,square=False):
 src=ROOT/source
 im=Image.open(src).convert('RGB')
 if box: im=im.crop(box)
 if square:
  d=min(im.size);l=(im.width-d)//2;t=(im.height-d)//2;im=im.crop((l,t,l+d,t+d))
 im.thumbnail((1600,1600))
 dest=ROOT/'docs/deck_assets/v7'/name
 im.save(dest,quality=91,subsampling=0,optimize=True)
 assets.append({'path':str(dest.relative_to(ROOT)),'source':source,'crop':box,'square_crop':square,'pixels':list(im.size),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
 return str(dest.relative_to(ROOT))
concept1=crop_asset('docs/deck_assets/v7/concept_spent_attempts.png','concept_spent_attempts.jpg')
concept2=crop_asset('docs/deck_assets/v7/concept_before_shot.png','concept_before_shot.jpg')
risk=crop_asset('demo/frames/02_risk_and_score_details.png','risk_card_crop.jpg',(895,110,1214,300))
rewrite=crop_asset('demo/frames/04_better_prompt_copied.png','better_prompt_crop.jpg',(1250,110,1598,455))
still_square=crop_asset('docs/deck_assets/spoon_original.jpg','spoon_original_square.jpg',square=True)
paste=crop_asset('demo/frames/02_risk_and_score_details.png','paste_crop.jpg',(320,119,817,278))
why=crop_asset('demo/frames/02_risk_and_score_details.png','why_crop.jpg',(897,566,1230,716))
earlier=crop_asset('../evidence/preflight-20261016/final-cloud-desktop.png','earlier_header_crop.jpg',(60,0,1380,350))
now=crop_asset('reports/first_viewport_d_primary/first_viewport.png','current_header_crop.jpg',(60,0,1380,350))

# Consolidated correction round: faithful source crops only, no new model calls.
risk_wide=crop_asset('demo/frames/02_risk_and_score_details.png','risk_wide_round2.jpg',(885,110,1598,300))
why_tight=crop_asset('demo/frames/02_risk_and_score_details.png','why_tight_round2.jpg',(897,620,1230,660))
rewrite_tight=crop_asset('demo/frames/04_better_prompt_copied.png','rewrite_tight_round2.jpg',(1265,225,1580,285))
still_wide=crop_asset('docs/deck_assets/spoon_original.jpg','still_wide_round2.jpg',(0,300,1344,662))
rewrite_nologo=crop_asset('docs/deck_assets/spoon_rewritten.jpg','spoon_rewrite_nologo_round2.jpg',(240,100,1344,728))
earlier_large=crop_asset('../evidence/preflight-20261016/final-cloud-desktop.png','earlier_header_large_round2.jpg',(60,0,660,340))
now_large=crop_asset('reports/first_viewport_d_primary/first_viewport.png','current_header_large_round2.jpg',(60,0,660,340))

metadata={}
def txt(sn,name,x,y,w,h,text,size=14,**kw):
 return shape(slides[sn],name,x,y,w,h,text,size,**kw)
def headline(sn,text):
 txt(sn,'V7 headline',.43,1.21,9.14,.47,text,22,font='Google Sans Flex Medium')
 metadata[sn]={'headline':text,'body':[],'sources':[],'visual_regions':[]}
def body(sn,name,x,y,w,h,text,size=14,**kw):
 metadata[sn]['body'].append(text); return txt(sn,name,x,y,w,h,text,size,**kw)
def source(sn,text):
 metadata[sn]['sources'].append(text)
 txt(sn,'V7 source line',.43,5.37,9.14,.18,text,7.6,color='5F6368',margin=0)
def pic(sn,path,x,y,w,h,name):
 # Caller supplies an aspect-correct prepared crop. Product pixels are never synthesized.
 picture(slides[sn],sn,path,x,y,w,h,name=name)
 metadata[sn]['visual_regions'].append({'kind':'raster picture','name':name,'x':x,'y':y,'w':w,'h':h,'asset':path})
def panel(sn,name,x,y,w,h,fill='F8F9FA',line='BDC1C6'):
 txt(sn,name,x,y,w,h,'',1,fill=fill,line=line)
 metadata[sn]['visual_regions'].append({'kind':'native requested diagram/card','name':name,'x':x,'y':y,'w':w,'h':h})

# 2. Photographic problem concept, with only the two supplied user quotes.
headline(3,'You pay first. You find out later.')
pic(3,concept1,3.24,1.76,6.45,3.65,'Concept photo: spent attempts')
body(3,'Quote: burned credits',.43,1.94,2.59,1.12,'“you still burn credits on the failed attempt”',16.5)
txt(3,'Quote attribution',.43,3.08,2.59,.35,'Trustpilot, Runway review',8.8,color='5F6368')
body(3,'Quote: preview request',.43,3.64,2.59,1.30,'“a lo-res preview render before having to spend actual credits”',16.5)
txt(3,'Quote attribution Adobe',.43,4.98,2.59,.22,'Adobe Community',8.8,color='5F6368')
source(3,'2024 GenAI-Bench: 21% of 1,911 human votes rejected both videos. Conceptual photograph.')

# 3. Editable workflow diagram, with the coral marker before pay.
headline(4,'A check belongs before pay.')
body(4,'Gap evidence',.43,1.78,9.12,.40,'Refunds cover errors, not unusable finished clips. Runway 1.1/5 (340 reviews). Adobe preview request: 219 votes.',12.2)
for j,label in enumerate(['Prompt','Pay','Generate','Judge','Re-prompt']):
 x=.43+j*1.87
 panel(4,'Workflow '+label,x,2.42,1.61,2.85)
 body(4,'Workflow label '+label,x+.04,3.61,1.53,.40,label,17,align='ctr')
 if j<4:connector(slides[4],'Workflow connector '+str(j),x+1.61,3.85,x+1.84,3.85)
body(4,'Before pay marker',1.91,2.11,1.0,.25,'Preflight',11,color='B4563B',bold=True,align='ctr')
txt(4,'Coral insertion marker',2.12,2.39,.08,2.90,'',1,fill='EF7F60')
source(4,'Sources: Runway credit-refund policy, Trustpilot, Adobe Community preview request.')

# 4. Three real crops. The saved still is deliberately square-cropped; no product pixels are invented.
headline(5,'Three checks before you spend.')
pic(5,risk,.43,1.89,3.00,3.00*190/319,'Real product risk crop')
pic(5,rewrite,3.50,1.89,3.00,3.00*345/348,'Real product better-prompt crop')
pic(5,still_square,6.57,1.89,3.00,3.00,'Real saved still, square crop')
body(5,'Risk crop label',.43,3.91,3.00,.86,'Risk from 1,911 human votes\nHistorical, uncalibrated',13.8)
body(5,'Rewrite crop label',3.50,4.96,3.00,.38,'Gemini rewrite, kept only if risk drops',11.3)
body(5,'Still crop label',6.57,4.96,3.00,.38,'A still before a $3.20 video\nMotion untested',11.3)
source(5,'Sources: demo/frames, saved spoon/laptop still, Google video pricing page.')

# 5. Four numbered, large source thumbnails. Only real raster areas count toward the 40% gate.
headline(6,'Paste. Check. Rewrite. Look.')
for number,label,x,y in [(1,'Paste',.43,1.78),(2,'Risk + why',5.10,1.78),(3,'Better prompt',.43,3.86),(4,'Still / clip review',5.10,3.86)]:
 body(6,'Process ordinal '+str(number),x,y,.28,.22,str(number),12.2,bold=True,align='ctr',fill='F8F9FA',line='BDC1C6')
 body(6,'Process label '+str(number),x+.38,y,4.17,.22,label,12.2)
pic(6,paste,.43,2.03,4.55,4.55*159/497,'Actual pasted prompt thumbnail')
pic(6,risk_wide,5.10,2.03,4.55,4.55*190/713,'Actual risk thumbnail')
pic(6,why_tight,5.10,3.29,4.55,4.55*40/333,'Actual why sentence thumbnail')
pic(6,rewrite_tight,.43,4.09,4.55,4.55*60/315,'Actual rewrite sentence thumbnail')
pic(6,still_wide,5.10,4.09,4.55,4.55*362/1344,'Actual saved still thumbnail')
source(6,'Source: demo/frames and saved spoon/laptop still.')

# 6. Existing architecture reduced to six editable boxes, keeping the service roles.
headline(8,'One request, a traceable check.')
nodes=[('Browser',.43,2.00),('Cloud Run\nFastAPI',3.59,2.00),('Google ADK\nGemini rewrite',6.75,2.00),('Nearest prompts\nIRT',6.75,3.76),('Firestore',3.59,3.76),('Agent Platform\nSessions',.43,3.76)]
for j,(label,x,y) in enumerate(nodes):
 panel(8,'Architecture node '+str(j),x,y,2.82,1.44)
 body(8,'Architecture label '+str(j),x+.09,y+.43,2.64,.66,label,15.4,align='ctr')
for j in [0,1]:connector(slides[8],'Top architecture connector '+str(j),nodes[j][1]+2.82,2.72,nodes[j+1][1]-.04,2.72)
connector(slides[8],'Architecture tools branch',8.16,3.44,8.16,3.72)
connector(slides[8],'Architecture data branch',5.00,3.44,5.00,3.72)
connector(slides[8],'Architecture session branch start',3.80,3.44,3.80,3.60)
connector(slides[8],'Architecture session branch rail',3.80,3.60,1.84,3.60)
connector(slides[8],'Architecture session branch end',1.84,3.60,1.84,3.72)
source(8,'Source: deployed application architecture and README service inventory.')

# 7. Six required technology chips with explicit service-to-role relationships.
headline(9,'All on Google Cloud.')
chips=['Cloud Run','Firestore','Gemini 3.5 Flash\n(Vertex AI)','Google ADK','Agent Platform\nSessions','Gemini image +\nvideo understanding']
roles=['Hosts','Stores','Rewrites','Orchestrates','Remembers','Stills/reviews']
for j,(label,role) in enumerate(zip(chips,roles)):
 x=.43+j*1.54
 panel(9,'Technology chip '+str(j),x,2.07,1.43,2.90)
 body(9,'Technology label '+str(j),x+.055,2.59,1.32,1.13,label,11.8 if j==5 else 13.1,align='ctr')
 connector(slides[9],'Service role relationship '+str(j),x+.715,3.82,x+.715,4.12)
 body(9,'Technology role '+str(j),x+.055,4.32,1.32,.33,role,12.3,bold=True,align='ctr')
source(9,'Source: README service inventory and deployed workflow.')

# 8. Real saved outputs. Rewrite crop omits the logo; original spoon is preserved intact.
headline(11,'See the estimate before the bill.')
body(11,'Original output label',.43,1.73,4.51,.20,'Original prompt',10.0,color='5F6368')
body(11,'Rewrite output label',5.06,1.73,4.51,.20,'Rewritten prompt',10.0,color='5F6368')
pic(11,'docs/deck_assets/spoon_original.jpg',.43,1.98,4.51,4.51*768/1344,'Actual saved original still; apparent edge retained')
pic(11,rewrite_nologo,5.06,1.98,4.51,4.51*628/1104,'Actual saved rewrite still; faithful logo-free crop')
body(11,'Original metric',.43,4.60,4.51,.43,'46.8%',30,font='Google Sans Flex Medium',align='ctr')
body(11,'Rewrite metric',5.06,4.60,4.51,.43,'15.8%',30,font='Google Sans Flex Medium',align='ctr')
body(11,'Hero interpretation',.43,5.13,9.14,.25,'Uncalibrated prompt estimates. Scene changed. Saved stills cannot establish video improvement or judge motion.',11.8)
source(11,'Sources: saved original and rewritten spoon/laptop outputs.')

# 9. Define the live result and distinguish retrieval from generation.
headline(12,'Measured, with the limits shown.')
for j in range(3):panel(12,'Metric card '+str(j),.43+j*3.08,2.00,3.00,3.15)
body(12,'Held-out AUC',.52,2.55,2.82,.68,'0.67',43,font='Google Sans Flex Medium',align='ctr')
body(12,'AUC label',.59,3.66,2.68,.86,'held-out historical AUC',15.5,align='ctr')
body(12,'Live-image best',3.60,2.55,2.82,.68,'8/20',43,font='Google Sans Flex Medium',align='ctr')
body(12,'Live-image definition',3.67,3.49,2.68,1.47,'valid images, best probe\n60 calls across probes',13.4,align='ctr')
body(12,'Replay model calls',6.68,2.43,2.82,.48,'0 model calls',22.0,font='Google Sans Flex Medium',align='ctr')
body(12,'Replay price',6.68,3.08,2.82,.60,'$0.00',35,font='Google Sans Flex Medium',align='ctr')
body(12,'Replay label',6.75,4.17,2.68,.43,'per saved-image replay',15.0,align='ctr')
body(12,'Metric caveats',.43,5.17,9.14,.19,'Risk uncalibrated. Clip accuracy unmeasured.',9.8)
source(12,'Sources: held-out evaluation, live-image probes, saved-image cache receipts.')

# 10. Actual number-free header pixels dominate; QA measurements are in the separate top strip.
headline(13,'Felix builds. Sidhant: 10 QA points, 6 fixes.')
panel(13,'Felix initials card',.43,1.77,4.51,.37)
panel(13,'Sidhant initials and QA card',5.06,1.77,4.51,.37)
body(13,'Felix initial',.47,1.79,.26,.29,'F',15,font='Google Sans Flex Medium',align='ctr')
body(13,'Felix provenance',.83,1.81,4.04,.27,'IRT preprints, 2.5 years',11.2)
body(13,'Sidhant initial',5.10,1.79,.26,.29,'S',15,font='Google Sans Flex Medium',align='ctr')
body(13,'Sidhant shipped label',5.43,1.81,.65,.27,'shipped',10.8,bold=True)
body(13,'Logged QA counts',6.17,1.81,3.36,.27,'Objects 30 → 18. Colours 23 → 7.',10.4)
body(13,'Earlier label',.43,2.23,4.51,.21,'Earlier interface',10.0,color='5F6368')
body(13,'After label',5.06,2.23,4.51,.21,'After teammate QA',10.0,color='5F6368')
pic(13,earlier_large,.43,2.48,4.51,4.51*340/600,'Genuine earlier checked-state header crop')
pic(13,now_large,5.06,2.48,4.51,4.51*340/600,'Genuine current initial-screen header crop')
body(13,'Next steps',.43,5.16,9.14,.19,'Next: live stills, tabs, non-English.',10.0)
source(13,'Sources: teammate QA, first-viewport audit, archival header captures.')

# 11. Point–Reason–Example–Point, with a second conceptual photo only.
headline(17,'Check before you pay.')
pic(17,concept2,3.24,1.76,6.45,3.65,'Concept photo: before the shot')
body(17,'Reason',.43,1.93,2.60,1.15,'Generators bill attempts. Refunds skip unusable clips.',15.5)
body(17,'Example',.43,3.22,2.60,1.17,'Uncalibrated spoon/laptop estimate: 46.8% → 15.8%, saved still before $3.20 video.',15.0)
body(17,'Closing point',.43,4.69,2.60,.63,'Preflight: check before you pay.',16.2,font='Google Sans Flex Medium')
source(17,'Sources: Runway refund policy, saved spoon/laptop example; conceptual photograph.')

# 12. Same organizer links fields. Root will complete Track D only when Felix supplies the URL.
s=slides[14]
shape(s,'Submission links',.43,1.45,9.08,3.80,[p('GitHub Public Repository',16,True),p('https://github.com/testofschool/preflight',15,after=22),p('Demo Video Link (3 Minutes)',16,True),p('Pending public upload',15,color='5F6368',after=22),p('Final Product Link',16,True),p('https://preflight-jcgro45veq-as.a.run.app',15)])
rn='ppt/slides/_rels/slide14.xml.rels';rr=xml(files[rn]);ni=max(int(x[3:]) for x in rr.xpath('//@Id') if x.startswith('rId'))+1
for run in s.xpath('.//a:r',namespaces=N):
 t=run.find('a:t',N)
 if t is not None and t.text and t.text.startswith('https://'):
  rid=f'rId{ni}';ni+=1;E.SubElement(rr,'{'+REL+'}Relationship',Id=rid,Type=N['r']+'/hyperlink',Target=t.text,TargetMode='External');h=el('a','hlinkClick',run.find('a:rPr',N));h.set(q('r','id'),rid)
files[rn]=ser(rr)

keep=[1,3,4,5,6,8,9,11,12,13,17,14]
# Retain original IDs/references. New slide uses one fresh relationship only.
pres=xml(files['ppt/presentation.xml']);lst=pres.find('p:sldIdLst',N)
rels=xml(files['ppt/_rels/presentation.xml.rels'])
rmap={r.get('Id'):posixpath.basename(r.get('Target')) for r in rels}
existing={int(re.search(r'(\d+)\.xml',rmap[n.get(q('r','id'))]).group(1)):deepcopy(n) for n in lst}
rid='rIdV7Closing';E.SubElement(rels,'{'+REL+'}Relationship',Id=rid,Type=N['r']+'/slide',Target='slides/slide17.xml')
node=E.Element(q('p','sldId'),id=str(max(int(n.get('id')) for n in lst)+1));node.set(q('r','id'),rid);existing[17]=node
for n in list(lst):lst.remove(n)
for i in keep:lst.append(existing[i])
files['ppt/presentation.xml']=ser(pres);files['ppt/_rels/presentation.xml.rels']=ser(rels)
ct=xml(files['[Content_Types].xml']);CT='http://schemas.openxmlformats.org/package/2006/content-types'
for part,typ in [('/ppt/slides/slide17.xml','application/vnd.openxmlformats-officedocument.presentationml.slide+xml'),('/ppt/notesSlides/notesSlide17.xml','application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml')]:
 E.SubElement(ct,'{'+CT+'}Override',PartName=part,ContentType=typ)
for ext,typ in [('jpg','image/jpeg'),('png','image/png')]:
 if not any(e.get('Extension')==ext for e in ct):E.SubElement(ct,'{'+CT+'}Default',Extension=ext,ContentType=typ)
files['[Content_Types].xml']=ser(ct)
for i in keep:files[f'ppt/slides/slide{i}.xml']=ser(slides[i]) if i!=1 else baseline['ppt/slides/slide1.xml']
if 'docProps/app.xml' in files:
 app=xml(files['docProps/app.xml'])
 for e in app.iter():
  if E.QName(e).localname=='Slides':e.text='12'
 files['docProps/app.xml']=ser(app)

notes={
3:['The two user quotes are intentionally shortened only to the exact fragments explicitly supplied in the v7 map.','https://www.trustpilot.com/reviews/6a9f952dc2a80e997c67354a','https://community.adobe.com/questions-404/wasted-generative-credits-on-bad-results-1479378','https://huggingface.co/datasets/TIGER-Lab/GenAI-Bench','GenAI-Bench 2024: 21% of 1,911 human pairwise votes rejected both videos.','Concept photograph generated using built-in image tool; model name not returned: UNREPORTED. It depicts no actual user event or product.'],
4:['https://help.runwayml.com/hc/en-us/articles/34266159290003-Can-I-have-credits-refunded','Runway TrustScore 1.1/5, 340 reviews; Adobe preview request 219 votes, per supplied v7 canon. These do not measure Preflight demand or savings.','A check belongs before pay describes the displayed workflow. It intentionally avoids claiming no competing market product exists.'],
5:['Risk and rewrite are genuine crops from demo/frames/02_risk_and_score_details.png and 04_better_prompt_copied.png. Saved still is a square crop of docs/deck_assets/spoon_original.jpg.','Risk comes from 1,911 human votes plus separately stored feedback, and is a mixed heuristic, not calibrated failure probability.','Gemini rewrite is presented only if estimated risk drops. Still before $3.20 video; price calculation in supplied canon is 8 s at $0.40/s.','Saved still cannot judge motion, flicker or timing; no new image or video model call was made for product evidence.'],
6:['Four product storyboard thumbnails: paste, risk and why, better prompt, saved still and separate clip-review workflow.','Process ordinals 1–4 are explicitly authorized by root from the user-mapped numbered thumbnails; they are structural identifiers, not new measured quantities. Actual source crops remain unmodified apart from cropping and resampling.'],
8:['Six-box simplification of deployed README architecture. Browser requests Cloud Run/FastAPI; Google ADK runs Gemini rewrite tools; nearby prompts and IRT support checking; Firestore persists data and feedback; Agent Platform Sessions stores anonymous sessions.','Image and video understanding services appear on the following technology page. This diagram simplifies connections and does not imply those services execute serially.'],
9:['Six technology labels are exactly the supplied v7 map.','Gemini 3.5 Flash is the user-explicit model identifier, not a newly introduced numerical result.','Google Cloud roles reproduced from README; image service remains limited to saved samples and live rewrite remains active.'],
11:['Actual saved original and rewrite spoon/laptop images. Original 46.8%, rewrite 15.8%, mixed estimated risk. No empirical video-quality improvement claim.','Original SHA256 ec93ee2616e1b65ac4cad0d2d82aabebe5f913900d9af9a3cde26c2915fa0121; rewrite SHA256 8dac9ce3a56559eb67a707a322be16a59dc91e19557b77480ef1aec2f6738ea7.','Rewrite image is faithfully cropped to omit the white logo. The complete original spoon is retained: its apparent thin extra edge/trackpad line remains unresolved. No pixel retouch, reconstruction or new image generation was performed. The changed scene and uncalibrated estimates establish no controlled video improvement.','Each is a saved image-model still; no motion, flicker or timing judgment follows from the image. Saved retrieval uses 0 model calls and $0.00.'],
12:['Historical held-out AUC 0.67 is signal, not calibrated probability for current models.','Live-image tests: 60 calls across three Gemini image models; best result 8/20 valid images under shared capacity. Saved stills support judging; no live-reliability pass is claimed.','Saved sample retrieval: 0 model calls, $0.00. Clip-review accuracy unmeasured.'],
13:['Felix designed and shipped Preflight. IRT method derives from his two preprints. He has 2.5 years of generative-video pipeline experience.','Sidhant performed QA across 10 points; 6 shipped. First-screen audit reduced 30 to 18 objects and 23 to 7 colours. Supplied canon, consistent with reports/first_viewport_after.json for the after counts.','Next: live stills, separate tabs for check/clip review, non-English vote data before scoring non-English prompts.','Earlier crop source: sibling evidence/preflight-20261016/final-cloud-desktop.png, a checked full-page state. Now crop source: reports/first_viewport_d_primary/first_viewport.png, initial screen after cleanup. Both show only number-free headers.','These are authentic earlier/current header crops, not matched initial-viewport audit samples. The original initial-viewport before screenshot could not be found. The QA count strip is separate from the header comparison. Never infer the 30/23 measurement from this earlier checked-state crop.'],
17:['Point: Know before you pay. Reason: Generators bill every attempt; refunds skip clips that finish but fail.','Example: A spoon and a laptop, mixed estimated risk 46.8% to 15.8%, with saved image stills before a $3.20 video. This is not measured savings or proven improvement in generated video quality.','Closing: Preflight, know before you pay.','Concept photograph generated using built-in image tool; exact model not returned: UNREPORTED. Blank slate image contains no product pixels or event claim.'],
14:['https://github.com/testofschool/preflight','https://preflight-jcgro45veq-as.a.run.app','Public YouTube URL remains unprovided. Pending public upload is intentional.','Original organizer field label Demo Video Link (3 Minutes) is retained as template text; selected final video is 3:28.233, independently checked by Track I.']}
for i in keep:
 if i==1:continue
 nn=f'ppt/notesSlides/notesSlide{i}.xml';note=xml(files[nn]);bodies=note.xpath('.//p:sp[p:nvSpPr/p:nvPr/p:ph[@type="body"]]/p:txBody',namespaces=N);assert len(bodies)==1
 tb=bodies[0]
 for x in tb.findall('a:p',N):tb.remove(x)
 paragraph(tb,'Content canon: user-supplied Preflight final v7 slide map; original organizer section and template resources preserved.',size=10)
 for line in notes.get(i,[]):paragraph(tb,line,size=10,after=4)
 files[nn]=ser(note)

with ZipFile(OUT,'w',ZIP_DEFLATED,compresslevel=9) as z:
 for name,data in files.items():z.writestr(name,data)
fidelity={'content_canon':'v6 byte-identical fallback plus user v7 map','format_canon':'official template, v6 OOXML and LibreOffice export, Google Sans Flex aliases','displayed_slide_parts':keep,'slide1_xml_byte_identical_to_v6':files['ppt/slides/slide1.xml']==baseline['ppt/slides/slide1.xml'],'pptx_bytes':OUT.stat().st_size,'pptx_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'shared_resources':{}}
for pref in ['ppt/slideMasters/','ppt/slideLayouts/','ppt/theme/','ppt/fonts/']:
 names=[n for n in baseline if n.startswith(pref)];fidelity['shared_resources'][pref]={'count':len(names),'byte_identical':sum(files[n]==baseline[n] for n in names)}
fidelity['all_original_media_preserved']=all(files[n]==baseline[n] for n in baseline if n.startswith('ppt/media/'))
fidelity['changed_existing_parts']=[n for n in baseline if files.get(n)!=baseline[n]]
fidelity['added_parts']=[n for n in files if n not in baseline]
metadata={str(j+1):dict(metadata.get(i,{}),source_slide=i,template_exception=(i in [1,14])) for j,i in enumerate(keep)}
(REPORT/'track_g_layout_manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
(REPORT/'track_g_fidelity.json').write_text(json.dumps(fidelity,indent=2)+'\n')
(REPORT/'track_g_assets.json').write_text(json.dumps(assets,indent=2)+'\n')
(REPORT/'track_g_authored_text.txt').write_text('\n\n'.join('PAGE '+str(j+1)+'\n'+'\n'.join(slides[i].xpath('.//a:t/text()',namespaces=N)) for j,i in enumerate(keep))+'\n')
print(json.dumps(fidelity,indent=2))
