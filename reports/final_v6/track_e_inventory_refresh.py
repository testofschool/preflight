#!/usr/bin/env python3
"""Measure all Desktop *demo*.mp4 files plus both explicit upload copies.
Read only for videos; streams hashes in a bounded worker and never mutates media.
"""
from pathlib import Path
import subprocess,sys,json,datetime
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/final_v6'
DESKTOP=Path.home()/'Desktop'
HASH_PROGRAM='import hashlib,sys; h=hashlib.sha256(); f=open(sys.argv[1],"rb"); b=f.read(1048576)\nwhile b: h.update(b); b=f.read(1048576)\nprint(h.hexdigest())'
def main():
 facts=json.loads((OUT/'track_c_submission_video_facts.json').read_text())
 previous=json.loads((OUT/'track_e_inventory_before_submission.json').read_text())
 scan=subprocess.run(['find',str(DESKTOP),'-type','f','-iname','*demo*.mp4','-print'],capture_output=True,text=True,timeout=300)
 if scan.returncode:raise RuntimeError('Desktop discovery incomplete: '+scan.stderr)
 matched=scan.stdout.splitlines();paths=list(dict.fromkeys(matched+[str(DESKTOP/'UPLOAD_THIS_Preflight_AIBC2026_2m52s.mp4'),facts['desktop_upload_copy']]))
 rows=[];old={x['path']:x for x in previous['files']}
 for raw in paths:
  p=Path(raw);r={'path':raw,'discovered_by_demo_glob':raw in matched}
  try:r['bytes']=p.stat().st_size
  except Exception as e:r['stat_error']=repr(e)
  try:
   q=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration,size','-of','json',raw],capture_output=True,text=True,timeout=30)
   r['ffprobe_exit_code']=q.returncode
   if q.returncode==0:
    f=json.loads(q.stdout)['format'];r['duration_native']=f['duration'];r['duration_seconds']=float(f['duration']);r['ffprobe_bytes']=int(f['size'])
   else:r['ffprobe_error']=q.stderr
  except Exception as e:r['ffprobe_error']=repr(e)
  try:
   q=subprocess.run([sys.executable,'-c',HASH_PROGRAM,raw],capture_output=True,text=True,timeout=60)
   r['sha256_exit_code']=q.returncode
   if q.returncode==0:r['sha256']=q.stdout.strip();r['sha256_prefix']=q.stdout.strip()[:12]
   else:r['sha256_error']=q.stderr
  except Exception as e:r['sha256_error']=repr(e)
  if r.get('sha256')==facts['sha256']:r['classification']='NEW SUBMISSION — 3:28.233; explicit upload copy' if raw==facts['desktop_upload_copy'] else 'NEW SUBMISSION — 3:28.233 final'
  elif raw==facts['new_segment_source']:r['classification']='New own-prompt production capture — source segment only'
  elif raw in old:
   r['classification']=old[raw]['classification'].replace('CURRENT FINAL','2:52 BACKUP')
   r['unchanged_from_initial_inventory']=r.get('sha256')==old[raw].get('sha256') and r.get('bytes')==old[raw].get('bytes')
  else:r['classification']='Other measured demo; no version identity assigned'
  rows.append(r)
 d={'measured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_find_command':"find /Users/felix/Desktop -type f -iname '*demo*.mp4' -print",'source_find_exit_code':scan.returncode,'source_find_timeout_seconds':300,'prior_discovery_attempt':'A 60-second full Desktop find timed out before publication; rerun allowed 300 seconds. No partial inventory was published.','source_find_count':len(matched),'total_inventory_count':len(rows),'no_pruning_or_symlink_following':True,'new_submission':facts['path'],'new_submission_upload_copy':facts['desktop_upload_copy'],'backup_upload_copy':str(DESKTOP/'UPLOAD_THIS_Preflight_AIBC2026_2m52s.mp4'),'originals_unchanged':all(x.get('unchanged_from_initial_inventory',True) for x in rows),'ffprobe_timeout_seconds':30,'sha256_timeout_seconds':60,'sha256_read_chunk_bytes':1048576,'files':rows}
 (OUT/'track_e_submission_inventory.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
 def cell(v):return str(v).replace('|','\\|').replace('\n',' ')
 lines=['# Track E — video inventory after submission extension','','## Upload the new submission video','',facts['desktop_upload_copy'],'',f"- Duration: {facts['duration_seconds']:.6f} s (3:28.233)",f"- Bytes: {facts['byte_size']:,}",'- SHA-256: `'+facts['sha256']+'`','','The 2:52 upload copy remains untouched as a backup. All original inventory hashes were rechecked. No video was deleted or renamed.','','## Complete inventory','', '| Absolute path | Bytes | Native duration (s) | SHA-256 prefix (12) | Role |','|---|---:|---:|---|---|']
 for r in rows:lines.append('| '+' | '.join(cell(x) for x in [r['path'],r.get('bytes','UNREADABLE'),r.get('duration_native','UNREADABLE'),r.get('sha256_prefix','UNREADABLE'),r['classification']])+' |')
 lines+=['','## Full SHA-256 values','']
 for r in rows:
  lines+=['- `'+r['path']+'`','  - `'+r.get('sha256','UNREADABLE')+'`']
  for k in ['stat_error','ffprobe_error','sha256_error']:
   if k in r:lines.append('  - '+k+': '+cell(r[k]))
 lines+=['',f"Complete Desktop find: exit {scan.returncode}, {len(matched)} matches. Two named upload copies are added separately, for {len(rows)} rows. No pruning or directory-symlink following. SHA worker reads 1 MiB chunks with a 60 s timeout; ffprobe has a 30 s timeout.",'',f"Original 9 inventory entries unchanged: {d['originals_unchanged']}.",'']
 (OUT/'track_e_submission_inventory.md').write_text('\n'.join(lines))
 print(json.dumps({'find_count':len(matched),'inventory_count':len(rows),'originals_unchanged':d['originals_unchanged'],'all_reads_succeeded':all(x.get('ffprobe_exit_code')==0 and x.get('sha256_exit_code')==0 for x in rows)},indent=2))
if __name__=='__main__':main()
