import os, json, time, shutil, subprocess, threading, uuid
from pathlib import Path
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel

ROOT=Path(__file__).resolve().parent
WORK=ROOT/'output'; WORK.mkdir(exist_ok=True)
app=FastAPI(title='AI Film Studio EP2')
JOBS={}
MODELS={'grok-imagine-video-1.5-lite':{'480p':.02,'720p':.03,'1080p':.14},'grok-imagine-video-1.5':{'480p':.08,'720p':.14,'1080p':.25}}
class Start(BaseModel):
    project:dict
    model:str='grok-imagine-video-1.5-lite'
    resolution:str='480p'
    approval:str=''
    max_budget_usd:float=0
    upload_drive:bool=False

def normalize(data):
    scenes=data.get('scenes')
    if not isinstance(scenes,list) or len(scenes)!=20: raise HTTPException(400,'JSON must contain exactly 20 scenes')
    out=[]
    for i,s in enumerate(scenes,1):
        if not isinstance(s,dict):raise HTTPException(400,f'Invalid scene {i}')
        prompt=s.get('grok_imagine_full_prompt') or s.get('prompt')
        if not isinstance(prompt,str) or not prompt.strip():raise HTTPException(400,f'Missing prompt scene {i}')
        out.append({'scene':i,'prompt':prompt})
    return out

def cost(model,res,scenes):
    if model not in MODELS or res not in MODELS[model]:raise HTTPException(400,'Unsupported model or resolution')
    return round(15*len(scenes)*MODELS[model][res],2)

@app.get('/health')
def health():return {'status':'ok','mode':'dry_run'}

@app.get('/',response_class=HTMLResponse)
def index():return (ROOT/'templates'/'index.html').read_text(encoding='utf-8')
@app.get('/example')
def example():return json.loads((ROOT/'data'/'ep2.json').read_text(encoding='utf-8'))
@app.post('/preflight')
def preflight(data:Start):
    scenes=normalize(data.project)
    return {'mode':'DRY_RUN','scenes':len(scenes),'duration_seconds':len(scenes)*15,'estimated_usd':cost(data.model,data.resolution,scenes),'model':data.model,'resolution':data.resolution,'api_configured':bool(os.getenv('XAI_API_KEY')),'ffmpeg_available':bool(shutil.which('ffmpeg')),'drive_configured':bool(os.getenv('GOOGLE_DRIVE_ACCESS_TOKEN')),'billing':'NO API REQUEST MADE'}

def run_job(jid,config,scenes):
    job=JOBS[jid]; folder=WORK/jid;folder.mkdir(exist_ok=True)
    key=os.environ['XAI_API_KEY'];headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'}
    try:
        files=[]
        for idx,s in enumerate(scenes,1):
            if job.get('cancel_requested'):raise RuntimeError('Stopped by user before next request')
            job.update(stage=f'Generating scene {idx}/20',completed=idx-1)
            payload={'model':config.model,'prompt':s['prompt'],'duration':15,'aspect_ratio':'9:16','resolution':config.resolution,'generate_audio':True}
            r=requests.post('https://api.x.ai/v1/videos/generations',json=payload,headers=headers,timeout=45);r.raise_for_status()
            request_id=r.json()['request_id'];job['requests'].append(request_id)
            for attempt in range(120):
                if job.get('cancel_requested'):raise RuntimeError('Stopped; previously submitted request may still incur charges')
                time.sleep(5)
                status=requests.get(f'https://api.x.ai/v1/videos/{request_id}',headers=headers,timeout=30);status.raise_for_status();result=status.json()
                if result.get('status')=='failed':raise RuntimeError(f'Scene {idx} failed: {result}')
                if result.get('status')=='done':break
            else:raise RuntimeError(f'Scene {idx} timed out')
            url=result['video']['url']
            p=folder/f'scene_{idx:02}.mp4'
            with requests.get(url,stream=True,timeout=120) as v:
                v.raise_for_status()
                with p.open('wb') as out:
                    for chunk in v.iter_content(1024*1024):out.write(chunk)
            files.append(p)
        if not shutil.which('ffmpeg'):raise RuntimeError('ffmpeg is required to merge')
        job['stage']='Merging clips'
        # Normalize to a consistent 9:16 video and audio format, avoiding concat codec mismatch.
        normalized=[]
        for idx,p in enumerate(files,1):
            dst=folder/f'norm_{idx:02}.mp4'
            subprocess.run(['ffmpeg','-y','-v','error','-i',str(p),'-vf','scale=480:854:force_original_aspect_ratio=decrease,pad=480:854:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24','-af','aresample=async=1:first_pts=0','-c:v','libx264','-preset','veryfast','-crf','23','-c:a','aac','-ar','48000','-ac','2',str(dst)],check=True,timeout=180)
            normalized.append(dst)
        manifest=folder/'concat.txt';manifest.write_text(''.join(f"file '{p.name}'\n" for p in normalized))
        final=folder/'The_Forgotten_Floor_EP2_Complete.mp4'
        subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(manifest),'-c','copy','-movflags','+faststart',str(final)],check=True,timeout=180)
        job.update(stage='Completed',status='completed',output=str(final),completed=20)
        if config.upload_drive:
            token=os.getenv('GOOGLE_DRIVE_ACCESS_TOKEN')
            if not token:job['drive_note']='No Drive OAuth token configured; MP4 remains available locally'
            else:
                # Google Drive v3 multipart upload with OAuth access token supplied locally.
                meta=json.dumps({'name':final.name,'mimeType':'video/mp4'})
                boundary='filmstudio'+uuid.uuid4().hex
                body=(f'--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n--{boundary}\r\nContent-Type: video/mp4\r\n\r\n').encode()+final.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
                rr=requests.post('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,webViewLink',headers={'Authorization':f'Bearer {token}','Content-Type':f'multipart/related; boundary={boundary}'},data=body,timeout=240)
                if rr.ok:job['drive_file']=rr.json()
                else:job['drive_note']=f'Upload failed HTTP {rr.status_code}; MP4 saved locally'
    except Exception as e:job.update(stage=str(e)[:400],status='failed')

@app.post('/start')
def start(config:Start, x_studio_admin_token:str|None=Header(default=None)):
    if os.getenv('ENABLE_PAID_GENERATION','false').lower()!='true':
        raise HTTPException(403,'Paid generation is disabled on this deployment (dry-run only)')
    scenes=normalize(config.project); estimate=cost(config.model,config.resolution,scenes)
    if x_studio_admin_token!=os.getenv('STUDIO_ADMIN_TOKEN') or not os.getenv('STUDIO_ADMIN_TOKEN'):raise HTTPException(403,'Admin token required')
    if config.approval!='I APPROVE PAID GENERATION':raise HTTPException(400,'Explicit approval phrase required')
    if config.max_budget_usd<estimate:raise HTTPException(400,f'Budget limit below estimate ${estimate}')
    if not os.getenv('XAI_API_KEY'):raise HTTPException(400,'XAI_API_KEY not configured')
    if not shutil.which('ffmpeg'):raise HTTPException(400,'ffmpeg not installed')
    jid=uuid.uuid4().hex[:12];JOBS[jid]={'status':'running','stage':'Starting','completed':0,'requests':[]}
    threading.Thread(target=run_job,args=(jid,config,scenes),daemon=True).start()
    return {'job_id':jid,'estimated_usd':estimate,'warning':'Paid generation submitted; retries and failures can incur costs'}

@app.get('/status/{jid}')
def status(jid:str):
    if jid not in JOBS:raise HTTPException(404)
    return {k:v for k,v in JOBS[jid].items() if k!='output'} | {'download_ready':bool(JOBS[jid].get('output'))}

@app.post('/cancel/{jid}')
def cancel(jid:str,x_studio_admin_token:str|None=Header(default=None)):
    if x_studio_admin_token!=os.getenv('STUDIO_ADMIN_TOKEN') or not os.getenv('STUDIO_ADMIN_TOKEN'):raise HTTPException(403)
    if jid not in JOBS:raise HTTPException(404)
    JOBS[jid]['cancel_requested']=True
    return {'cancel_requested':True,'note':'Already submitted requests may still incur charges'}

@app.get('/download/{jid}')
def download(jid:str,x_studio_admin_token:str|None=Header(default=None)):
    if x_studio_admin_token!=os.getenv('STUDIO_ADMIN_TOKEN') or not os.getenv('STUDIO_ADMIN_TOKEN'):raise HTTPException(403)
    p=JOBS.get(jid,{}).get('output')
    if not p or not Path(p).exists():raise HTTPException(404)
    return FileResponse(p,media_type='video/mp4',filename=Path(p).name)
