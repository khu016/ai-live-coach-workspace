// Recording-only input fixture. All ASR, bullets and reports use the normal backend.
const ctx = new AudioContext();
const dest = ctx.createMediaStreamDestination();
let source;
const canvas = document.createElement('canvas'); canvas.width=1280;canvas.height=720;
const g=canvas.getContext('2d');
function paint(){
 g.fillStyle='#111e27';g.fillRect(0,0,1280,720);
 g.fillStyle='#65d5d1';g.textAlign='center';g.font='600 56px sans-serif';g.fillText('NIVI',640,215);
 g.fillStyle='#e4edf0';g.font='32px sans-serif';g.fillText('新人如何准备第一场直播',640,295);
 const t=performance.now()/350;
 for(let i=0;i<45;i++){const h=source?22+Math.abs(Math.sin(t+i*.7))*70:8;g.fillStyle='#39b9bd';g.fillRect(324+i*14,395-h/2,6,h);}
 g.fillStyle='#93aab5';g.font='24px sans-serif';g.fillText('合成语音演示 · 非真人出镜',640,515);
 requestAnimationFrame(paint);
}paint();
const video=canvas.captureStream(20);
Object.defineProperty(navigator.mediaDevices,'getUserMedia',{configurable:true,value:async constraints=>{
 await ctx.resume();
 return new MediaStream([...(constraints.audio?dest.stream.getAudioTracks().map(t=>t.clone()):[]),...(constraints.video?video.getVideoTracks().map(t=>t.clone()):[])]);
}});
const panel=document.createElement('div');
panel.style.cssText='position:fixed;bottom:12px;left:12px;z-index:99999;display:flex;gap:9px;align-items:center;padding:8px 12px;border:1px solid #cce5e5;border-radius:9px;background:#f2fbfbea;font:12px sans-serif;color:#24686c';
const label=document.createElement('span');label.textContent='合成语音演示';panel.append(label);
const select=document.createElement('select');for(const s of ['opening','response','retrain']){let o=document.createElement('option');o.value=s;o.textContent=({opening:'开场',response:'回应弹幕',retrain:'重练'})[s];select.append(o);}panel.append(select);
const play=document.createElement('button');play.textContent='播放演示语音';play.onclick=async()=>{try{await ctx.resume();if(source)source.stop();const res=await fetch('/video-demo/'+select.value+'.wav');if(!res.ok)throw new Error('音频未就绪');const b=await ctx.decodeAudioData(await res.arrayBuffer());source=ctx.createBufferSource();source.buffer=b;source.connect(dest);source.connect(ctx.destination);source.start();play.textContent='语音播放中';source.onended=()=>{source=null;play.textContent='播放演示语音';};}catch(e){play.textContent=String(e);}};panel.append(play);document.body.append(panel);
await import('/src/main.tsx');
