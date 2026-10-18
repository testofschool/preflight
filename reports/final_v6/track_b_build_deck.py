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
OUT=ROOT/'docs/Preflight_pitch_deck.pptx'
REPORT=ROOT/'reports/final_v6'
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

with ZipFile(SRC) as z:files={n:z.read(n) for n in z.namelist()}
original=dict(files)
slides={i:xml(files[f'ppt/slides/slide{i}.xml']) for i in range(1,17)}
keep=[1,3,4,5,6,8,9,11,12,13,14]
# Slide 1: fill existing field text in place. No geometry/style/paragraph/master edits.
for t in slides[1].xpath('.//a:t',namespaces=N):
 if t.text=='Team name: ':t.text+='testofschool'
 elif t.text=='Team leader name: ':t.text+='Jung Min Kang'
 elif t.text=='Problem Statement: ':t.text+='People who pay per generation for AI video only learn a clip is unusable after they have paid for it.'
# All content pages retain original section headings in their original position and style.
for i in keep[1:]:title_only(slides[i])
# 2: V5 quotes + benchmark context.
s=slides[3]
shape(s,'Preflight short description',.36,1.30,9.18,.45,'Preflight: check an AI-video prompt before you pay',18,font='Google Sans Flex Medium')
quotes=[('"you still burn credits on the failed attempt"','Trustpilot, Runway review, Sept 2026'),('"Only one of the generations was usable for my purposes"','Trustpilot, Sept 2026'),('"I\'m tired of wasting valuable credits on bad footage, I simply can\'t use"','Adobe Community'),('"I recommend a lo-res preview render before having to spend actual credits"','Adobe Community')]
for j,(quote,source) in enumerate(quotes):
 yy=1.91+j*.66
 shape(s,f'User quote {j+1}',.46,yy,9.05,.39,quote,14.1)
 shape(s,f'Quote source {j+1}',.46,yy+.37,9.05,.20,source,8.8,color='5F6368')
shape(s,'Historical context',.46,4.70,9.05,.62,'In a 2024 public benchmark (GenAI-Bench), 21% of 1,911 human pairwise votes rejected both videos.',12.2,font='Google Sans Flex Medium')
# 3: opportunities: gap / buyer case / producer provenance.
s=slides[4]
shape(s,'The gap',.43,1.37,9.10,.60,'Refunds cover generation errors, not finished clips that are unusable.\nNothing sits before "pay".',15,font='Google Sans Flex Medium')
shape(s,'Business case content',.43,2.17,9.10,2.85,[
 p('Who pays today',14.8,True),
 p('Per-generation buyers. Runway TrustScore 1.1/5 from 340 reviews (Sept 2026). Adobe feature request: "I lose too many credits doing trial and error" (219 votes).',14),
 p('Who would buy a pre-pay step',14.8,True),
 p('Studios and agencies running generation pipelines. Generator platforms as an embedded step.',14),
 p('Built by a Seoul producer who ran generative-video pipelines for 2.5 years. Tested by a teammate in India.',14),
 p('No revenue or market-size figure is claimed.',12.5,color='5F6368')])
# 4: three rungs + distinct clip review.
s=slides[5]
shape(s,'Feature content',.43,1.40,9.08,3.78,[
 p('Preflight: three rungs before you pay',18,True),
 p('Risk check (free)',15.5,True),p('Failure-risk estimate from 1,911 human votes, with the nearest historical prompts as evidence.',14.5,after=10),
 p('Gemini rewrite',15.5,True),p('Kept only if the estimated risk drops.',14.5,after=10),
 p('A still before a $3.20 Veo attempt',15.5,True),p('Veo 3.1, 8 s at $0.40/s (Google pricing page).',14.5,after=10),
 p('After generation: upload a clip for a Gemini second look. Its verdict is stored separately as feedback.',14.5)])
# 5: loop + original/rewrite stills. Both are crops of existing images, no generated calls.
s=slides[6]
shape(s,'Generator loop',.43,1.38,9.10,.46,'Every generator\'s loop: prompt → pay → generate → judge → re-prompt.',15.5,font='Google Sans Flex Medium')
shape(s,'Preflight placement',.43,1.98,9.10,.58,'Preflight adds a risk check, a lower-risk rewrite and a still before "pay".',15)
picture(s,6,'docs/deck_assets/spoon_original.jpg',.47,2.70,4.18,2.388571,name='Saved original spoon/laptop still')
picture(s,6,'docs/deck_assets/spoon_rewritten.jpg',5.05,2.70,4.18,2.388571,name='Saved rewrite spoon/laptop still')
shape(s,'Original still caption',.47,5.12,4.18,.24,'Saved original still',10.5,color='5F6368')
shape(s,'Rewrite still caption',5.05,5.12,4.18,.24,'Saved rewrite still',10.5,color='5F6368')
# 6: editable architecture diagram.
s=slides[8]
shape(s,'Architecture caption',.43,1.35,9.12,.35,'Browser request and Google Cloud services',15,font='Google Sans Flex Medium')
boxes=[(.25,1.00,'Browser'),(1.55,1.65,'Cloud Run\nFastAPI\nasia-southeast1'),(3.55,1.85,'Google ADK\nrewrite agent\nGemini 3.5 Flash\nVertex AI'),(5.75,1.65,'Tools\nNearest prompts\nIRT difficulty'),(7.75,1.98,'Cloud Firestore\n1,911 votes\nIRT parameters\nFeedback\nSaved stills')]
for j,(xx,ww,txt) in enumerate(boxes):shape(s,f'Architecture node {j}',xx,2.05,ww,1.42,txt,11.2,fill='F8F9FA',line='BDC1C6',align='ctr',margin=.08)
for j in range(4):connector(s,f'Main flow arrow {j}',boxes[j][0]+boxes[j][1],2.75,boxes[j+1][0]-.035,2.75)
connector(s,'Session branch',4.475,3.47,4.475,3.80)
shape(s,'Agent session service',3.40,3.82,2.15,.64,'Agent Platform\nSessions',12,fill='F8F9FA',line='BDC1C6',align='ctr')
shape(s,'Clip review branch',.43,4.60,9.10,.32,'Clip review: Gemini video understanding',13.5)
shape(s,'Image preview branch',.43,4.95,9.10,.32,'Still preview: Gemini image model',13.5)
# 7: technologies: explicit roles already in v5 architecture.
s=slides[9]
shape(s,'Technology roles',.43,1.40,9.12,3.92,[
 p('Cloud Run (FastAPI, asia-southeast1)',15.5,True),p('Hosts the browser request workflow.',14,after=10),
 p('Google ADK + Gemini 3.5 Flash on Vertex AI',15.5,True),p('Rewrite agent with Agent Platform Sessions. Tools retrieve nearby prompts and IRT difficulty.',14,after=10),
 p('Cloud Firestore',15.5,True),p('Stores 1,911 votes, IRT parameters, feedback and saved stills.',14,after=10),
 p('Gemini video understanding + Gemini image model',15.5,True),p('Clip second look and still preview.',14,after=10),
 p('Active for sample prompts (saved stills); live generation limited',12.5,color='5F6368')])
# 8: actual demo crops, no browser chrome or unrelated numeric counters.
s=slides[11]
shape(s,'Demo caption',.43,1.35,9.10,.54,'a spoon and a laptop: 46.8% → 15.8% estimated risk after the Gemini rewrite.',15.5,font='Google Sans Flex Medium')
shape(s,'Risk label',.47,2.02,4.30,.28,'Risk + why',12.5,font='Google Sans Flex Medium')
picture(s,11,'demo/frames/02_risk_and_score_details.png',.47,2.38,4.30,1.145863,crop=(885,110,1598,300),name='Frame 02 risk estimate')
picture(s,11,'demo/frames/02_risk_and_score_details.png',.47,3.62,4.30,1.265,crop=(895,615,1235,715),name='Frame 02 nearest-prompt explanation')
shape(s,'Rewrite label',5.10,2.02,2.50,.28,'Better prompt',12.5,font='Google Sans Flex Medium')
picture(s,11,'demo/frames/04_better_prompt_copied.png',5.10,2.38,2.40,2.379310,crop=(1250,110,1598,455),name='Frame 04 better prompt')
shape(s,'Still label',7.75,2.02,1.80,.28,'Saved still',12.5,font='Google Sans Flex Medium')
picture(s,11,'docs/deck_assets/spoon_original.jpg',7.75,2.38,1.85,1.057143,name='Frame 05 saved-still asset, cache byte match')
shape(s,'Still limitation label',7.75,3.62,1.86,1.33,'0 model calls\n$0.00\n\nA still cannot judge motion, flicker or timing.',11.2,color='5F6368')
# 9: fixed measured figures and honest limits.
s=slides[12]
shape(s,'Benchmarking content',.43,1.40,9.10,3.94,[
 p('What we measured, and the limits',18,True),
 p('Held-out AUC 0.67',17,True),p('Historical signal, not a calibrated probability for today\'s models.',14.5,after=12),
 p('Live image generation',16,True),p('60 test calls across three Gemini image models. Best 8/20 under shared capacity.',14.5),p('Judges see saved stills for the 5 samples, labelled "0 model calls · $0.00".',14.5,after=12),
 p('Clip-review accuracy: not measured',16,True)])
# 10: exact future claims.
s=slides[13]
shape(s,'Future development content',.43,1.45,9.10,3.80,[
 p('Next',18,True,after=16),p('Live stills with dedicated image capacity.',16,after=16),p('Separate tabs for check and clip review.',16,after=16),p('Non-English vote data before scoring non-English prompts.',16,after=16),p('On-page emphasis of the risk drop.',16,after=16)])
# 11: template's link fields, explicit missing video fact.
s=slides[14]
# Keep title paragraph only, replace instructional field bullets with filled native fields.
shape(s,'Submission links',.43,1.45,9.08,3.80,[
 p('GitHub Public Repository',16,True),p('https://github.com/testofschool/preflight',15,after=22),
 p('Demo Video Link (3 Minutes)',16,True),p('Pending public upload',15,color='5F6368',after=22),
 p('Final Product Link',16,True),p('https://preflight-jcgro45veq-as.a.run.app',15)])
# Link targets for visible live/repo URLs.
relsname='ppt/slides/_rels/slide14.xml.rels';rr=xml(files[relsname]);nextid=max(int(x[3:]) for x in rr.xpath('//@Id') if x.startswith('rId'))+1
for run in s.xpath('.//a:r',namespaces=N):
 t=run.find('a:t',N)
 if t is not None and t.text and t.text.startswith('https://'):
  rid=f'rId{nextid}';nextid+=1;E.SubElement(rr,'{'+REL+'}Relationship',Id=rid,Type=N['r']+'/hyperlink',Target=t.text,TargetMode='External');r=run.find('a:rPr',N);h=el('a','hlinkClick',r);h.set(q('r','id'),rid)
files[relsname]=ser(rr)
# JPEG still assets are additional to the template's PNG resources.
ct=xml(files['[Content_Types].xml'])
if not any(e.get('Extension')=='jpg' for e in ct):
 E.SubElement(ct,'{http://schemas.openxmlformats.org/package/2006/content-types}Default',Extension='jpg',ContentType='image/jpeg')
files['[Content_Types].xml']=ser(ct)
# Retain only selected slide references. Source slide resource bytes remain in archive for provenance,
# but omitted slides cannot display. All retained slide IDs/layout references remain original.
root=xml(files['ppt/presentation.xml']);lst=root.find('p:sldIdLst',N)
for i,node in enumerate(list(lst),1):
 if i not in keep:lst.remove(node)
files['ppt/presentation.xml']=ser(root)
for i in keep:files[f'ppt/slides/slide{i}.xml']=ser(slides[i])
# Update app slide count, without modifying any template resources.
if 'docProps/app.xml' in files:
 app=xml(files['docProps/app.xml'])
 for e in app.iter():
  if E.QName(e).localname=='Slides':e.text=str(len(keep))
 files['docProps/app.xml']=ser(app)
# Sources in speaker notes. Existing note placeholder geometry/style and all slide XML stay unchanged.
source_rows={1:'1',3:'2',4:'3 and 8',5:'4',6:'3 and 5',8:'6',9:'6 and 7',11:'5',12:'7',13:'9',14:'submission notes links and pending-upload state'}
known_notes={
 3:[
  'Known quote link (first quote), reproduced from README: https://www.trustpilot.com/reviews/6a9f952dc2a80e997c67354a',
  'Known quote link (preview request), reproduced from README: https://community.adobe.com/questions-404/wasted-generative-credits-on-bad-results-1479378',
  'Other quote source labels: Trustpilot, Sept 2026; Adobe Community, as supplied in v5. No missing individual quote URL was invented.',
  'Dataset link, reproduced from README: https://huggingface.co/datasets/TIGER-Lab/GenAI-Bench'],
 4:['Refund-policy link, reproduced from README: https://help.runwayml.com/hc/en-us/articles/34266159290003-Can-I-have-credits-refunded',
    'Runway review counts, Adobe feature-request votes, buyer hypotheses and producer history are the supplied v5 facts; no separate URL for an unspecified review/feature-request page was invented.'],
 5:['Cost source label: Google pricing page, as supplied in v5. No new price estimate or claim was introduced.'],
 6:['Visual evidence: docs/deck_assets/spoon_original.jpg and spoon_rewritten.jpg. Byte-identical saved assets verified in reports/final_v6/track_b_saved_stills.json.'],
 8:['Architecture facts: supplied v5 row 6; existing README Architecture and Google Cloud services sections.'],
 9:['Service facts: supplied v5 rows 6 and 7; current samples wording is reproduced from README.'],
 11:['Visual evidence: demo/frames/02_risk_and_score_details.png and 04_better_prompt_copied.png, plus frame-05 byte-matched saved still asset docs/deck_assets/spoon_original.jpg.'],
 12:['All measured figures and claim limits are exactly the supplied v5 row 7. The deck build did not run a new evaluation.'],
 14:['Known links reproduced from docs/submission-notes.md: https://github.com/testofschool/preflight and https://preflight-jcgro45veq-as.a.run.app',
     'Video URL has not been supplied. Pending public upload is displayed. The template-origin 3 Minutes label is a field label, not a measured-duration claim.']}
for i in keep:
 nn=f'ppt/notesSlides/notesSlide{i}.xml';note=xml(files[nn])
 bodies=note.xpath('.//p:sp[p:nvSpPr/p:nvPr/p:ph[@type="body"]]/p:txBody',namespaces=N)
 assert len(bodies)==1, f'Unexpected note body: {nn}'
 header=f'Content canon: Felix-supplied CODEX_ONESHOT_preflight_final_v5, Track B row(s) {source_rows[i]}.' if i!=14 else 'Content canon: docs/submission-notes.md links and the user-supplied pending-upload state.'
 lines=[header,
        'Canonical local copy: reports/final_v6/CODEX_ONESHOT_preflight_final_v5.md. Wording shortened only within the authorized table facts.']+known_notes.get(i,[])
 for line in lines:paragraph(bodies[0],line,size=10,after=4)
 files[nn]=ser(note)

with ZipFile(OUT,'w',ZIP_DEFLATED,compresslevel=9) as z:
 for n,b in files.items():z.writestr(n,b)
# Mechanically compare all resources and slide-one format to canon.
changes=[n for n in original if files.get(n)!=original[n]]
fidelity={}
for prefix in ['ppt/slideMasters/','ppt/slideLayouts/','ppt/theme/','ppt/fonts/']:
 names=[n for n in original if n.startswith(prefix)];fidelity[prefix]={'count':len(names),'unchanged':sum(files[n]==original[n] for n in names)}
def no_text(b):
 r=xml(b)
 for t in r.xpath('.//a:t',namespaces=N):t.text=''
 return E.tostring(r,method='c14n')
fidelity['slide1_all_nontext_xml_identical']=no_text(original['ppt/slides/slide1.xml'])==no_text(files['ppt/slides/slide1.xml'])
fidelity['slide1_picture_assets_identical']=all(files[n]==original[n] for n in original if n.startswith('ppt/media/'))
fidelity['template_sha256']=hashlib.sha256(SRC.read_bytes()).hexdigest()
fidelity['pptx_sha256']=hashlib.sha256(OUT.read_bytes()).hexdigest()
fidelity['pptx_bytes']=OUT.stat().st_size
fidelity['displayed_source_slides']=keep;fidelity['omitted_source_slides']=[i for i in range(1,17) if i not in keep];fidelity['modified_original_package_parts']=changes;fidelity['added_media_parts']=[n for n in files if n not in original]
(REPORT/'track_b_fidelity.json').write_text(json.dumps(fidelity,indent=2)+'\n')
(REPORT/'track_b_authored_text.txt').write_text('\n\n'.join('PAGE '+str(j+1)+' (template slide '+str(i)+')\n'+'\n'.join(slides[i].xpath('.//a:t/text()',namespaces=N)) for j,i in enumerate(keep))+'\n')
print(json.dumps(fidelity,indent=2))
