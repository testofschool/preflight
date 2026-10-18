#!/usr/bin/env python3
"""Read-only verification of candidate video; all active caption midpoint checks."""
from pathlib import Path
from PIL import Image
import numpy as np
import hashlib,io,json,subprocess,re,datetime
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/final_v7';FINAL=ROOT/'demo/submission_supplement_v7/submission_candidate_v4.mp4'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def frame(sec):
 b=subprocess.check_output(['ffmpeg','-v','error','-ss',f'{sec:.9f}','-i',str(FINAL),'-frames:v','1','-f','image2pipe','-c:v','png','pipe:1'])
 return Image.open(io.BytesIO(b)).convert('RGB')
def main():
 facts=json.loads((OUT/'track_i_video_facts.json').read_text());assert sha(FINAL)==facts['candidate']['sha256']
 cues=json.loads((OUT/'track_i_submission_captions.json').read_text());old=json.loads((ROOT/'reports/final_v6/track_c_submission_captions.json').read_text())
 assert cues==old
 timeline=cues[0]['start_frame']==0 and cues[-1]['end_frame']==facts['frame_count'] and all(a['end_frame']==b['start_frame']for a,b in zip(cues,cues[1:]))
 rows=[]
 for i,c in enumerate(cues):
  if not c['text']:continue
  mid=(c['start_frame']+c['end_frame'])//2;sec=mid/30
  im=frame(sec);a=np.asarray(im,dtype=np.int16);t=np.asarray(Image.open(c['asset']).convert('RGBA'))
  glyph=(t[:,:,3]>=250)&(t[:,:,0]>=240)&(t[:,:,1]>=240)&(t[:,:,2]>=230)
  dark=(t[:,:,3]>=240)&(t[:,:,0]<40)&(t[:,:,1]<80)&(t[:,:,2]<90)
  bright=float((a[:,:,0][glyph]>200).mean());median=float(np.median(a[:,:,0][dark]));passed=bright>.95 and median<80
  rows.append({'cue_index':i,'seconds':sec,'text':c['text'],'bright_glyph_fraction':bright,'background_median_red':median,'PASS':passed})
  if c.get('source')=='new real production capture':im.save(OUT/f'track_i_caption_midpoint_{i}.png')
 cap=json.loads((OUT/'track_i_capture.json').read_text());net=[r for r in cap['take']['network']if r['method']=='POST']
 src=(ROOT/'app.py').read_text();guard=src.index('if not sample and not service.state.preview_live_enabled:');provider=src.index('generated = await provider.generate(body.prompt)')
 network=len(net)==2 and net[0]['path']=='/preflight' and net[0]['status']==200 and net[1]['path']=='/preview' and net[1]['status']==503
 mode=cap['status_before']['preview_mode']==cap['status_after']['preview_mode']=='samples'
 immutable=all(sha(ROOT/k)==v['sha256']for k,v in cap['immutable_source_evidence'].items())
 result={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'video_sha256':sha(FINAL),'caption_cues_exactly_equal_v6':cues==old,'timeline_contiguous':timeline,'caption_active_cues_checked':len(rows),'all_caption_midpoints_PASS':all(r['PASS']for r in rows),'rows':rows,
 'production_network':{'POSTs':[{'path':r['path'],'status':r['status'],'response':r.get('observed_response',{})}for r in net],'network_PASS':network,'preview_mode_before_after_samples':mode,'pre_provider_reject_guard_PASS':guard<provider,'image_model_calls':0,'Veo_calls':0,'counter_caveat':'status.generations is hard-coded0; zero image calls is request-path evidence, not a cumulative usage meter.'},'runtime_source_hashes_unchanged':immutable,'outside_every_frame_exact':facts['outside_inserted_segment']['PASS']}
 result['automated_PASS']=all([cues==old,timeline,all(r['PASS']for r in rows),network,mode,guard<provider,immutable,facts['outside_inserted_segment']['PASS'],facts['full_decode_pass']])
 (OUT/'track_i_qa.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ('rows','production_network')},indent=2),flush=True)
 assert result['automated_PASS']
if __name__=='__main__':main()
