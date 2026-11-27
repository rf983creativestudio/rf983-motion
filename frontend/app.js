(() => {
"use strict";
const $ = (selector, root=document) => root.querySelector(selector);
const $$ = (selector, root=document) => Array.from(root.querySelectorAll(selector));
const STORAGE_KEY = "rf983-motion-projects-v2";
const DRAFT_KEY = "rf983-motion-active-v2";
const API_BASE_KEY = "rf983-motion-api-base-v1";
const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const state = { shots: [], reference: null, activeView: "studio", projects: [], previewUrl: null };
const defaultShots = () => [
  {id:makeId(),name:"Establishing shot",framing:"Extreme wide",camera:"Slow push-in",action:"Reveal the environment and establish the subject's place in it.",duration:5},
  {id:makeId(),name:"The approach",framing:"Medium wide",camera:"Tracking",action:"Follow the subject moving through the environment with clear screen direction.",duration:5},
  {id:makeId(),name:"Final detail",framing:"Close-up",camera:"Gentle orbit",action:"End on a meaningful visual detail or emotional beat.",duration:5}
];
function makeId(){return "s"+Math.random().toString(36).slice(2,10)}
function setApiBadge(state,label){const badge=$("#api-connection-pill");if(!badge)return;badge.textContent=label;badge.classList.remove("connected","disconnected","unconfigured");badge.classList.add(state);}
function escapeHtml(value){return String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function getShots(){return state.shots}
function totalDuration(){return state.shots.reduce((sum,shot)=>sum+Number(shot.duration||0),0)}
function toast(message){const el=$("#toast");el.textContent=message;el.classList.add("show");clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.classList.remove("show"),2300)}
function setView(name){state.activeView=name;$$(".view").forEach(v=>v.classList.toggle("active",v.id==="view-"+name));$$(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.view===name));$("#crumb-current").textContent=({studio:"Studio",storyboard:"Storyboard",library:"My projects",models:"Model lab"})[name]||"Studio";if(name==="storyboard")renderShotEditor();if(name==="library")renderLibrary();window.scrollTo({top:0,behavior:"smooth"})}
function readForm(){return {name:$("#project-name").value.trim()||"Untitled cinematic project",prompt:$("#prompt").value,negativePrompt:$("#negative-prompt").value,subject:$("#subject").value,environment:$("#environment").value,lighting:$("#lighting").value,mood:$("#mood").value,model:$("#model").value,aspect:$("#aspect").value,resolution:$("#resolution").value,duration:$("#duration").value,fps:$("#fps").value,quality:$("#quality").value,seed:$("#seed").value,audio:$("#audio").checked,refine:$("#refine").checked,shots:state.shots.map(s=>({...s})),reference:state.reference?{name:state.reference.name,type:state.reference.type,size:state.reference.size}:null,updatedAt:new Date().toISOString()}}
function applyForm(data){if(!data)return;const fields=["project-name","prompt","negative-prompt","subject","environment","lighting","mood","model","aspect","resolution","duration","fps","quality","seed"];const keys=["name","prompt","negativePrompt","subject","environment","lighting","mood","model","aspect","resolution","duration","fps","quality","seed"];fields.forEach((id,i)=>{if(data[keys[i]]!==undefined)$("#"+id).value=data[keys[i]]});if(data.audio!==undefined)$("#audio").checked=!!data.audio;if(data.refine!==undefined)$("#refine").checked=!!data.refine;if(Array.isArray(data.shots)&&data.shots.length)state.shots=data.shots.map(s=>({...s}));renderAll()}
function saveDraft(silent=false){const data=readForm();try{localStorage.setItem(DRAFT_KEY,JSON.stringify(data));$("#save-state").textContent="SAVED LOCALLY · "+new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"});if(!silent)toast("Draft saved in this browser.");return true}catch(e){if(!silent)toast("Could not save locally. Browser storage may be full.");return false}}
function getProjects(){try{return JSON.parse(localStorage.getItem(STORAGE_KEY)||"[]")}catch(e){return []}}
function saveProjectToLibrary(){const data=readForm();const projects=getProjects();const existing=projects.findIndex(p=>p.name===data.name);data.id=existing>=0?projects[existing].id:makeId();if(existing>=0)projects[existing]=data;else projects.unshift(data);try{localStorage.setItem(STORAGE_KEY,JSON.stringify(projects.slice(0,30)));saveDraft(true);renderLibrary();toast("Project saved to your local library.");return true}catch(e){toast("Storage limit reached. Remove large browser data or export your project.");return false}}
function exportProject(){const data=readForm();const blob=new Blob([JSON.stringify({format:"rf983-motion-project",version:2,project:data},null,2)],{type:"application/json"});downloadBlob(blob,(data.name||"rf983-project").replace(/[^a-z0-9-_]+/gi,"-").toLowerCase()+".json");toast("Project JSON exported.")}
function downloadBlob(blob,name){const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function renderShots(){
 const strip=$("#shot-strip");
 strip.innerHTML=state.shots.map((shot,index)=>'<article class="shot-card"><div class="shot-card-top"><span>SHOT '+String(index+1).padStart(2,"0")+'</span><span>'+escapeHtml(shot.framing)+'</span></div><b>'+escapeHtml(shot.name)+'</b><small>'+escapeHtml(shot.camera)+'</small><div class="shot-time">'+Number(shot.duration)+' SEC</div></article>').join("");
 $("#shot-count").textContent=state.shots.length;
 $("#storyboard-total").textContent=state.shots.length+" shots · "+totalDuration()+" seconds planned";
 $("#sequence-duration").textContent=totalDuration()+"s";
 $("#timeline-label").textContent=totalDuration()+" seconds planned";
 $("#timeline-track").innerHTML=state.shots.map((shot,index)=>'<div class="timeline-segment" style="flex:'+Math.max(1,Number(shot.duration)||5)+'" title="'+escapeHtml(shot.name)+' · '+Number(shot.duration)+'s"><b>'+String(index+1).padStart(2,"0")+'</b><small>'+escapeHtml(shot.name)+'</small></div>').join("");
}
function renderShotEditor(){
 const host=$("#shot-editor-list");
 host.innerHTML=state.shots.map((s,i)=>'<article class="shot-editor panel" data-shot-id="'+escapeHtml(s.id)+'"><div class="shot-visual">SHOT '+String(i+1).padStart(2,"0")+' / RF983</div><div><div class="shot-fields"><div><label>SHOT TITLE</label><input data-field="name" value="'+escapeHtml(s.name)+'" maxlength="60"></div><div><label>FRAMING</label><select data-field="framing">'+options(["Extreme wide","Wide","Medium wide","Medium","Medium close-up","Close-up","Extreme close-up","Overhead","Low angle"],s.framing)+'</select></div><div><label>CAMERA MOVEMENT</label><select data-field="camera">'+options(["Locked-off","Slow push-in","Pull-back","Tracking","Pan left","Pan right","Tilt up","Tilt down","Crane","Gentle orbit","Handheld"],s.camera)+'</select></div><div class="shot-field-wide"><label>VISIBLE ACTION / BEAT</label><textarea data-field="action" maxlength="500">'+escapeHtml(s.action)+'</textarea></div><div><label>PLANNED DURATION</label><select data-field="duration">'+options(["3","4","5","6","8","10","12","15"],String(s.duration),v=>v+" seconds")+'</select></div></div><div class="shot-actions"><small>Sequence position '+(i+1)+' of '+state.shots.length+'</small><div><button data-move-up="'+escapeHtml(s.id)+'" '+(i===0?"disabled":"")+'>↑</button><button data-move-down="'+escapeHtml(s.id)+'" '+(i===state.shots.length-1?"disabled":"")+'>↓</button><button data-duplicate-shot="'+escapeHtml(s.id)+'">Duplicate</button><button data-remove-shot="'+escapeHtml(s.id)+'" '+(state.shots.length===1?"disabled":"")+'>Remove ×</button></div></div></div></article>').join("");
}
function options(values,selected,labeler){return values.map(v=>'<option value="'+escapeHtml(v)+'" '+(String(v)===String(selected)?"selected":"")+'>'+escapeHtml(labeler?labeler(v):v)+'</option>').join("")}
function renderLibrary(){const projects=getProjects();$("#library-count").textContent=projects.length+" projects";const host=$("#library-grid");if(!projects.length){host.innerHTML='<div class="empty-library"><div style="font-size:28px">▧</div><b>Your creative library is waiting.</b><small>Save a project draft to keep it in this browser, or export a portable JSON project file.</small></div>';return}host.innerHTML=projects.map(p=>'<article class="library-card"><div class="library-art">RF983 / '+escapeHtml(p.aspect||"16:9")+'</div><h3>'+escapeHtml(p.name)+'</h3><p>'+escapeHtml((p.prompt||"No creative brief yet").slice(0,110))+'</p><div class="library-card-footer"><small>'+new Date(p.updatedAt||Date.now()).toLocaleDateString()+' · '+(p.shots||[]).length+' shots</small><button data-load-project="'+escapeHtml(p.id)+'">Open draft ↗</button></div></article>').join("")}
function updateReadiness(){const prompt=$("#prompt").value.trim();const essentials=[!!prompt,state.shots.length>0,true];const ready=essentials.filter(Boolean).length;$("#check-prompt").textContent=essentials[0]?"●":"○";$("#check-prompt-label").textContent=essentials[0]?"Ready":"Missing";$("#check-shots").textContent=essentials[1]?"●":"○";$("#check-shots-label").textContent=state.shots.length+" shots";$("#check-reference").textContent=state.reference?"●":"○";$("#check-reference-label").textContent=state.reference?"Added":"Optional";$("#readiness-fill").style.width=(ready/3*100)+"%";$("#readiness-text").textContent=ready+" of 3 essentials ready"}
function renderAll(){renderShots();updateReadiness();$("#prompt-count").textContent=$("#prompt").value.length+" / 4000";analyzePrompt();renderProductionDesk();if(state.activeView==="storyboard")renderShotEditor()}
function buildPrompt(){const parts=[];const subject=$("#subject").value.trim(),environment=$("#environment").value.trim(),lighting=$("#lighting").value,mood=$("#mood").value;if(subject)parts.push(subject);if(environment)parts.push("Set in "+environment+".");if(lighting)parts.push(lighting+".");if(mood)parts.push("Mood: "+mood.toLowerCase()+".");const current=$("#prompt").value.trim();const addition=parts.join(" ");if(!addition){toast("Add at least one director's note first.");return}$("#prompt").value=[current,addition].filter(Boolean).join(current?" ":"");$("#prompt").dispatchEvent(new Event("input"));toast("Director's notes added to the master prompt.")}
function handleReference(file){if(!file)return;if(!["image/jpeg","image/png","image/webp"].includes(file.type)){toast("Choose a JPG, PNG or WEBP image.");return}if(file.size>MAX_IMAGE_BYTES){toast("Image is larger than 10 MB. Choose a smaller reference.");return}if(state.previewUrl)URL.revokeObjectURL(state.previewUrl);state.previewUrl=URL.createObjectURL(file);state.reference={name:file.name,type:file.type,size:file.size,url:state.previewUrl};$("#reference-thumb").src=state.previewUrl;$("#reference-name").textContent=file.name;$("#reference-size").textContent=(file.size/1024/1024).toFixed(2)+" MB · local preview only";$("#reference-preview").classList.remove("hidden");$("#drop-zone").classList.add("hidden");updateReadiness()}
function clearReference(){if(state.previewUrl)URL.revokeObjectURL(state.previewUrl);state.previewUrl=null;state.reference=null;$("#reference-image").value="";$("#reference-preview").classList.add("hidden");$("#drop-zone").classList.remove("hidden");updateReadiness()}
function addShot(){if(state.shots.length>=12){toast("This planner supports up to 12 shots per project.");return}state.shots.push({id:makeId(),name:"New shot",framing:"Wide",camera:"Locked-off",action:"Describe the visible action and the beat this shot should communicate.",duration:5});renderAll();renderShotEditor();scheduleDraftSave();toast("Shot added to storyboard.")}

function renderWorkerHistory(items){
 const host=$("#worker-history-list");if(!host)return;
 if(!items.length){host.innerHTML='<div class="history-empty">No worker reports saved yet. Start the local preflight agent and refresh.</div>';return}
 host.innerHTML=items.map(item=>{
  const d=item.diagnostics||{},tools=d.tools||{},gpu=d.gpu_detected?"GPU detected":"No NVIDIA GPU reported";
  const when=new Date(Number(item.observed_at)*1000),stamp=Number.isNaN(when.getTime())?"Unknown time":when.toLocaleString();
  return '<article class="history-item"><div class="history-time"><b>'+escapeHtml(stamp)+'</b><small>'+escapeHtml(item.worker_id||"local worker")+'</small></div><div class="history-facts"><span>'+escapeHtml(gpu)+'</span><span>FFmpeg '+(tools.ffmpeg?"available":"missing")+'</span><span>Python '+escapeHtml(d.python||"unknown")+'</span><span>Disk '+escapeHtml(String(d.disk_free_gb??"—"))+' GB free</span></div></article>';
 }).join("");
}
async function refreshDiagnostics(){
 const button=$("#refresh-diagnostics"),host=$("#diagnostic-results"),note=$("#diagnostic-note");
 let base=$("#api-base").value.trim();
 if(!base){setApiBadge("unconfigured","API NOT SET");note.textContent="Paste the backend service URL from Render (for example, https://your-service.onrender.com), then connect again.";return}
 let parsed;
 try{parsed=new URL(base)}catch(error){setApiBadge("disconnected","API INVALID");note.textContent="Enter a complete backend URL, including https://.";return}
 if(!["http:","https:"].includes(parsed.protocol)||parsed.username||parsed.password||parsed.search||parsed.hash||parsed.pathname!=="/"){setApiBadge("disconnected","API INVALID");note.textContent="Use only the backend HTTPS origin, without credentials, a path, query or fragment.";return}
 if(location.protocol==="https:"&&parsed.protocol!=="https:"){setApiBadge("disconnected","API HTTPS REQUIRED");note.textContent="The live studio requires an HTTPS backend address; browsers block insecure HTTP API calls from this HTTPS site.";return}
 base=parsed.origin;
 const opsToken=$("#operations-token").value.trim();
 const privateHeaders=opsToken?{"X-Operations-Token":opsToken}:{};
 button.disabled=true;button.textContent="Checking…";note.textContent="Checking public service health and protected operations…";
 const row=(name,detail,status,kind)=>'<div><span class="arch-dot '+kind+'"></span><b>'+escapeHtml(name)+'</b><small>'+escapeHtml(detail)+'</small><em>'+escapeHtml(status)+'</em></div>';
 try{
  const publicPaths=["/api/health","/api/models","/api/system/ready"];
  const publicResponses=await Promise.all(publicPaths.map(path=>fetch(base+path,{headers:{Accept:"application/json"},cache:"no-store"})));
  if(publicResponses.some(r=>!r.ok))throw new Error("The public API health check returned an error.");
  const [health,models,ready]=await Promise.all(publicResponses.map(r=>r.json()));
  try{localStorage.setItem(API_BASE_KEY,base)}catch(error){}
  setApiBadge("connected","API CONNECTED");
  let worker=null,history=null,opsError="";
  if(opsToken){
   const privatePaths=["/api/worker/status","/api/worker/history?limit=12","/api/operations/summary"];
   const privateResponses=await Promise.all(privatePaths.map(path=>fetch(base+path,{headers:{Accept:"application/json",...privateHeaders},cache:"no-store"})));
   if(privateResponses.every(r=>r.ok)){
    const privateData=await Promise.all(privateResponses.map(r=>r.json()));
    worker=privateData[0];history=privateData[1];renderWorkerHistory(history.items||[]);
    const summary=privateData[2];
    opsError="Private operations unlocked · "+summary.worker_history_records+" retained reports · "+summary.persistent_state+" state store.";
   }else{
    const failed=privateResponses.find(r=>!r.ok);
    opsError=failed&&failed.status===401?"Operations token rejected. Check the server's RF983_OPERATIONS_TOKEN.":"Private operations are unavailable ("+(failed?failed.status:"unknown")+").";
    $("#worker-history-list").innerHTML='<div class="history-empty">Private worker history is locked. Check the operations token and refresh.</div>';
   }
  }else{
   $("#worker-history-list").innerHTML='<div class="history-empty">Private worker history is locked. Enter the operations token above to view stored reports.</div>';
   opsError="Enter the private operations token to view machine diagnostics and worker history. The token is held only in this page's memory and is not saved.";
  }
  const verified=models.verified_model_count||0,diag=worker&&worker.diagnostics||{};
  const machineDetail=worker?(worker.connected?(diag.platform||"Local agent connected")+" · GPU: "+(diag.gpu_detected?(diag.gpu_detail||"Detected"):"not detected")+" · FFmpeg: "+(diag.tools&&diag.tools.ffmpeg?"yes":"no")+" · PyTorch: "+(diag.python_packages&&diag.python_packages.torch?"yes":"no"):"No fresh heartbeat"):"Private machine details are locked.";
  host.innerHTML=[
   row("API connection",health.service+" · version "+health.version,"CONNECTED","ready"),
   row("GPU worker",worker?(worker.connected?(worker.worker_id||"Worker online"):"No fresh heartbeat"):"Protected · token required",worker?(worker.connected?"CONNECTED":"OFFLINE"):"LOCKED",worker?(worker.connected?"pending":"offline"):"pending"),
   row("Machine preflight",machineDetail,worker?(diag.gpu_detected?"GPU DETECTED":worker.connected?"AGENT ONLINE":"WAITING"):"LOCKED",worker?(diag.gpu_detected?"pending":worker.connected?"ready":"offline"):"pending"),
   row("Verified models",verified+" verified · "+models.models.length+" candidates",verified?"VERIFIED":"NONE",verified?"ready":"offline"),
   row("Generation pipeline",ready.generation_reason||"Not enabled",ready.generation_enabled?"ENABLED":"DISABLED",ready.generation_enabled?"ready":"offline")
  ].join("");
  note.textContent=opsError+" A connected heartbeat or detected GPU does not prove a video can be rendered.";
 }catch(error){
  host.innerHTML=row("API connection","Could not reach "+base,"UNAVAILABLE","offline")+row("GPU worker","Cannot verify without API","UNKNOWN","offline")+row("Verified models","Cannot verify without API","UNKNOWN","offline")+row("Generation pipeline","Must remain disabled","DISABLED","offline");
  setApiBadge("disconnected","API OFFLINE");
  note.textContent="Could not reach the backend. Check that the Render service is deployed, the URL is correct, and RF983_ALLOWED_ORIGINS includes https://rf983creativestudio.github.io. "+error.message;
 }finally{button.disabled=false;button.textContent="Connect & verify API ↻"}
}
let autosaveHandle=null;
function scheduleDraftSave(){
 clearTimeout(autosaveHandle);
 const stateLabel=$("#save-state");
 if(stateLabel)stateLabel.textContent="UNSAVED CHANGES";
 autosaveHandle=setTimeout(()=>saveDraft(true),650);
}
function analyzePrompt(){
 const value=$("#prompt").value.trim();
 const words=value?value.split(/\s+/).filter(Boolean):[];
 const checks=[
  ["subject",/\b(person|woman|man|child|character|car|ship|building|animal|robot|astronaut|landscape|city|product|object)\b/i.test(value)],
  ["action",/\b(walk|run|move|turn|look|rise|fall|fly|drive|flow|dance|open|close|approach|reveal|cross|drift|transform|build)\w*\b/i.test(value)],
  ["setting",/\b(in|inside|outside|across|beneath|above|within|through|at|on)\b/i.test(value)],
  ["camera",/\b(camera|close-up|wide shot|medium shot|tracking|pan|tilt|dolly|crane|orbit|push-in|pull-back|overhead|low angle)\b/i.test(value)],
  ["light",/\b(light|lighting|sun|sunlight|moonlight|shadow|neon|backlit|golden hour|blue hour|volumetric|soft glow)\b/i.test(value)]
 ];
 const score=checks.filter(item=>item[1]).length;
 $("#prompt-score").textContent=value?score+"/5 direction cues · "+words.length+" words":"Awaiting brief";
 $("#prompt-advice").textContent=!value?"Start with a visible subject and one clear action.":score>=4?"Strong direction. Keep the action physically clear and consistent through time.":"Consider adding: "+checks.filter(item=>!item[1]).map(item=>item[0]).join(", ")+". This is a writing heuristic, not an AI evaluation.";
}
function validateImportedProject(raw){
 if(!raw||typeof raw!=="object")throw new Error("Invalid project file.");
 if(raw.format&&raw.format!=="rf983-motion-project")throw new Error("This is not an RF983 MOTION project export.");
 const data=raw.project&&typeof raw.project==="object"?raw.project:raw;
 if(typeof data.prompt!=="string"||data.prompt.length>4000)throw new Error("Project prompt is missing or too long.");
 if(!Array.isArray(data.shots)||data.shots.length<1||data.shots.length>12)throw new Error("Project must contain between 1 and 12 shots.");
 const clean={...data,shots:data.shots.map((shot,index)=>{
  if(!shot||typeof shot!=="object")throw new Error("Invalid shot "+(index+1)+".");
  return {id:makeId(),name:String(shot.name||"Shot "+(index+1)).slice(0,60),framing:String(shot.framing||"Wide").slice(0,40),camera:String(shot.camera||"Locked-off").slice(0,40),action:String(shot.action||"").slice(0,500),duration:Math.max(3,Math.min(15,Number(shot.duration)||5))};
 })};
 const limits={name:70,negativePrompt:1200,subject:300,environment:300,lighting:100,mood:100,model:40,aspect:10,resolution:10,duration:4,fps:3,quality:20,seed:12};
 Object.keys(limits).forEach(key=>{if(clean[key]!==undefined)clean[key]=String(clean[key]).slice(0,limits[key])});
 clean.audio=!!clean.audio;clean.refine=clean.refine!==false;clean.reference=null;
 return clean;
}
function importProjectFile(file){
 if(!file)return;
 if(file.size>1024*1024){toast("Project file is too large. Maximum 1 MB.");return}
 const reader=new FileReader();
 reader.onload=()=>{
  try{
   const project=validateImportedProject(JSON.parse(String(reader.result||"")));
   applyForm(project);clearReference();saveDraft(true);setView("studio");
   toast("Project imported. Re-select its reference image if needed.");
  }catch(error){toast(error.message||"Could not import this project file.")}
 };
 reader.onerror=()=>toast("Could not read the selected project file.");
 reader.readAsText(file);
}
function moveShot(id,delta){
 const index=state.shots.findIndex(shot=>shot.id===id),target=index+delta;
 if(index<0||target<0||target>=state.shots.length)return;
 [state.shots[index],state.shots[target]]=[state.shots[target],state.shots[index]];
 renderAll();renderShotEditor();scheduleDraftSave();
}
function duplicateShot(id){
 if(state.shots.length>=12){toast("Maximum 12 shots per project.");return}
 const index=state.shots.findIndex(shot=>shot.id===id);if(index<0)return;
 const copy={...state.shots[index],id:makeId(),name:(state.shots[index].name+" copy").slice(0,60)};
 state.shots.splice(index+1,0,copy);renderAll();renderShotEditor();scheduleDraftSave();toast("Shot duplicated.");
}

function productionAudit(){
 const data=readForm(),words=data.prompt.trim()?data.prompt.trim().split(/\s+/).length:0;
 const checks=[];
 const add=(level,label,detail)=>checks.push({level,label,detail});
 add(data.name&&data.name!=="Untitled cinematic project"?"good":"warn","Project identity",data.name&&data.name!=="Untitled cinematic project"?"Project has a descriptive title.":"Give this project a distinctive name before handoff.");
 add(words>=30?"good":words>=10?"warn":"risk","Creative brief",words+" words. "+(words>=30?"Enough detail for a useful first handoff.":"Expand the prompt with subject, action, setting, camera and lighting."));
 const blankShots=data.shots.filter(x=>!String(x.action||"").trim()).length;
 add(blankShots===0?"good":"warn","Shot actions",blankShots===0?"Every shot has a visible action or beat.":blankShots+" shot(s) need a defined action.");
 const names=data.shots.map(x=>String(x.name||"").trim().toLowerCase());
 const duplicates=names.filter((x,i)=>x&&names.indexOf(x)!==i);
 add(duplicates.length?"warn":"good","Shot naming",duplicates.length?"Repeated shot titles found; rename them to make handoff clearer.":"Shot titles are distinct.");
 const repeated=data.shots.length>1&&data.shots.every(x=>x.camera===data.shots[0].camera);
 add(repeated?"warn":"good","Camera variety",repeated?"Every shot uses the same camera movement. Check whether that is intentional.":"Camera movement varies or the sequence is a single shot.");
 add(data.negativePrompt.trim()?"good":"note","Negative prompt",data.negativePrompt.trim()?"A negative prompt is included.":"Optional: add exclusions if the selected model supports them.");
 add(data.reference?"good":"note","Visual reference",data.reference?"Reference file selected: "+data.reference.name+". The file itself is not included in exports.":"No reference image selected. This is optional, but remember to share it separately.");
 add(data.shots.length<=12?"good":"risk","Sequence limits",data.shots.length+" shots in the storyboard.");
 return {data,checks,words,frames:Math.round(Number(data.duration||5)*Number(data.fps||24)*Math.max(1,data.shots.length)),runtime:totalDuration()};
}
function renderProductionDesk(){
 const audit=productionAudit();
 $("#prod-shots").textContent=audit.data.shots.length;
 $("#prod-runtime").textContent=audit.runtime+"s";
 $("#prod-frames").textContent=(audit.runtime*Number(audit.data.fps||24)).toLocaleString();
 $("#prod-score").textContent=audit.checks.filter(x=>x.level==="good").length+"/"+audit.checks.length;
 $("#production-checks").innerHTML=audit.checks.map(item=>'<div class="production-check '+item.level+'"><span>'+({good:"✓",warn:"!",risk:"×",note:"i"}[item.level])+'</span><div><b>'+escapeHtml(item.label)+'</b><small>'+escapeHtml(item.detail)+'</small></div></div>').join("");
}
function exportDirectorBrief(){
 const a=productionAudit(),d=a.data;
 const lines=["# "+d.name,"","## Production overview","- Planned shots: "+d.shots.length,"- Planned runtime: "+a.runtime+" seconds","- Frame rate target: "+d.fps+" fps","- Estimated frames: "+(a.runtime*Number(d.fps||24))+" (planning estimate only)","- Aspect ratio: "+d.aspect,"- Resolution target: "+d.resolution,"- Quality profile: "+d.quality,"- Model route: "+d.model,"- Audio requested: "+(d.audio?"Yes":"No"),"","## Creative brief",d.prompt||"_No prompt supplied._","","## Negative prompt",d.negativePrompt||"_None supplied._","","## Director's notes","- Subject: "+(d.subject||"Not specified"),"- Environment: "+(d.environment||"Not specified"),"- Lighting: "+(d.lighting||"Not specified"),"- Mood: "+(d.mood||"Not specified"),"","## Shot-by-shot plan"];
 d.shots.forEach((shot,i)=>lines.push("### "+String(i+1).padStart(2,"0")+". "+shot.name,"- Duration: "+shot.duration+" seconds","- Framing: "+shot.framing,"- Camera: "+shot.camera,"- Action: "+(shot.action||"Not specified")));
 lines.push("","## Pre-production checks",...a.checks.map(x=>"- ["+(x.level==="good"?"x":x.level==="risk"?"!":" ")+"] "+x.label+": "+x.detail),"","## Handoff notes","- This document is a creative handoff, not a render or model execution report.","- Re-attach any reference image separately; project exports do not embed image bytes.","- Actual output length, frame count and supported settings depend on the connected model and render pipeline.","","Generated by RF983 MOTION 0.6.0.");
 downloadBlob(new Blob([lines.join("\n")],{type:"text/markdown;charset=utf-8"}),fileSlug(d.name)+"-director-brief.md");
 toast("Director brief exported.");
}
function fileSlug(value){return String(value||"rf983-project").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,60)||"rf983-project"}
function exportShotCsv(){
 const d=readForm(),rows=[["Shot","Title","Duration (seconds)","Framing","Camera movement","Visible action"]];
 d.shots.forEach((x,i)=>rows.push([i+1,x.name,x.duration,x.framing,x.camera,x.action]));
 const csv=rows.map(row=>row.map(value=>'"'+String(value??"").replace(/"/g,'""')+'"').join(",")).join("\r\n");
 downloadBlob(new Blob(["\uFEFF",csv],{type:"text/csv;charset=utf-8"}),fileSlug(d.name)+"-shot-list.csv");
 toast("Shot list CSV exported.");
}
function exportProductionJson(){
 const a=productionAudit(),payload={format:"rf983-motion-production-pack",version:1,generatedAt:new Date().toISOString(),project:a.data,production:{plannedRuntimeSeconds:a.runtime,targetFps:Number(a.data.fps||24),estimatedFrames:a.runtime*Number(a.data.fps||24),checks:a.checks}};
 downloadBlob(new Blob([JSON.stringify(payload,null,2)],{type:"application/json"}),fileSlug(a.data.name)+"-production-pack.json");
 toast("Production JSON exported.");
}

function bindEvents(){
$$(".nav-item").forEach(b=>b.addEventListener("click",()=>setView(b.dataset.view)));
$$("[data-go]").forEach(b=>b.addEventListener("click",()=>setView(b.dataset.go)));
$("#refresh-diagnostics").addEventListener("click",refreshDiagnostics);
$("#refresh-history").addEventListener("click",refreshDiagnostics);
$("#run-production-check").addEventListener("click",()=>{renderProductionDesk();toast("Pre-production checks refreshed.")});
$("#export-director-brief").addEventListener("click",exportDirectorBrief);
$("#export-shot-csv").addEventListener("click",exportShotCsv);
$("#export-production-json").addEventListener("click",exportProductionJson);
$("#import-project").addEventListener("click",()=>$("#import-file").click());
$("#import-library").addEventListener("click",()=>$("#import-file").click());
$("#import-file").addEventListener("change",e=>{importProjectFile(e.target.files&&e.target.files[0]);e.target.value="";});
$("#prompt").addEventListener("input",()=>{$("#prompt-count").textContent=$("#prompt").value.length+" / 4000";updateReadiness();analyzePrompt();scheduleDraftSave()});
$("#prompt-guide").addEventListener("click",()=>$("#guide-dialog").showModal());
$("#build-prompt").addEventListener("click",buildPrompt);
$("#reference-image").addEventListener("change",e=>handleReference(e.target.files&&e.target.files[0]));
$("#remove-reference").addEventListener("click",clearReference);
const drop=$("#drop-zone");["dragenter","dragover"].forEach(evt=>drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.add("dragover")}));["dragleave","drop"].forEach(evt=>drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.remove("dragover")}));drop.addEventListener("drop",e=>handleReference(e.dataTransfer.files&&e.dataTransfer.files[0]));
$("#random-seed").addEventListener("click",()=>$("#seed").value=Math.floor(Math.random()*2147483647));
$("#save-project").addEventListener("click",saveProjectToLibrary);$("#export-project").addEventListener("click",exportProject);
$("#generate").addEventListener("click",()=>{$("#generation-status").textContent="Generation is unavailable: no authenticated GPU worker is connected. Your prompt and reference image have not been uploaded.";toast("Generation safely blocked — no inference engine connected.")});
$("#add-shot").addEventListener("click",addShot);
$("#reset-shots").addEventListener("click",()=>{state.shots=defaultShots();renderAll();renderShotEditor();scheduleDraftSave();toast("Storyboard reset to the starter sequence.")});
$("#shot-editor-list").addEventListener("input",e=>{const card=e.target.closest("[data-shot-id]");if(!card)return;const shot=state.shots.find(s=>s.id===card.dataset.shotId);if(!shot||!e.target.dataset.field)return;shot[e.target.dataset.field]=e.target.value;renderShots();updateReadiness();scheduleDraftSave()});
$("#shot-editor-list").addEventListener("change",e=>{const card=e.target.closest("[data-shot-id]");if(!card)return;const shot=state.shots.find(s=>s.id===card.dataset.shotId);if(shot&&e.target.dataset.field){shot[e.target.dataset.field]=e.target.value;renderShots();scheduleDraftSave()}});
$("#shot-editor-list").addEventListener("click",e=>{const id=e.target.dataset.removeShot;if(id){state.shots=state.shots.filter(s=>s.id!==id);renderAll();renderShotEditor();scheduleDraftSave();return}const duplicate=e.target.dataset.duplicateShot;if(duplicate){duplicateShot(duplicate);return}const up=e.target.dataset.moveUp;if(up){moveShot(up,-1);return}const down=e.target.dataset.moveDown;if(down){moveShot(down,1);return}});
$("#new-project").addEventListener("click",()=>{if(!confirm("Start a new project? Save or export your current draft first if you need it."))return;$("#project-name").value="Untitled cinematic project";["prompt","negative-prompt","subject","environment","seed"].forEach(id=>$("#"+id).value="");["lighting","mood"].forEach(id=>$("#"+id).selectedIndex=0);$("#model").value="auto";$("#aspect").value="16:9";$("#resolution").value="720p";$("#duration").value="5";$("#fps").value="24";$("#quality").value="cinematic";$("#audio").checked=false;$("#refine").checked=true;state.shots=defaultShots();clearReference();renderAll();scheduleDraftSave();setView("studio")});
$("#clear-library").addEventListener("click",()=>{if(!confirm("Delete all locally saved RF983 MOTION drafts from this browser? Export any projects you want to keep."))return;localStorage.removeItem(STORAGE_KEY);renderLibrary();toast("Local project library cleared.")});
$("#library-grid").addEventListener("click",e=>{const id=e.target.dataset.loadProject;if(!id)return;const p=getProjects().find(x=>x.id===id);if(!p)return;applyForm(p);saveDraft(true);setView("studio");toast("Project draft opened.")});
document.addEventListener("input",e=>{if(e.target.matches("input,textarea,select")&&!e.target.matches("#import-file,#reference-image")){scheduleDraftSave();renderProductionDesk()}});
document.addEventListener("change",e=>{if(e.target.matches("input,textarea,select")&&!e.target.matches("#import-file,#reference-image")){scheduleDraftSave();renderProductionDesk()}});
document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="s"){e.preventDefault();saveProjectToLibrary()}});
}
function init(){const apiInput=$("#api-base");if(apiInput){let savedApi="";try{savedApi=localStorage.getItem(API_BASE_KEY)||""}catch(error){}const githubPages=location.hostname.endsWith(".github.io");apiInput.value=savedApi||(!githubPages?location.origin:"");setApiBadge("unconfigured",savedApi?"API READY TO CHECK":"API NOT SET")}state.shots=defaultShots();state.projects=getProjects();try{const draft=JSON.parse(localStorage.getItem(DRAFT_KEY)||"null");if(draft)applyForm(draft);else renderAll()}catch(e){renderAll()}bindEvents();renderAll()}
init();
})();