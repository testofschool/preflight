#!/usr/bin/env python3
"""Reproduce the authorized Track C export without modifying the raw recording.
Requires ffmpeg/ffprobe and Pillow. No model, network, TTS, or upload calls.
Run from any directory: python3 reports/final_v5/track_c_render.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, json, math, re, subprocess

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "demo/final_assets"
CHECK = ROOT / "demo/final_check"
REPORT = ROOT / "reports/final_v5"
RAW = ROOT / "demo/preflight_demo_raw.mp4"
FINAL = ROOT / "demo/preflight_demo_final.mp4"
EXPECTED_RAW_SHA = "d1f3772d1187ee7ce1aeed1e0efe3f432c09337e90cc0b7113b6ca37aa94ab78"
W, H, FPS, TOTAL = 1920, 1080, 30, 172
PAPER, INK, MUTED, LINE, WHITE, MINT, CORAL = "#f5f4ee", "#142b31", "#657276", "#d5dcd5", "#fffefa", "#dcf0e8", "#ef7f60"
SANS = "/System/Library/Fonts/HelveticaNeue.ttc"
MONO = "/System/Library/Fonts/Menlo.ttc"
SCRIPT = [
(0, 16, 'People who generate AI video pay per attempt. Here is what they say. "You still burn credits on the failed attempt." "Only one of the generations was usable." "I recommend a lo-res preview before having to spend actual credits."'),
(16, 22, "Preflight is that step before you pay."),
(22, 50, 'Paste a prompt. Preflight compares it with 1,911 human votes on earlier AI videos and returns a risk estimate, with the closest past prompts as evidence. For "a spoon and a laptop", the estimate is 46.8 percent.'),
(50, 60, "Then a Google ADK agent on Gemini rewrites the prompt and keeps the rewrite only if the estimated risk drops. Here it drops to 15.8 percent. Copy it and go."),
(60, 80, "Before paying about three dollars for an eight-second video, you can look at a still of the scene. For judging, the five sample prompts use saved stills: zero model calls, zero cost, and the label says so. In our tests, live image generation failed too often under shared capacity, so we did not put it in front of you."),
(80, 115, "After you generate, upload the clip. Gemini takes a second look at sampled frames, and its verdict is stored as separate feedback next to the human votes. It is a second pair of eyes, not a verdict."),
(115, 130, "Everything runs on Google Cloud: Cloud Run, Firestore, Gemini on Vertex AI, an ADK agent with Agent Platform Sessions."),
(130, 142, "The architecture: one prompt, a traceable check, tools for evidence and difficulty, Firestore as memory."),
(142, 156, "The limits are on the page. The risk score is a historical signal, held-out AUC 0.67, not a promise about today's models. Clip-review accuracy is not measured yet."),
(156, 172, "Built in Seoul by a producer who paid for these failures, tested from India. Preflight: know before you pay.")
]
# Phrase boundaries only; joining these strings must reproduce C.2 exactly.
PHRASES = [
["People who generate AI video pay per attempt. Here is what they say.", '"You still burn credits on the failed attempt."', '"Only one of the generations was usable."', '"I recommend a lo-res preview before having to spend actual credits."'],
["Preflight is that step before you pay."],
["Paste a prompt.", "Preflight compares it with 1,911 human votes on earlier AI videos", "and returns a risk estimate, with the closest past prompts as evidence.", 'For "a spoon and a laptop", the estimate is 46.8 percent.'],
["Then a Google ADK agent on Gemini rewrites the prompt", "and keeps the rewrite only if the estimated risk drops.", "Here it drops to 15.8 percent. Copy it and go."],
["Before paying about three dollars for an eight-second video,", "you can look at a still of the scene.", "For judging, the five sample prompts use saved stills:", "zero model calls, zero cost, and the label says so.", "In our tests, live image generation failed too often under shared capacity,", "so we did not put it in front of you."],
["After you generate, upload the clip.", "Gemini takes a second look at sampled frames,", "and its verdict is stored as separate feedback next to the human votes.", "It is a second pair of eyes, not a verdict."],
["Everything runs on Google Cloud: Cloud Run, Firestore,", "Gemini on Vertex AI, an ADK agent with Agent Platform Sessions."],
["The architecture: one prompt, a traceable check,", "tools for evidence and difficulty, Firestore as memory."],
["The limits are on the page.", "The risk score is a historical signal, held-out AUC 0.67,", "not a promise about today's models.", "Clip-review accuracy is not measured yet."],
["Built in Seoul by a producer who paid for these failures,", "tested from India. Preflight: know before you pay."]
]

def run(args):
    subprocess.run([str(a) for a in args], check=True, cwd=ROOT)

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def font(size,mono=False):
    return ImageFont.truetype(MONO if mono else SANS, size)

def wrap(draw,text,face,width):
    lines=[]
    current=""
    for word in text.split():
        test=(current+" "+word).strip()
        if current and draw.textlength(test,font=face)>width:
            lines.append(current); current=word
        else:
            current=test
    if current: lines.append(current)
    return lines

def text(draw,xy,value,size,fill=INK,width=None,align="left",spacing=12):
    face=font(size)
    value="\n".join(wrap(draw,value,face,width)) if width else value
    draw.multiline_text(xy,value,font=face,fill=fill,spacing=spacing,align=align)
    return value

def center(draw,value,y,size,width=1600,fill=INK):
    face=font(size)
    lines=wrap(draw,value,face,width)
    for i,line in enumerate(lines):
        length=draw.textlength(line,font=face)
        draw.text(((W-length)/2,y+i*(size+18)),line,font=face,fill=fill)
    return len(lines)*(size+18)

def base(label):
    im=Image.new("RGB",(W,H),PAPER); d=ImageDraw.Draw(im)
    d.line((90,94,128,94),fill=CORAL,width=5)
    d.text((150,75),label.upper(),font=font(26,True),fill=MUTED)
    d.line((90,170,1830,170),fill=LINE,width=2)
    return im,d

def save(im,name):
    path=ASSETS/name
    im.save(path)
    return path

def box(d,rect,title,body=(),color=MINT):
    d.rounded_rectangle(rect,14,fill=color,outline=LINE,width=2)
    x,y,x2,y2=rect
    text(d,(x+28,y+20),title,36,width=x2-x-56)
    yy=y+76
    for value in body:
        lines=text(d,(x+28,yy),value,28,MUTED,width=x2-x-56,spacing=8)
        yy+=(lines.count("\n")+1)*38

def arrow(d,a,b):
    d.line((*a,*b),fill=MUTED,width=4)
    angle=math.atan2(b[1]-a[1],b[0]-a[0]); n=17
    pts=[b,(b[0]-n*math.cos(angle-.5),b[1]-n*math.sin(angle-.5)),(b[0]-n*math.cos(angle+.5),b[1]-n*math.sin(angle+.5))]
    d.polygon(pts,fill=MUTED)

def ffconcat(path,items):
    # Durations are exact frame multiples, and the repeated terminal image is
    # clipped by -t. PNG packet timestamps otherwise use the concat 25 Hz default.
    lines=["ffconcat version 1.0"]
    for filename,duration in items:
        lines.extend(["file '"+str(filename)+"'", "option framerate 30", "duration "+format(duration,".9f")])
    lines.extend(["file '"+str(items[-1][0])+"'", "option framerate 30"])
    path.write_text("\n".join(lines)+"\n")

def static_video(manifest,out,duration):
    run(["ffmpeg","-hide_banner","-loglevel","warning","-y","-f","concat","-safe","0","-i",manifest,"-t",duration,"-an","-vf","fps=30,format=yuv420p","-c:v","libx264","-preset","fast","-crf","18","-threads","6","-movflags","+faststart",out])

def main():
    for p in (ASSETS,CHECK,REPORT):p.mkdir(parents=True,exist_ok=True)
    if sha(RAW)!=EXPECTED_RAW_SHA:raise SystemExit("Mismatch -> STOP: raw recording SHA-256")
    if list((ROOT/"demo").glob("voiceover.*")):
        raise SystemExit("Voiceover now present; STOP for alignment instead of silently ignoring it")
    quoted=[
    ("you still burn credits on the failed attempt", "Trustpilot · Runway review · Sept 2026"),
    ("Only one of the generations was usable for my purposes", "Trustpilot · Sept 2026"),
    ("I'm tired of wasting valuable credits on bad footage, I simply can't use", "Adobe Community"),
    ("I recommend a lo-res preview render before having to spend actual credits", "Adobe Community")]
    opening,d=base("Paying to find out")
    center(d,"People who generate AI video pay per attempt. Here is what they say.",365,72,1500)
    intro=[(save(opening,"intro_opening.png"),4)]
    for idx,(quote,source) in enumerate(quoted,1):
        im,d=base("Paying to find out")
        d.text((150,220),"“",font=font(150),fill=CORAL)
        center(d,quote,350,74,1450)
        center(d,source,730,28,1600,MUTED)
        intro.append((save(im,f"intro_quote_{idx}.png"),3))
    im,d=base("Before you pay")
    center(d,"Preflight",285,150)
    center(d,"Preflight — check an AI-video prompt before you pay to generate it.",505,66,1500)
    intro.append((save(im,"intro_title.png"),6))
    im,d=base("Architecture")
    text(d,(90,195),"One prompt. A traceable check.",60)
    box(d,(90,300,410,440),"Browser",[],WHITE)
    box(d,(500,300,1030,440),"Cloud Run",["FastAPI · asia-southeast1"],WHITE)
    box(d,(1120,300,1830,490),"Google ADK rewrite agent",["Gemini 3.5 Flash · Vertex AI", "Agent Platform Sessions"])
    arrow(d,(412,370),(494,370));arrow(d,(1032,370),(1112,370))
    box(d,(1120,545,1830,685),"Tools",["Nearest prompts + IRT difficulty"],WHITE)
    arrow(d,(1475,494),(1475,539))
    box(d,(90,495,1030,665),"Still preview / Clip review",["Gemini image model", "Gemini video understanding"],WHITE)
    box(d,(90,750,1830,890),"Cloud Firestore",["1,911 votes · IRT parameters · feedback · saved stills"])
    arrow(d,(1475,688),(1475,744));arrow(d,(560,668),(560,744));arrow(d,(765,444),(765,490))
    architecture=save(im,"outro_architecture.png")
    im,d=base("What we measured, and the limits")
    text(d,(90,195),"Evidence, with its limits in view.",60)
    for rect in [(90,300,935,555),(985,300,1830,555),(90,600,935,855),(985,600,1830,855)]:
        d.rounded_rectangle(rect,16,fill=WHITE,outline=LINE,width=2)
    text(d,(120,325),"Risk score",32,MUTED)
    text(d,(120,375),"Held-out AUC 0.67",60)
    text(d,(120,460),"Historical signal, not a calibrated probability for today's models.",32,MUTED,760)
    text(d,(1015,325),"Live image generation",32,MUTED)
    text(d,(1015,375),"Best 8/20",60)
    text(d,(1015,460),"60 test calls across three Gemini image models, under shared capacity.",32,MUTED,760)
    text(d,(120,625),"Judging: saved stills for the 5 samples",32,MUTED)
    text(d,(120,690),"0 model calls · $0.00",54)
    text(d,(120,780),"The saved stills are labelled on the page.",32,MUTED)
    text(d,(1015,625),"Clip review",32,MUTED)
    text(d,(1015,690),"Accuracy: not measured",50)
    text(d,(1015,780),"A second pair of eyes.",32,MUTED)
    limits=save(im,"outro_limits.png")
    im,d=base("Know before you pay")
    center(d,"Preflight",270,150)
    center(d,"Know before you pay.",455,68)
    center(d,"Live: preflight-jcgro45veq-as.a.run.app · Code: github.com/testofschool/preflight",650,39,1770)
    closing=save(im,"outro_closing.png")
    ffconcat(ASSETS/"intro.ffconcat",intro)
    ffconcat(ASSETS/"outro.ffconcat",[(architecture,12),(limits,16),(closing,14)])
    cues=[]
    for section,((start,end,script),phrases) in enumerate(zip(SCRIPT,PHRASES)):
        assert " ".join(phrases)==script,script
        if section==0:
            intro_times=[(0,4),(4,7),(7,10),(13,16)]
            for phrase,(a,b) in zip(phrases,intro_times):
                cues.append({"start_frame":a*FPS,"end_frame":b*FPS,"start":a,"end":b,"text":phrase})
            cues.append({"start_frame":10*FPS,"end_frame":13*FPS,"start":10,"end":13,"text":""})
            continue
        # Proportional word allocation, quantized to exact output frame boundaries.
        weights=[len(p.split()) for p in phrases]; total=sum(weights); before=0
        for phrase,weight in zip(phrases,weights):
            a=round((start+(end-start)*before/total)*FPS);before+=weight
            b=round((start+(end-start)*before/total)*FPS)
            cues.append({"start_frame":a,"end_frame":b,"start":a/FPS,"end":b/FPS,"text":phrase})
    cues.sort(key=lambda c:c["start_frame"])
    for idx,cue in enumerate(cues):
        im=Image.new("RGBA",(W,H),(0,0,0,0));d=ImageDraw.Draw(im);face=font(43)
        lines=wrap(d,cue["text"],face,1670)
        assert len(lines)<=2,(cue["text"],lines)
        line_height=58;top=H-56-len(lines)*line_height
        maximum=max((d.textlength(line,font=face) for line in lines),default=0)
        if lines:
            d.rounded_rectangle(((W-maximum)/2-30,top-16,(W+maximum)/2+30,H-42),14,fill=(20,43,49,242))
        for n,line in enumerate(lines):
            length=d.textlength(line,font=face)
            d.text(((W-length)/2,top+n*line_height),line,font=face,fill=WHITE)
        cue["lines"]=lines;cue["font_px"]=43
        cue["asset"]=str(save(im,f"caption_{idx:02d}.png"))
    ffconcat(ASSETS/"captions.ffconcat",[(Path(c["asset"]),(c["end_frame"]-c["start_frame"])/FPS)for c in cues])
    (ASSETS/"captions.json").write_text(json.dumps(cues,indent=2)+"\n")
    (ASSETS/"caption_script.txt").write_text("\n".join(s[2] for s in SCRIPT)+"\n")
    (REPORT/"track_c_captions.json").write_text(json.dumps(cues,indent=2)+"\n")
    (REPORT/"track_c_caption_script.txt").write_text("\n".join(s[2] for s in SCRIPT)+"\n")
    static_video(ASSETS/"intro.ffconcat",ASSETS/"intro.mp4",22)
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_format","-of","json",str(RAW)]))
    duration=float(probe["format"]["duration"])
    run(["ffmpeg","-hide_banner","-loglevel","warning","-y","-i",RAW,"-an","-vf",f"setpts=(PTS-STARTPTS)*108/{duration},fps=30,format=yuv420p","-t","108","-c:v","libx264","-preset","fast","-crf","18","-threads","6",ASSETS/"raw_108s.mp4"])
    static_video(ASSETS/"outro.ffconcat",ASSETS/"outro.mp4",42)
    (ASSETS/"base.ffconcat").write_text("ffconcat version 1.0\n"+"".join("file '"+str(ASSETS/f)+"'\n" for f in ["intro.mp4","raw_108s.mp4","outro.mp4"]))
    run(["ffmpeg","-hide_banner","-loglevel","warning","-y","-reinit_filter","0","-f","concat","-safe","0","-i",ASSETS/"base.ffconcat","-f","concat","-safe","0","-i",ASSETS/"captions.ffconcat","-filter_complex","[1:v]fps=30,format=rgba[cap];[0:v][cap]overlay=0:0:format=auto,format=yuv420p[v]","-map","[v]","-an","-t",TOTAL,"-c:v","libx264","-preset","fast","-crf","18","-threads","6","-movflags","+faststart",FINAL])
    finalize(cues,duration)

def finalize(cues,duration):
    raw_after=sha(RAW); assert raw_after==EXPECTED_RAW_SHA
    metadata=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(FINAL)]))
    v=next(s for s in metadata["streams"] if s["codec_type"]=="video")
    assert (v["width"],v["height"],v["avg_frame_rate"])==(1920,1080,"30/1")
    assert float(metadata["format"]["duration"])==172
    assert not any(s["codec_type"]=="audio" for s in metadata["streams"])
    assert " ".join(c["text"] for c in cues if c["text"])==" ".join(section[2] for section in SCRIPT)
    (REPORT/"track_c_ffprobe.json").write_text(json.dumps(metadata,indent=2)+"\n")
    frames=[]
    for time in [5,30,70,100,135,165]:
        name=f"{time//60:02d}m{time%60:02d}s.png";path=CHECK/name
        run(["ffmpeg","-hide_banner","-loglevel","error","-y","-ss",time,"-i",FINAL,"-frames:v","1",path])
        frames.append({"time_seconds":time,"path":str(path.relative_to(ROOT)),"sha256":sha(path),"byte_size":path.stat().st_size})
    summary={"duration_seconds":172,"resolution":"1920x1080","fps":"30/1","video_codec":v["codec_name"],"audio_stream":False,"loudness_lufs":None,"loudness_note":"N/A: no audio stream; no voiceover input was supplied.","sha256":sha(FINAL),"byte_size":FINAL.stat().st_size,"raw_sha256_before":EXPECTED_RAW_SHA,"raw_sha256_after":raw_after,"source_duration_seconds":duration,"source_speed_multiplier":duration/108,"source_extent":"Entire source interval 0–108.366667 mapped to final 22–130 s; no cuts.","caption_cue_count":len(cues),"caption_font_px":43,"caption_max_lines":max(len(c["lines"])for c in cues),"exact_caption_reconstruction":True,"frames":frames,"outro_holds_seconds":{"architecture":12,"limits":16,"closing":14},"intro_quote_holds_seconds":3,"intro_opening_hold_seconds":4,"intro_caption_gap_seconds":[10,13],"deviations":["Brief lists 10+12+8 seconds of outro content in a 42-second window. Holds extended to 12+16+14 to preserve 2:10–2:52 boundaries.","A 4-second opening card uses the exact C.2 opening sentences; four quote cards then hold3 seconds each through0:16. The unspoken third quote has no overlapping caption at0:10–0:13, preserving attribution.","No voiceover supplied: silent captioned export, no AAC/audio stream, per the explicit fallback."]}
    (REPORT/"track_c_video_facts.json").write_text(json.dumps(summary,indent=2)+"\n")
    sheet=Image.new("RGB",(1920,1242),PAPER);d=ImageDraw.Draw(sheet)
    for i,fr in enumerate(frames):
        thumb=Image.open(ROOT/fr["path"]).convert("RGB");thumb.thumbnail((960,540))
        x=(i%2)*960;y=(i//2)*414
        thumb=thumb.resize((704,396));sheet.paste(thumb,(x+128,y+18))
        seconds=fr["time_seconds"]
        d.text((x+16,y+20),f"{seconds//60}:{seconds%60:02d}",font=font(30),fill=INK)
    sheet.save(CHECK/"contact_sheet.png")
    print(json.dumps(summary,indent=2))

if __name__=="__main__":main()
