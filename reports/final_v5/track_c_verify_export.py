#!/usr/bin/env python3
"""Decode the real export and check every caption cue, the intentional gap,
required PNGs, native streams, source integrity, and the complete bitstream.
Run after track_c_render.py. No network or production application calls.
"""
from pathlib import Path
from PIL import Image
import hashlib, io, json, statistics, subprocess

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/'reports/final_v5'
FINAL=ROOT/'demo/preflight_demo_final.mp4'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def frame(time):
    data=subprocess.check_output(['ffmpeg','-hide_banner','-loglevel','error','-ss',str(time),'-i',str(FINAL),'-frames:v','1','-f','image2pipe','-c:v','png','pipe:1'])
    return Image.open(io.BytesIO(data)).convert('RGB')

def main():
    cues=json.loads((REPORT/'track_c_captions.json').read_text())
    results=[]
    for cue in cues:
        t=(cue['start']+cue['end'])/2
        actual=frame(t); pixels=actual.load()
        if not cue['text']:
            red=[pixels[x,y][0] for y in range(951,1039,5) for x in range(300,1620,5)]
            med=statistics.median(red)
            results.append({'time_seconds':t,'text':'','expected':'Intentional transparent gap under unspoken third quote','median_red':med,'PASS':med>200})
            continue
        template=Image.open(ROOT/'demo/final_assets'/Path(cue['asset']).name).convert('RGBA');mask=template.load()
        dark=[];glyph=[]
        for y in range(951,1039,2):
            for x in range(100,1820,2):
                r,g,b,a=mask[x,y]
                if (r,g,b,a)==(20,43,49,242):dark.append(pixels[x,y][0])
                if r>240 and g>240 and b>230 and a==255:glyph.append(pixels[x,y][0]>200)
        assert dark and glyph
        median=statistics.median(dark);match=sum(glyph)/len(glyph)
        results.append({'time_seconds':t,'text':cue['text'],'caption_background_median_red':median,'expected_glyph_bright_fraction':match,'PASS':median<75 and match>.95})
    decode=subprocess.run(['ffmpeg','-hide_banner','-v','error','-i',str(FINAL),'-f','null','-'],capture_output=True,text=True)
    decode_fact={'command':'ffmpeg -hide_banner -v error -i demo/preflight_demo_final.mp4 -f null -','exit_code':decode.returncode,'stdout':decode.stdout,'stderr':decode.stderr,'PASS':decode.returncode==0 and not decode.stderr}
    (REPORT/'track_c_full_decode.json').write_text(json.dumps(decode_fact,indent=2)+'\n')
    facts=json.loads((REPORT/'track_c_video_facts.json').read_text())
    metadata=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(FINAL)]))
    video=next(s for s in metadata['streams']if s['codec_type']=='video')
    native=(video['codec_name']=='h264' and video['width']==1920 and video['height']==1080 and video['avg_frame_rate']=='30/1' and float(metadata['format']['duration'])==172 and not any(s['codec_type']=='audio'for s in metadata['streams']))
    images=[]
    for f in facts['frames']:
        p=ROOT/f['path'];im=Image.open(p);im.verify()
        images.append({'time_seconds':f['time_seconds'],'path':f['path'],'PASS':p.stat().st_size==f['byte_size'] and digest(p)==f['sha256'] and im.size==(1920,1080)})
    current_hash=digest(FINAL)
    raw_current=digest(ROOT/'demo/preflight_demo_raw.mp4')
    result={'final_sha256':current_hash,'facts_hash_matches':current_hash==facts['sha256'],'raw_unchanged':raw_current==facts['raw_sha256_before']==facts['raw_sha256_after'],'native_specs_PASS':native,'caption_check_method':'Actual final-frame decode at each cue midpoint; dark caption background and >95% expected bright glyph pixels. Blank gap must show plain light card.','caption_cues_checked':len(results),'caption_nonblank_checked':sum(bool(c['text'])for c in cues),'caption_cues_PASS':all(r['PASS']for r in results),'caption_cues':results,'requested_frames':images,'full_decode_PASS':decode_fact['PASS']}
    result['PASS']=all([result['facts_hash_matches'],result['raw_unchanged'],native,result['caption_cues_PASS'],all(i['PASS']for i in images),decode_fact['PASS']])
    (REPORT/'track_c_overlay_check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in ['caption_cues','requested_frames']},indent=2))
    if not result['PASS']:raise SystemExit('Export verification FAIL; inspect track_c_overlay_check.json')

if __name__=='__main__':main()
