"""Independent read-only QA of new submission MP4. No application/network writes.
Writes sanitized audit evidence only under this directory; never edits a video.
"""
from pathlib import Path
from PIL import Image
import numpy as np
import hashlib,io,json,re,subprocess,datetime
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
FINAL=ROOT/'demo/preflight_demo_submission_3m.mp4';BACKUP=ROOT/'demo/preflight_demo_final.mp4'
SHA_OLD='4bbe0168a40156c06718c53df736ecd90e2314b0539629bed0cc3fa947bdda03'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def norm(x):return ' '.join(x.replace('\\n',' ').split())
def load(p):return json.loads((ROOT/p).read_text())
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))
def frame(path,seconds,out=None):
 b=subprocess.check_output(['ffmpeg','-v','error','-ss',f'{seconds:.9f}','-i',str(path),'-frames:v','1','-f','image2pipe','-c:v','png','pipe:1'])
 if out:out.write_bytes(b)
 return Image.open(io.BytesIO(b)).convert('RGB')
def main():
 facts=load('reports/final_v6/track_c_submission_video_facts.json')
 cues=load('reports/final_v6/track_c_submission_captions.json');old=load('reports/final_v5/track_c_captions.json')
 cap=load('reports/final_v6/track_c_supplement_capture.json')
 assert FINAL.exists() and facts['sha256']==sha(FINAL)
 desktop=Path(facts['desktop_upload_copy']);p=probe(FINAL);v=next(s for s in p['streams'] if s['codec_type']=='video')
 dur=float(p['format']['duration']);fps=v['avg_frame_rate'];nframes=int(v['nb_frames']);audio=any(s['codec_type']=='audio' for s in p['streams'])
 native={'duration_seconds':dur,'within_human_accepted_190_to_215':190<=dur<=215,'resolution':[v['width'],v['height']],'fps':fps,'codec':v['codec_name'],'pixel_format':v.get('pix_fmt'),'frame_count':nframes,'audio_stream':audio,'loudness_lufs':None if not audio else 'not measured'}
 native['PASS']=native['within_human_accepted_190_to_215'] and native['resolution']==[1920,1080] and fps=='30/1' and v['codec_name']=='h264' and not audio and abs(nframes/30-dur)<.00001
 dec=subprocess.run(['ffmpeg','-v','error','-i',str(FINAL),'-f','null','-'],capture_output=True,text=True)
 decode={'exit_code':dec.returncode,'stderr':dec.stderr,'PASS':dec.returncode==0 and not dec.stderr}
 inherited=[c for c in cues if c.get('source')=='original v5 burned captions'];added=[c for c in cues if c.get('source')=='new real production capture']
 original_exact=[c['text'] for c in inherited]==[c['text'] for c in old]
 script=(ROOT/'reports/final_v5/track_c_caption_script.txt').read_text()
 source_reconstructed=norm(' '.join(c['text'] for c in old if c['text']))==norm(script)
 assert original_exact and source_reconstructed and len(added)==3
 insertion=80.;extra=facts['new_segment_raw_duration_seconds']
 timeline_ok=(cues[0]['start_frame']==0 and cues[-1]['end_frame']==nframes and all(a['end_frame']==b['start_frame'] for a,b in zip(cues,cues[1:])))
 offset_ok=all(c['start_frame']==o['start_frame']+(round(extra*30) if o['start_frame']>=2400 else 0) and c['end_frame']==o['end_frame']+(round(extra*30) if o['start_frame']>=2400 else 0) for c,o in zip(inherited,old))
 caption_rows=[]
 for index,c in enumerate(cues):
  if not c['text']:continue
  midpoint=(c['start_frame']+c['end_frame'])//2;seconds=midpoint/30
  image=frame(FINAL,seconds);a=np.asarray(image,dtype=np.int16);asset=Image.open(c['asset']).convert('RGBA');t=np.asarray(asset)
  glyph=(t[:,:,3]>=250)&(t[:,:,0]>=240)&(t[:,:,1]>=240)&(t[:,:,2]>=230)
  dark=(t[:,:,3]>=240)&(t[:,:,0]<40)&(t[:,:,1]<80)&(t[:,:,2]<90)
  assert glyph.sum()>100 and dark.sum()>500
  bright=float((a[:,:,0][glyph]>200).mean());median=float(np.median(a[:,:,0][dark]));passed=bright>.95 and median<80
  caption_rows.append({'cue_index':index,'sample_frame':midpoint,'sample_seconds':seconds,'source':c['source'],'text':c['text'],'font_px':c['font_px'],'line_count':len(c['lines']),'expected_glyph_count':int(glyph.sum()),'bright_glyph_fraction':bright,'caption_background_median_red':median,'PASS':passed})
  if c in added: image.save(OUT/f'new_caption_midpoint_{added.index(c)+1}.png')
 # Read independently decoded full-frame comparisons at representative preserved beats.
 preserved=[]
 for oldtime in [5,30,70,79.5,80.5,100,130,145,171]:
  newtime=oldtime+(extra if oldtime>=80 else 0)
  a=np.asarray(frame(BACKUP,oldtime),dtype=np.int16);b=np.asarray(frame(FINAL,newtime),dtype=np.int16)
  mae=float(np.abs(a-b).mean());f95=float((np.abs(a-b)<=20).mean())
  preserved.append({'backup_seconds':oldtime,'new_seconds':newtime,'mean_abs_channel_difference':mae,'fraction_within20_per_channel':f95,'PASS':mae<8 and f95>.95})
 checkframes=[]
 for sec in [5,70,95,100,102,110,140,180]:
  path=OUT/f'check_{sec:03d}s.png';im=frame(FINAL,sec,path)
  checkframes.append({'seconds':sec,'path':str(path.relative_to(ROOT)),'sha256':sha(path),'dimensions':list(im.size)})
 # Source/UI/network evidence without printing tokens, headers, sessions or raw cloud identifiers.
 src=(ROOT/'app.py').read_text();guard=src.index('if not sample and not service.state.preview_live_enabled:');provider=src.index('generated = await provider.generate(body.prompt)');counter_hardcoded='"generations": 0,' in src
 net=[{'method':r['method'],'path':r['path'],'status':r['status'],'rewrite_source':r.get('observed_response',{}).get('rewrite_source'),'detail':r.get('observed_response',{}).get('detail')} for r in cap['take']['network'] if r['path'] in ['/api/status','/preflight','/preview','/postcheck']]
 posts=[r for r in net if r['method']=='POST'];expected_detail='Live stills are limited to the sample prompts during judging — shared Gemini image capacity. The risk check still works.'
 network_ok=len(posts)==2 and posts[0]['path']=='/preflight' and posts[0]['status']==200 and posts[0]['rewrite_source']=='live' and posts[1]['path']=='/preview' and posts[1]['status']==503 and posts[1]['detail']==expected_detail
 response=cap['preflight_response']; own_prompt=cap['prompt'];samples=cap['status_before']['sample_prompts']
 rewrite_ok=response['rewrite_source']=='live' and response['rewrite_status']=='improved' and response['p_fail_after']<response['p_fail_before'] and own_prompt not in samples
 counter={'visible_in_app_before':'NOT SHOWN','visible_in_app_after':'NOT SHOWN','status_generations_before':cap['counter_before'],'status_generations_after':cap['counter_after'],'status_field_hardcoded_in_source':counter_hardcoded,'is_a_cumulative_meter':False,'image_model_calls_for_this_recorded_typed_preview':0,'zero_image_basis':'Recorded single non-sample /preview returned exact HTTP503 limited copy while preview_mode=samples; inspected source guard rejects it before provider.generate. This is request-path evidence, not a cumulative usage counter.','source_guard_precedes_provider':guard<provider,'source_file_sha256':sha(ROOT/'app.py'),'network':net,'PASS':network_ok and rewrite_ok and guard<provider and counter_hardcoded and cap['status_before']['preview_mode']==cap['status_after']['preview_mode']=='samples'}
 olddesktop=Path.home()/'Desktop/UPLOAD_THIS_Preflight_AIBC2026_2m52s.mp4'
 identities={'final_path':str(FINAL),'final_bytes':FINAL.stat().st_size,'final_sha256':sha(FINAL),'desktop_copy':str(desktop),'desktop_copy_sha256':sha(desktop),'desktop_copy_bytes':desktop.stat().st_size,'copy_matches':sha(desktop)==sha(FINAL),'backup_sha256':sha(BACKUP),'backup_original_sha256_expected':SHA_OLD,'backup_unchanged':sha(BACKUP)==SHA_OLD,'backup_desktop_sha256':sha(olddesktop),'backup_desktop_unchanged':sha(olddesktop)==SHA_OLD}
 caption={'source_C2_reconstructed_exact':source_reconstructed,'all_v5_cues_text_and_order_exact':original_exact,'old_cue_count':len(old),'old_active_cue_count':sum(bool(c['text'])for c in old),'new_cue_count':len(added),'new_captions':[c['text'] for c in added],'new_caption_numeric_digits':re.findall(r'\d+',' '.join(c['text']for c in added)),'timeline_contiguous':timeline_ok,'inherited_frame_offsets_exact':offset_ok,'all_active_cues_checked':len(caption_rows),'all_active_cues_burned_PASS':all(c['PASS']for c in caption_rows),'minimum_font_px':min(c['font_px']for c in cues),'max_lines':max(len(c['lines'])for c in cues),'midpoint_method':'Actual exported MP4 frame at every active cue midpoint; expected alpha-backed caption asset glyph pixels must be >95% bright and pill background median red<80.','rows':caption_rows,'PASS':all([source_reconstructed,original_exact,len(added)==3,timeline_ok,offset_ok,all(c['PASS']for c in caption_rows),not re.findall(r'\d+',' '.join(c['text']for c in added))])}
 (OUT/'native_and_identity.json').write_text(json.dumps({'native':native,'identity':identities,'full_decode':decode},indent=2)+'\n')
 (OUT/'caption_burned_checks.json').write_text(json.dumps(caption,indent=2)+'\n')
 (OUT/'production_request_evidence.json').write_text(json.dumps(counter,indent=2)+'\n')
 (OUT/'preserved_beat_comparisons.json').write_text(json.dumps(preserved,indent=2)+'\n')
 result={'auditor':'Independent deck agent, read-only video audit','checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'native':native,'identity':identities,'full_decode':decode,'captions':{k:v for k,v in caption.items() if k!='rows'},'source_and_network_evidence':counter,'preserved_beat_comparisons':preserved,'check_frames':checkframes,'visual_review':'PENDING - inspect actual saved frames before final PASS','visual_review_PASS':False}
 result['automated_PASS']=all([native['PASS'],decode['PASS'],caption['PASS'],counter['PASS'],identities['copy_matches'],identities['backup_unchanged'],identities['backup_desktop_unchanged'],all(x['PASS']for x in preserved)])
 (OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'automated_PASS':result['automated_PASS'],'native':native,'identity':identities,'active_caption_midpoints':len(caption_rows),'caption_PASS':caption['PASS'],'failed_caption_indices':[c['cue_index']for c in caption_rows if not c['PASS']],'source_network_PASS':counter['PASS'],'preserved_beats_PASS':all(x['PASS']for x in preserved)},indent=2))
 if not result['automated_PASS']:raise SystemExit(1)
if __name__=='__main__':main()
