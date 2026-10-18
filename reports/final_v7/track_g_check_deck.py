"""Reproduce authored-word, PDF-text, numeric and rendered-main-visual checks.

Requested native diagrams/cards are visual regions; screenshot text is separately
real product evidence. This does not replace visual review or validate claims.
"""
from pathlib import Path
from PIL import Image, ImageDraw
import argparse, hashlib, json, re, subprocess

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/'reports/final_v7'
parser=argparse.ArgumentParser(description='Check the preserved FAILED G candidate; selected v6 deliverables are separate.')
parser.add_argument('--pdf',default='reports/final_v7/candidate_v7/Preflight_v7_FAILED_G.pdf')
parser.add_argument('--pptx',default='reports/final_v7/candidate_v7/Preflight_v7_FAILED_G.pptx')
parser.add_argument('--render-dir',default='docs/deck_check_v7')
parser.add_argument('--report',default='reports/final_v7/track_g_check_replay.json')
args=parser.parse_args()
CHECK=ROOT/args.render_dir
PDF=ROOT/args.pdf
PPTX=ROOT/args.pptx
if hashlib.sha256(PDF.read_bytes()).hexdigest()!='0695c9768a0881349197ccbc53b0e614d1f2161f4083e4eddc093be804c49610':
 raise SystemExit('This historical checker accepts only the preserved failed-v7 PDF, never the selected v6 deliverable.')
if hashlib.sha256(PPTX.read_bytes()).hexdigest()!='588f2f9aed4b7e3df9c5bb2edcd84e7748f603e14e2102b6559cf0a7614fb184':
 raise SystemExit('PPTX does not match the preserved failed-v7 candidate.')
manifest=json.loads((REPORT/'track_g_layout_manifest.json').read_text())
text=subprocess.check_output(['pdftotext','-layout',str(PDF),'-'],text=True)
(CHECK/'deck_text.txt').write_text(text)
pages=[x for x in text.split('\f') if x.strip()]
BANNED=re.compile('revolutionize|revolutionary|seamless|seamlessly|cutting-edge|game-changer|game-changing|unlock|empower|leverage|robust|harness|next-generation|AI-powered|journey|elevate|delve|supercharge|effortless|magic',re.I)
ALLOWED={'1,911','21%','2024','1.1/5','340','219','46.8%','15.8%','3.20','0.40','8','0.67','60','8/20','5','0','0.00','30','18','23','7','10','6','2.5','3:28'}
NUM=re.compile(r'\d+(?:,\d{3})*(?:\.\d+)?(?:/\d+(?:\.\d+)?)?%?(?::\d+)?')
rows=[]
for number,entry in manifest.items():
 page=int(number);content=pages[page-1]
 im=Image.open(CHECK/f'page-{page:02d}.png')
 mask=Image.new('1',im.size,0);draw=ImageDraw.Draw(mask)
 for a in entry.get('visual_regions',[]):
  # Pixels use inclusive coordinates. This is a union, so nested pictures are not double-counted.
  rect=(round(a['x']/10*im.width),round(a['y']/5.625*im.height),round((a['x']+a['w'])/10*im.width)-1,round((a['y']+a['h'])/5.625*im.height)-1)
  draw.rectangle(rect,fill=1)
 area=100*sum(mask.get_flattened_data())/(im.width*im.height)
 raster_mask=Image.new('1',im.size,0);rdraw=ImageDraw.Draw(raster_mask)
 for a in entry.get('visual_regions',[]):
  if a['kind']!='raster picture':continue
  rect=(round(a['x']/10*im.width),round(a['y']/5.625*im.height),round((a['x']+a['w'])/10*im.width)-1,round((a['y']+a['h'])/5.625*im.height)-1)
  rdraw.rectangle(rect,fill=1)
 raster_area=100*sum(raster_mask.get_flattened_data())/(im.width*im.height)
 raster_mask.save(CHECK/f'raster-area-mask-{page:02d}.png')
 mask.save(CHECK/f'area-mask-{page:02d}.png')
 items=[]
 for hit in NUM.finditer(content):
  token=hit.group()
  if page==5 and token in {'1','2','3','4'}:kind='explicit user-map structural process ordinal identifier'
  elif token in ALLOWED:kind='whitelisted quantitative token'
  elif token=='3.5' and 'Gemini' in content[max(0,hit.start()-12):hit.start()]:kind='explicit user-map model identifier Gemini 3.5 Flash'
  elif page==12 and token=='3' and 'Minutes' in content[hit.end():hit.end()+15]:kind='unchanged template field label (3 Minutes)'
  elif page==12 and 'https://' in content[max(0,hit.start()-30):hit.start()]:kind='native URL identifier digits'
  else:kind='UNSUPPORTED'
  items.append({'token':token,'class':kind,'context':content[max(0,hit.start()-35):hit.end()+45].replace('\n',' ')})
 filled_words=24 if page==1 else 5 if page==12 else len(' '.join(entry.get('body',[])).split())
 row={'page':page,'actual_raster_area_render_percent':round(raster_area,2),'template_exception':entry['template_exception'],'headline_words':len(entry.get('headline','').split()),'body_words':filled_words,'picture_visual_area_render_percent':round(area,2),'render_pixels':list(im.size),'area_method':'Union of actual main raster-picture and explicitly requested native diagram/card rectangles mapped to 50-dpi render pixels. Overlaps counted once. Header/footer excluded.','banned_hits':BANNED.findall(content),'numbers':items,'unsupported_numeric_count':sum(x['class']=='UNSUPPORTED' for x in items),'generated_image_model':'UNREPORTED' if page in [2,11] else None}
 row['mechanical_pass']=(entry['template_exception'] or(row['headline_words']<=8 and row['body_words']<=25 and area>=40 and (page not in [5,10] or raster_area>=40))) and not row['banned_hits'] and not row['unsupported_numeric_count']
 rows.append(row)
sheet=Image.new('RGB',(1500,1220),'#9d9d9d');draw=ImageDraw.Draw(sheet)
for j,path in enumerate(sorted(CHECK.glob('page-*.png'))):
 sheet.paste(Image.open(path),(j%3*500,j//3*305+23));draw.text((j%3*500+8,j//3*305+5),path.name,fill='white')
sheet.save(CHECK/'contact_sheet.png')
facts=lambda p:{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
qa={'pdf':dict(facts(PDF),pages=len(pages)),'pptx':facts(PPTX),'word_count_method':'Whitespace token count, stricter than lexical word count for standalone arrows, plus signs and slashes; numbers count as tokens. Includes every authored content label and every explanatory caveat. Filled template cover/link values are counted as 24/5; organizer labels/sections are excluded. Only pure citations and quote/image attributions are excluded. Embedded screenshot text is separately real product evidence, not additional authored prose.','rows':rows,'banned_total':sum(len(x['banned_hits']) for x in rows),'unsupported_numeric_total':sum(x['unsupported_numeric_count'] for x in rows),'mechanical_pass':all(x['mechanical_pass'] for x in rows),'font_output':subprocess.check_output(['pdffonts',str(PDF)],text=True),'model_generations':2,'generated_model_exact_return':'UNREPORTED','product_image_model_calls':0,'claim_boundary':'Mechanical checks only. Author and independent visual reviews are recorded separately.'}
(ROOT/args.report).write_text(json.dumps(qa,indent=2)+'\n')
print(json.dumps({k:qa[k] for k in ['pdf','pptx','mechanical_pass','banned_total','unsupported_numeric_total']},indent=2))
