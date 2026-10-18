#!/usr/bin/env python3
"""Promote the already audited compact Track I export, preserving prior videos."""
from pathlib import Path
import hashlib,json,shutil,datetime
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/final_v7'
FINAL=ROOT/'demo/preflight_demo_submission_3m.mp4';DESKTOP=Path.home()/'Desktop/UPLOAD_THIS_Preflight_AIBC2026_3m28s.mp4'
OLD='6ebd825cbe8cbc1810c81d9592ac4e21028340a4ed92dbafb840cd5d684703a2'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 facts=json.loads((OUT/'track_i_video_facts.json').read_text());qa=json.loads((OUT/'track_i_qa.json').read_text())
 candidate=Path(facts['candidate']['path']);expected=facts['candidate']['sha256']
 assert candidate.name=='submission_candidate_v4.mp4' and sha(candidate)==expected
 assert facts['full_decode_pass'] and facts['outside_inserted_segment']['PASS'] and qa['automated_PASS']
 approval=json.loads((OUT/'track_i_review_gate.json').read_text())
 assert approval['candidate_sha256']==expected and approval['independent_review_PASS'] and approval['parent_target_frame_visual_PASS']
 assert sha(FINAL)==sha(DESKTOP)==OLD,'Mismatch -> STOP: selected v6 targets changed'
 assert sha(ROOT/'demo/preflight_demo_submission_3m_before_v7_20261018.mp4')==OLD
 assert sha(Path.home()/'Desktop/Preflight_AIBC2026_3m28s_backup_before_v7_20261018.mp4')==OLD
 oldmanifest=json.loads((OUT/'track_i_old_video_manifest.json').read_text());exceptions={str(FINAL),str(DESKTOP)}
 preserved=[{'path':r['path'],'sha256_before':r['sha256'],'sha256_after':sha(Path(r['path'])),'unchanged':r['sha256']==sha(Path(r['path']))}for r in oldmanifest if r['path']not in exceptions]
 assert all(r['unchanged']for r in preserved)
 shutil.copy2(candidate,FINAL);shutil.copy2(candidate,DESKTOP)
 assert sha(FINAL)==sha(DESKTOP)==expected
 facts.update(status='PASS - PROMOTED TO FINAL AND DESKTOP UPLOAD COPY',selected_video={'path':str(FINAL),'sha256':sha(FINAL),'bytes':FINAL.stat().st_size,'duration_seconds':facts['duration_seconds']},desktop_upload_copy=str(DESKTOP),desktop_upload_copy_sha256=sha(DESKTOP),desktop_upload_copy_bytes=DESKTOP.stat().st_size,promoted_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),old_video_preservation={'old_video_count_including_replaced_targets':len(oldmanifest),'unreplaced_originals_verified_unchanged':len(preserved),'replaced_targets_backed_up':True,'backups':[facts['old_submission'],facts['old_desktop_copy']],'rows':preserved},human_full_video_acceptance='PENDING Felix; technical and selected-frame reviews passed')
 (OUT/'track_i_video_facts.json').write_text(json.dumps(facts,indent=2)+'\n')
 print(json.dumps({k:facts[k]for k in ['status','selected_video','desktop_upload_copy','desktop_upload_copy_sha256','desktop_upload_copy_bytes','duration_seconds']},indent=2),flush=True)
if __name__=='__main__':main()
