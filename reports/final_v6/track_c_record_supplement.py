#!/usr/bin/env python3
"""Capture one authorized own-prompt segment on production.
Imports the existing scripts/record_demo.py Take, cursor and native video helpers;
uses a custom safe sequence because its --live-prompt branch generates an image.
No mocks, response/DOM replacement, clipboard reads, or image generation.
"""
from pathlib import Path
import asyncio, hashlib, json, sys, time
from types import SimpleNamespace
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.record_demo import Take, CURSOR_SCRIPT, async_playwright, run, probe, video_valid
URL='https://preflight-jcgro45veq-as.a.run.app'
PROMPT='a dog catching a frisbee on a beach at sunset'
LIMITED='Live stills are limited to the sample prompts during judging — shared Gemini image capacity. The risk check still works.'
OUT=ROOT/'demo/submission_supplement_v6'
REPORT=ROOT/'reports/final_v6/track_c_supplement_capture.json'
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
async def main():
 OUT.mkdir(exist_ok=False)
 log={'url':URL,'prompt':PROMPT,'started_at_utc':datetime.now(timezone.utc).isoformat(),
      'capture_base_script':'scripts/record_demo.py','capture_base_script_sha256':digest(ROOT/'scripts/record_demo.py'),
      'policy':'one own-prompt check; one preview click; no retries; no generated image; no UI or response replacement',
      'generations_counter_limitation':'/api/status.generations is hard-coded 0 in current source; no visible UI usage counter exists. It is not cumulative image accounting.'}
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True)
  context=await browser.new_context(viewport={'width':1920,'height':1080},device_scale_factor=1,
    record_video_dir=str(OUT/'browser'),record_video_size={'width':1920,'height':1080},
    locale='en-US',timezone_id='Asia/Seoul')
  await context.add_init_script(CURSOR_SCRIPT)
  page=await context.new_page();page.set_default_timeout(6000); video=page.video
  args=SimpleNamespace(preview_mode='on',warm_receipt=None,warmed_prompts=set())
  take=Take(page,OUT,1,time.monotonic(),args)
  try:
   async def home():
    r=await page.goto(URL,wait_until='domcontentloaded',timeout=30000)
    assert r.status==200
    await page.locator('.mode-pill.cloud').wait_for(state='visible',timeout=20000)
    status=await page.evaluate('() => window.preflightStatus')
    assert status['preview_mode']=='samples' and PROMPT not in status['sample_prompts']
    log['status_before']=status
    await take.frame('production_home_before')
   assert await take.step('production_home_before',home,1)
   assert await take.step('typed_own_prompt_and_check',lambda:take.preflight(PROMPT))
   result=take.preflight_result
   log['preflight_response']={k:v for k,v in result.items() if k not in ('session_id','session','agent_session_id','token')}
   assert result.get('rewrite_source')=='live', 'Own-prompt rewrite source was not live'
   assert result['rewritten_prompt'] not in log['status_before']['sample_prompts'], 'Returned rewrite unexpectedly matches a sample'
   assert result.get('rewrite_status')=='improved', 'No accepted rewrite is available; retain observed footage and stop'
   async def rewrite():
    await take.scroll_to('.better-card',120)
    await page.locator('.rewritten-prompt').wait_for(state='visible')
    text=await page.locator('.rewritten-prompt').inner_text()
    line=await page.locator('.rewrite-comparison').inner_text()
    assert text==result['rewritten_prompt']
    assert 0<=result['p_fail_after']<result['p_fail_before']<=1
    await take.frame('own_prompt_live_rewrite')
    return {'rewritten_prompt':text,'risk_line':line,'rewrite_source':result['rewrite_source']}
   assert await take.step('show_live_rewrite_and_risk_line',rewrite,5)
   async def preview():
    await take.scroll_to('.preview-controls',180)
    async with page.expect_response(lambda r:r.request.method=='POST' and r.url.split('?')[0].endswith('/preview'),timeout=10000) as waiting:
     await take.click('.preview-button')
    r=await waiting.value; body=await r.json()
    assert r.status==503 and body.get('detail')==LIMITED,(r.status,body)
    error=page.locator('.preview-controls .form-error')
    await error.wait_for(state='visible')
    assert (await error.inner_text()).strip()==LIMITED
    await take.frame('own_prompt_preview_limited')
    return {'http_status':r.status,'detail':body['detail'],'request_prompt_is_sample':False,'image_model_calls':0,
            'zero_image_basis':'samples mode + non-sample request rejected at app.py pre-provider guard'}
   assert await take.step('click_preview_and_show_real_limited_message',preview,5)
   async def details():
    await take.scroll_to('.risk-card',120)
    await take.click('.risk-card details > summary')
    assert await page.locator('.risk-card details[open]').count()==1
    await take.scroll_to('.risk-card details',170)
    text=await page.locator('#score-explanation').inner_text()
    assert '1,911' in text and '0.67' in text
    await take.frame('own_prompt_score_explanation')
    return {'visible_explanation':text}
   assert await take.step('open_what_this_score_is',details)
   await take.at(35)
   after=await context.request.get(URL+'/api/status',timeout=15000)
   log['status_after']=await after.json()
   assert log['status_after']['preview_mode']=='samples'
   log['counter_before']=log['status_before']['generations'];log['counter_after']=log['status_after']['generations']
   await take.frame('production_score_explanation_final')
   log['sequence_pass']=True
  except Exception as e:
   log['sequence_pass']=False;log['error']=f'{type(e).__name__}: {e}'
   await take.pause(2)
  finally:
   if take.network_tasks:
    await asyncio.wait_for(asyncio.gather(*list(take.network_tasks),return_exceptions=True),timeout=3)
   log['take']=take.log
   log['sequence_wall_seconds']=take.offset()
   await context.close()
   source=Path(await video.path());output=OUT/'preflight_demo_own_prompt_raw.mp4'
   run(['ffmpeg','-v','error','-y','-i',str(source),'-an','-vf','fps=30','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(output)])
   info=probe(output)
   run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'])
   log['video']={'path':str(output),'source':str(source),'ffprobe':info,'duration_seconds':float(info['format']['duration']),
     'bytes':output.stat().st_size,'sha256':digest(output),'full_decode_pass':True,'format_pass':video_valid(info)}
   log['capture_base_script_sha256_after']=digest(ROOT/'scripts/record_demo.py')
   log['image_model_calls']=0 if log.get('sequence_pass') else None
   REPORT.write_text(json.dumps(log,indent=2,ensure_ascii=False)+'\n')
   await browser.close()
 print(json.dumps({k:log.get(k) for k in ['sequence_pass','error','counter_before','counter_after','image_model_calls','sequence_wall_seconds','video']},indent=2),flush=True)
 if not log.get('sequence_pass'):sys.exit(1)
if __name__=='__main__':asyncio.run(main())
