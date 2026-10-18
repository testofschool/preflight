#!/usr/bin/env python3
"""Insert a real production own-prompt capture after the saved-still beat.
Never writes any pre-existing video. Reuses the burned v5 video and exactly its
caption text; only the new live-footage segment receives three new captions.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import hashlib,json,subprocess,shutil,datetime
ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/'reports/final_v6';ASSETS=ROOT/'demo/submission_assets_v6';CHECK=ROOT/'demo/submission_check_v6'
OLD=ROOT/'demo/preflight_demo_final.mp4';RAW=ROOT/'demo/submission_supplement_v6/preflight_demo_own_prompt_raw.mp4'
FINAL=ROOT/'demo/preflight_demo_submission_3m.mp4'
BACKUP_SHA='4bbe0168a40156c06718c53df736ecd90e2314b0539629bed0cc3fa947bdda03'
FONT='/System/Library/Fonts/HelveticaNeue.ttc'
FPS=30;INSERT=80;W=1920;H=1080
NEW_TEXT=["Your own prompt gets a live Gemini rewrite too.","Live stills are limited to the samples during judging, and the page says so.","Every number comes with what it is and what it is not."]
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def run(cmd):subprocess.run([str(x) for x in cmd],check=True,cwd=ROOT)
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))
def wrap(d,text,font,width):
 lines=[];line=''
 for word in text.split():
  test=(line+' '+word).strip()
  if line and d.textlength(test,font=font)>width:lines.append(line);line=word
  else:line=test
 if line:lines.append(line)
 return lines
def main():
 assert not FINAL.exists(),'New submission output already exists; preserve it instead of overwriting'
 assert sha(OLD)==BACKUP_SHA,'Mismatch -> STOP: 2:52 backup'
 assert not list((ROOT/'demo').glob('voiceover.*')),'Voiceover now exists; align explicitly'
 for p in [ASSETS,CHECK]:p.mkdir(exist_ok=False)
 capture=json.loads((REPORT/'track_c_supplement_capture.json').read_text())
 assert capture['sequence_pass'] and sha(RAW)==capture['video']['sha256']
 raw=probe(RAW);nframes=int(next(s for s in raw['streams'] if s['codec_type']=='video')['nb_frames'])
 duration=nframes/FPS;total_frames=172*FPS+nframes;total=total_frames/FPS
 assert 30<=duration<=40 and 190<=total<=215
 # These frame boundaries follow the actual captured actions, including browser lead-in.
 starts=[0,round(21.4*FPS),round(28.8*FPS)];ends=starts[1:]+[nframes]
 added=[]
 for i,(text,a,b) in enumerate(zip(NEW_TEXT,starts,ends)):
  im=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(im);face=ImageFont.truetype(FONT,43)
  lines=wrap(d,text,face,1670);assert len(lines)<=2
  top=H-56-len(lines)*58;maximum=max(d.textlength(x,font=face) for x in lines)
  d.rounded_rectangle(((W-maximum)/2-30,top-16,(W+maximum)/2+30,H-42),14,fill=(20,43,49,242))
  for n,line in enumerate(lines):d.text(((W-d.textlength(line,font=face))/2,top+n*58),line,font=face,fill='#fffefa')
  asset=ASSETS/f'caption_new_{i}.png';im.save(asset)
  added.append({'start_frame':INSERT*FPS+a,'end_frame':INSERT*FPS+b,'start':INSERT+a/FPS,'end':INSERT+b/FPS,
   'source_start_frame':a,'source_end_frame':b,'text':text,'font_px':43,'lines':lines,'asset':str(asset),'source':'new real production capture'})
 manifest=['ffconcat version 1.0']
 for c in added:
  manifest += ["file '"+c['asset']+"'",'option framerate 30','duration '+format((c['source_end_frame']-c['source_start_frame'])/FPS,'.9f')]
 manifest += ["file '"+added[-1]['asset']+"'",'option framerate 30']
 caps=ASSETS/'new_captions.ffconcat';caps.write_text('\n'.join(manifest)+'\n')
 oldcues=json.loads((ROOT/'reports/final_v5/track_c_captions.json').read_text());cues=[]
 for old in oldcues:
  c=dict(old);c['source']='original v5 burned captions'
  if c['start_frame']>=INSERT*FPS:
   c['start_frame']+=nframes;c['end_frame']+=nframes;c['start']=c['start_frame']/FPS;c['end']=c['end_frame']/FPS
  assert not (old['start_frame']<INSERT*FPS<old['end_frame']),'Insertion splits an original caption'
  cues.append(c)
 cues=sorted(cues+added,key=lambda c:c['start_frame'])
 assert [c['text'] for c in cues if c['source']=='original v5 burned captions']==[c['text'] for c in oldcues]
 (REPORT/'track_c_submission_captions.json').write_text(json.dumps(cues,indent=2)+'\n')
 (REPORT/'track_c_submission_caption_script.txt').write_text('\n'.join(c['text'] for c in cues if c['text'])+'\n')
 filters=(f'[0:v]split=2[of][ol];[of]trim=start_frame=0:end_frame={INSERT*FPS},setpts=PTS-STARTPTS[first];'
  f'[ol]trim=start_frame={INSERT*FPS}:end_frame={172*FPS},setpts=PTS-STARTPTS[last];'
  '[2:v]fps=30,format=rgba[cap];[1:v][cap]overlay=0:0:shortest=1:format=auto,format=yuv420p[new];'
  '[first][new][last]concat=n=3:v=1:a=0,format=yuv420p[v]')
 cmd=['ffmpeg','-hide_banner','-loglevel','warning','-nostdin','-i',OLD,'-i',RAW,'-f','concat','-safe','0','-i',caps,
  '-filter_complex',filters,'-map','[v]','-an','-r','30','-frames:v',total_frames,'-c:v','libx264','-preset','fast','-crf','18','-threads','6','-movflags','+faststart',FINAL]
 (REPORT/'track_c_submission_ffmpeg_command.json').write_text(json.dumps([str(x) for x in cmd],indent=2)+'\n')
 run(cmd)
 info=probe(FINAL);v=next(s for s in info['streams'] if s['codec_type']=='video')
 assert v['codec_name']=='h264' and (v['width'],v['height'],v['avg_frame_rate'])==(1920,1080,'30/1')
 assert int(v['nb_frames'])==total_frames and abs(float(info['format']['duration'])-total)<0.000002
 assert not any(s['codec_type']=='audio' for s in info['streams'])
 run(['ffmpeg','-v','error','-i',FINAL,'-f','null','-'])
 assert sha(OLD)==BACKUP_SHA
 secs=int(total);desktop=Path.home()/'Desktop'/f'UPLOAD_THIS_Preflight_AIBC2026_{secs//60}m{secs%60:02d}s.mp4'
 assert not desktop.exists(),'Desktop new name already exists; preserve it'
 shutil.copy2(FINAL,desktop);assert sha(FINAL)==sha(desktop)
 frame_receipts=[]
 # Five requested checks plus clear detail checks within the new segment.
 for t in [5,70,95,100,102,110,140,180]:
  p=CHECK/f'{t//60:02d}m{t%60:02d}s.png'
  run(['ffmpeg','-v','error','-ss',t,'-i',FINAL,'-frames:v','1',p])
  frame_receipts.append({'time_seconds':t,'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size})
 sheet=Image.new('RGB',(1920,1620),'#f5f4ee');d=ImageDraw.Draw(sheet);face=ImageFont.truetype(FONT,28)
 for i,t in enumerate([5,70,100,102,140,180]):
  p=next(x for x in frame_receipts if x['time_seconds']==t)
  im=Image.open(ROOT/p['path']).convert('RGB');im.thumbnail((920,518));x=(i%2)*960;y=(i//2)*540
  sheet.paste(im,(x+20,y+20));d.rectangle((x+22,y+22,x+118,y+58),fill='#f5f4ee');d.text((x+30,y+23),f'{t//60}:{t%60:02d}',font=face,fill='#142b31')
 sheet.save(CHECK/'contact_sheet.png')
 facts={'duration_seconds':float(info['format']['duration']),'duration_display':f'{secs//60}:{secs%60:02d}.233',
  'byte_size':FINAL.stat().st_size,'sha256':sha(FINAL),'path':str(FINAL),'desktop_upload_copy':str(desktop),
  'desktop_upload_copy_sha256':sha(desktop),'desktop_upload_copy_bytes':desktop.stat().st_size,
  'resolution':'1920x1080','fps':'30/1','video_codec':v['codec_name'],'audio_stream':False,'full_decode_pass':True,
  'backup_2m52s_sha256_before':BACKUP_SHA,'backup_2m52s_sha256_after':sha(OLD),'backup_unchanged':True,
  'new_segment_raw_duration_seconds':duration,'new_segment_start_seconds':INSERT,'new_segment_end_seconds':INSERT+duration,
  'new_segment_source':str(RAW),'new_segment_source_sha256':sha(RAW),'new_segment_trimmed':False,
  'existing_frame_order_preserved':True,'existing_caption_text_preserved':True,'existing_static_cards_extended':False,
  'new_caption_text':NEW_TEXT,'new_caption_numbers':[],'caption_font_px':43,'caption_max_lines':max(len(x['lines']) for x in cues),
  'visible_counter_before':'NOT SHOWN','visible_counter_after':'NOT SHOWN','status_generations_before':0,'status_generations_after':0,
  'status_generations_limitation':capture['generations_counter_limitation'],'image_model_calls':0,'zero_image_model_calls_basis':capture['zero_image_model_calls_basis'],
  'own_prompt_rewrite_source':capture['preflight_response']['rewrite_source'],'own_prompt_rewrite_status':capture['preflight_response']['rewrite_status'],
  'own_prompt_risk_line':'13.3% original → 3.3% rewrite (readable in real captured UI; no number added in new captions)',
  'caption_cue_count':len(cues),'frames':frame_receipts,'timing_note':'Human confirmed preserve scene order; 1:40 checks new segment, 2:20 remains clip review.',
  'ffprobe':info,'measured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 (REPORT/'track_c_submission_video_facts.json').write_text(json.dumps(facts,indent=2)+'\n')
 print(json.dumps({k:facts[k] for k in ['duration_seconds','byte_size','sha256','path','desktop_upload_copy','new_segment_start_seconds','new_segment_end_seconds','backup_unchanged','full_decode_pass']},indent=2),flush=True)
if __name__=='__main__':main()
