#!/usr/bin/env python3
"""Replace only v6's 1087-frame production insert; preserve every outside decoded frame.
No application/network writes. Existing video targets are backed up before overwrite.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import hashlib,json,subprocess,shutil,datetime
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/final_v7';SUP=ROOT/'demo/submission_supplement_v7';CHECK=ROOT/'demo/submission_check_v7'
FINAL=ROOT/'demo/preflight_demo_submission_3m.mp4';RAW=SUP/'preflight_demo_own_prompt_raw.mp4'
DESKTOP=Path.home()/'Desktop/UPLOAD_THIS_Preflight_AIBC2026_3m28s.mp4'
BACKUP=ROOT/'demo/preflight_demo_submission_3m_before_v7_20261018.mp4'
DESKBACKUP=Path.home()/'Desktop/Preflight_AIBC2026_3m28s_backup_before_v7_20261018.mp4'
CANDIDATE=SUP/'submission_candidate.mp4'
FPS=30;START=2400;LENGTH=1087;END=START+LENGTH;TOTAL=6247
EXPECTED='6ebd825cbe8cbc1810c81d9592ac4e21028340a4ed92dbafb840cd5d684703a2'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def run(cmd):return subprocess.run([str(x)for x in cmd],check=True,cwd=ROOT,capture_output=True,text=True)
def probe(p):return json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',p]).stdout)
def record(p):
 info=probe(p)
 return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'duration_seconds':float(info['format']['duration'])}
def frame_md5(p,path):
 run(['ffmpeg','-v','error','-i',p,'-map','0:v','-pix_fmt','yuv420p','-f','framemd5',path])
 return [line.rsplit(',',1)[-1].strip()for line in path.read_text().splitlines()if not line.startswith('#') and line.strip()]
def main():
 assert sha(FINAL)==sha(DESKTOP)==EXPECTED,'Mismatch -> STOP: v6 selected video/copy'
 assert not BACKUP.exists() and not DESKBACKUP.exists() and not CANDIDATE.exists(),'Retain all prior videos; do not clobber backup/candidate'
 cap=json.loads((OUT/'track_i_capture.json').read_text());assert cap['sequence_pass'] and cap['image_model_calls']==0
 assert sha(RAW)==cap['video']['sha256']
 before_paths=sorted([p for p in (ROOT/'demo').rglob('*')if p.is_file() and p.suffix.lower()in('.mp4','.webm') and SUP not in p.parents]+list(Path.home().joinpath('Desktop').glob('UPLOAD_THIS*.mp4')))
 before=[record(p)for p in before_paths]
 (OUT/'track_i_old_video_manifest.json').write_text(json.dumps(before,indent=2)+'\n')
 shutil.copy2(FINAL,BACKUP);shutil.copy2(DESKTOP,DESKBACKUP)
 assert sha(BACKUP)==sha(DESKBACKUP)==EXPECTED
 CHECK.mkdir(exist_ok=False)
 # These are exactly the original caption cue data and assets; content/timing unchanged.
 cues_path=ROOT/'reports/final_v6/track_c_submission_captions.json';cues=json.loads(cues_path.read_text())
 shutil.copy2(cues_path,OUT/'track_i_submission_captions.json')
 shutil.copy2(ROOT/'reports/final_v6/track_c_submission_caption_script.txt',OUT/'track_i_submission_caption_script.txt')
 begin=round(cap['selected_window_start_offset']*FPS);finish=begin+LENGTH
 rinfo=probe(RAW);rvid=next(s for s in rinfo['streams']if s['codec_type']=='video')
 assert finish<=int(rvid['nb_frames'])
 filters=(f'[0:v]split=2[a][b];[a]trim=start_frame=0:end_frame={START},setpts=PTS-STARTPTS[first];'
  f'[b]trim=start_frame={END}:end_frame={TOTAL},setpts=PTS-STARTPTS[last];'
  f'[1:v]trim=start_frame={begin}:end_frame={finish},setpts=PTS-STARTPTS[raw];'
  '[2:v]fps=30,format=rgba[cap];[raw][cap]overlay=0:0:shortest=1:format=auto,format=yuv420p[new];'
  '[first][new][last]concat=n=3:v=1:a=0,format=yuv420p[v]')
 cmd=['ffmpeg','-hide_banner','-loglevel','warning','-nostdin','-i',BACKUP,'-i',RAW,'-f','concat','-safe','0','-i',ROOT/'demo/submission_assets_v6/new_captions.ffconcat',
  '-filter_complex',filters,'-map','[v]','-an','-r','30','-frames:v',TOTAL,'-c:v','libx264','-preset','fast','-qp','0','-threads','6','-movflags','+faststart',CANDIDATE]
 (OUT/'track_i_ffmpeg_command.json').write_text(json.dumps([str(x)for x in cmd],indent=2)+'\n')
 run(cmd)
 info=probe(CANDIDATE);v=next(s for s in info['streams']if s['codec_type']=='video');duration=float(info['format']['duration'])
 assert 190<=duration<=215 and v['width']==1920 and v['height']==1080 and v['avg_frame_rate']=='30/1' and v['codec_name']=='h264'
 assert int(v['nb_frames'])==TOTAL and not any(s['codec_type']=='audio'for s in info['streams'])
 decode=run(['ffmpeg','-v','error','-i',CANDIDATE,'-f','null','-']);assert not decode.stderr
 oldhashes=frame_md5(BACKUP,OUT/'track_i_v6_decoded_yuv420.framemd5');newhashes=frame_md5(CANDIDATE,OUT/'track_i_v7_decoded_yuv420.framemd5')
 assert len(oldhashes)==len(newhashes)==TOTAL
 outside=list(range(START))+list(range(END,TOTAL));mismatches=[i for i in outside if oldhashes[i]!=newhashes[i]]
 assert not mismatches,f'Outside inserted segment changed at {mismatches[:10]}'
 frame_rows=[]
 for t in [5,70,90,95,100,105,110,140,180]:
  p=CHECK/f'{t//60:02d}m{t%60:02d}s.png'
  run(['ffmpeg','-v','error','-ss',t,'-i',CANDIDATE,'-frames:v','1',p])
  frame_rows.append({'seconds':t,'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size})
 sheet=Image.new('RGB',(1920,1620),'#f5f4ee');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('/System/Library/Fonts/HelveticaNeue.ttc',28)
 for i,t in enumerate([5,70,90,105,140,180]):
  im=Image.open(CHECK/f'{t//60:02d}m{t%60:02d}s.png').convert('RGB');im.thumbnail((920,518));x=(i%2)*960;y=(i//2)*540
  sheet.paste(im,(x+20,y+20));draw.rectangle((x+20,y+20,x+120,y+58),fill='#f5f4ee');draw.text((x+30,y+23),f'{t//60}:{t%60:02d}',font=font,fill='#142b31')
 sheet.save(CHECK/'contact_sheet.png')
 facts={'status':'CANDIDATE_READY_FOR_VISUAL_AND_CAPTION_QA','candidate':record(CANDIDATE),'intended_final_path':str(FINAL),'desktop_upload_copy':str(DESKTOP),
  'duration_seconds':duration,'duration_display':'3:28.233','frame_count':TOTAL,'resolution':'1920x1080','fps':'30/1','codec':v['codec_name'],'pixel_format':v['pix_fmt'],'audio_stream':False,'full_decode_pass':True,
  'replaced_interval':{'start_frame':START,'end_frame_exclusive':END,'start_seconds':START/FPS,'end_seconds':END/FPS,'length_frames':LENGTH,'length_seconds':LENGTH/FPS},
  'raw_capture':record(RAW),'selected_raw_interval':{'start_frame':begin,'end_frame_exclusive':finish,'start_seconds':begin/FPS,'end_seconds':finish/FPS},
  'framing':cap['framing'],'native_browser_page_scale':2,'image_model_calls':0,'Veo_calls':0,'zero_image_model_calls_basis':cap['zero_image_model_calls_basis'],
  'old_submission':record(BACKUP),'old_desktop_copy':record(DESKBACKUP),'outside_inserted_segment':{'method':'Every decoded YUV420 frame MD5, v6 selected video vs v7 candidate','compared_frames':len(outside),'changed_frames':len(mismatches),'PASS':not mismatches,'first_frame_range':[0,START],'last_frame_range':[END,TOTAL]},
  'captions':{'cue_count':len(cues),'active_cue_count':sum(bool(c['text'])for c in cues),'content_and_timing_identical_v6':sha(cues_path)==sha(OUT/'track_i_submission_captions.json'),'caption_script_identical_v6':sha(ROOT/'reports/final_v6/track_c_submission_caption_script.txt')==sha(OUT/'track_i_submission_caption_script.txt'),'new_content_added':False},
  'frames':frame_rows,'ffprobe':info,'measured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 (OUT/'track_i_video_facts.json').write_text(json.dumps(facts,indent=2)+'\n')
 print(json.dumps({k:facts[k]for k in ['status','candidate','duration_seconds','outside_inserted_segment','captions']},indent=2),flush=True)
if __name__=='__main__':main()
