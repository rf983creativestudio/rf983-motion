(() => {
"use strict";
const $ = (selector, root=document) => root.querySelector(selector);
const $$ = (selector, root=document) => Array.from(root.querySelectorAll(selector));
const STORAGE_KEY = "rf983-motion-projects-v2";
const DRAFT_KEY = "rf983-motion-active-v2";
const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const state = { shots: [], reference: null, activeView: "studio", projects: [], previewUrl: null };
const defaultShots = () => [
  {id:makeId(),name:"Establishing shot",framing:"Extreme wide",camera:"Slow push-in",action:"Reveal the environment and establish the subject's place in it.",duration:5},
  {id:makeId(),name:"The approach",framing:"Medium wide",camera:"Tracking",action:"Follow the subject moving through the environment with clear screen direction.",duration:5},
  {id:makeId(),name:"Final detail",framing:"Close-up",camera:"Gentle orbit",action:"End on a meaningful visual detail or emotional beat.",duration:5}
];
function makeId(){return "s"+Math.random().toString(36).slice(2,10)}
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
function renderShotEditor(){const host=$("#shot-editor-list");host.innerHTML=state.shots.map((s,i)=>'<article class="shot-editor panel" data-shot-id="'+escapeHtml(s.id)+'"><div class="shot-visual">SHOT '+String(i+1).padStart(2,"0")+' / RF983</div><div><div class="shot-fields"><div><label>SHOT TITLE</label><input data-field="name" value="'+escapeHtml(s.name)+'" maxlength="60"></div><div><label>FRAMING</label><select data-field="framing">'+options(["Extreme wide","Wide","Medium wide","Medium","Medium close-up","Close-up","Extreme close-up","Overhead","Low angle"],s.framing)+'</select></div><div><label>CAMERA MOVEMENT</label><select data-field="camera">'+options(["Locked-off","Slow push-in","Pull-back","Tracking","Pan left","Pan right","Tilt up","Tilt down","Crane","Gentle orbit","Handheld"],s.camera)+'</select></div><div class="shot-field-wide"><label>VISIBLE ACTION / BEAT</label><textarea data-field="action" maxlength="500">'+escapeHtml(s.action)+'</textarea></div><div><label>PLANNED DURATION</label><select data-field="duration">'+options(["3","4","5","6","8","10","12","15"],String(s.duration),v=>v+" seconds")+'</select></div></div><div class="shot-actions"><small>Sequence position '+(i+1)+' of '+state.shots.length+'</small><button data-remove-shot="'+escapeHtml(s.id)+'" '+(state.shots.length===1?"disabled":"")+'>Remove shot ×</button></div></div></article>').join("");}
function options(values,selected,labeler){return values.map(v=>'<option value="'+escapeHtml(v)+'" '+(String(v)===String(selected)?"selected":"")+'>'+escapeHtml(labeler?labeler(v):v)+'</option>').join("")}
function renderLibrary(){const projects=getProjects();$("#library-count").textContent=projects.length+" projects";const host=$("#library-grid");if(!projects.length){host.innerHTML='<div class="empty-library"><div style="font-size:28px">▧</div><b>Your creative library is waiting.</b><small>Save a project draft to keep it in this browser, or export a portable JSON project file.</small></div>';return}host.innerHTML=projects.map(p=>'<article class="library-card"><div class="library-art">RF983 / '+escapeHtml(p.aspect||"16:9")+'</div><h3>'+escapeHtml(p.name)+'</h3><p>'+escapeHtml((p.prompt||"No creative brief yet").slice(0,110))+'</p><div class="library-card-footer"><small>'+new Date(p.updatedAt||Date.now()).toLocaleDateString()+' · '+(p.shots||[]).length+' shots</small><button data-load-project="'+escapeHtml(p.id)+'">Open draft ↗</button></div></article>').join("")}
function updateReadiness(){const prompt=$("#prompt").value.trim();const essentials=[!!prompt,state.shots.length>0,true];const ready=essentials.filter(Boolean).length;$("#check-prompt").textContent=essentials[0]?"●":"○";$("#check-prompt-label").textContent=essentials[0]?"Ready":"Missing";$("#check-shots").textContent=essentials[1]?"●":"○";$("#check-shots-label").textContent=state.shots.length+" shots";$("#check-reference").textContent=state.reference?"●":"○";$("#check-reference-label").textContent=state.reference?"Added":"Optional";$("#readiness-fill").style.width=(ready/3*100)+"%";$("#readiness-text").textContent=ready+" of 3 essentials ready"}
function renderAll(){renderShots();updateReadiness();$("#prompt-count").textContent=$("#prompt").value.length+" / 4000";if(state.activeView==="storyboard")renderShotEditor()}
function buildPrompt(){const parts=[];const subject=$("#subject").value.trim(),environment=$("#environment").value.trim(),lighting=$("#lighting").value,mood=$("#mood").value;if(subject)parts.push(subject);if(environment)parts.push("Set in "+environment+".");if(lighting)parts.push(lighting+".");if(mood)parts.push("Mood: "+mood.toLowerCase()+".");const current=$("#prompt").value.trim();const addition=parts.join(" ");if(!addition){toast("Add at least one director's note first.");return}$("#prompt").value=[current,addition].filter(Boolean).join(current?" ":"");$("#prompt").dispatchEvent(new Event("input"));toast("Director's notes added to the master prompt.")}
function handleReference(file){if(!file)return;if(!["image/jpeg","image/png","image/webp"].includes(file.type)){toast("Choose a JPG, PNG or WEBP image.");return}if(file.size>MAX_IMAGE_BYTES){toast("Image is larger than 10 MB. Choose a smaller reference.");return}if(state.previewUrl)URL.revokeObjectURL(state.previewUrl);state.previewUrl=URL.createObjectURL(file);state.reference={name:file.name,type:file.type,size:file.size,url:state.previewUrl};$("#reference-thumb").src=state.previewUrl;$("#reference-name").textContent=file.name;$("#reference-size").textContent=(file.size/1024/1024).toFixed(2)+" MB · local preview only";$("#reference-preview").classList.remove("hidden");$("#drop-zone").classList.add("hidden");updateReadiness()}
function clearReference(){if(state.previewUrl)URL.revokeObjectURL(state.previewUrl);state.previewUrl=null;state.reference=null;$("#reference-image").value="";$("#reference-preview").classList.add("hidden");$("#drop-zone").classList.remove("hidden");updateReadiness()}
function addShot(){if(state.shots.length>=12){toast("This planner supports up to 12 shots per project.");return}state.shots.push({id:makeId(),name:"New shot",framing:"Wide",camera:"Locked-off",action:"Describe the visible action and the beat this shot should communicate.",duration:5});renderAll();renderShotEditor();toast("Shot added to storyboard.")}
async function refreshDiagnostics(){
 const button=$("#refresh-diagnostics"),host=$("#diagnostic-results"),note=$("#diagnostic-note");
 let base=$("#api-base").value.trim();
 while(base.endsWith("/"))base=base.slice(0,-1);
 if(!(base.startsWith("http://")||base.startsWith("https://"))){note.textContent="Enter a valid HTTP or HTTPS API address.";return}
 button.disabled=true;button.textContent="Checking…";note.textContent="Checking API health, worker and model registry…";
 const row=(name,detail,status,kind)=>'<div><span class="arch-dot '+kind+'"></span><b>'+escapeHtml(name)+'</b><small>'+escapeHtml(detail)+'</small><em>'+escapeHtml(status)+'</em></div>';
 try{
  const paths=["/api/health","/api/worker/status","/api/models","/api/system/ready"];
  const responses=await Promise.all(paths.map(path=>fetch(base+path,{headers:{Accept:"application/json"},cache:"no-store"})));
  if(responses.some(r=>!r.ok))throw new Error("One or more API checks returned an error.");
  const [health,worker,models,ready]=await Promise.all(responses.map(r=>r.json()));
  const verified=models.verified_model_count||0;
  host.innerHTML=[
   row("API connection",health.service+" · version "+health.version,"CONNECTED","ready"),
   row("GPU worker",worker.connected?(worker.worker_id||"Worker online"):"No fresh heartbeat",worker.connected?"CONNECTED":"OFFLINE",worker.connected?"pending":"offline"),
   row("Verified models",verified+" verified · "+models.models.length+" candidates",verified?"VERIFIED":"NONE",verified?"ready":"offline"),
   row("Generation pipeline",ready.generation_reason||"Not enabled",ready.generation_enabled?"ENABLED":"DISABLED",ready.generation_enabled?"ready":"offline")
  ].join("");
  note.textContent="Diagnostics received. A connected heartbeat or detected GPU does not prove a video can be rendered.";
 }catch(error){
  host.innerHTML=row("API connection","Could not reach "+base,"UNAVAILABLE","offline")+row("GPU worker","Cannot verify without API","UNKNOWN","offline")+row("Verified models","Cannot verify without API","UNKNOWN","offline")+row("Generation pipeline","Must remain disabled","DISABLED","offline");
  note.textContent="Check that the API is running, the address is correct, and CORS allows this frontend origin. "+error.message;
 }finally{button.disabled=false;button.textContent="Run system check ↻"}
}
function bindEvents(){
$$(".nav-item").forEach(b=>b.addEventListener("click",()=>setView(b.dataset.view)));
$$("[data-go]").forEach(b=>b.addEventListener("click",()=>setView(b.dataset.go)));
$("#refresh-diagnostics").addEventListener("click",refreshDiagnostics);\n$("#prompt").addEventListener("input",()=>{$("#prompt-count").textContent=$("#prompt").value.length+" / 4000";updateReadiness()});
$("#prompt-guide").addEventListener("click",()=>$("#guide-dialog").showModal());
$("#build-prompt").addEventListener("click",buildPrompt);
$("#reference-image").addEventListener("change",e=>handleReference(e.target.files&&e.target.files[0]));
$("#remove-reference").addEventListener("click",clearReference);
const drop=$("#drop-zone");["dragenter","dragover"].forEach(evt=>drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.add("dragover")}));["dragleave","drop"].forEach(evt=>drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.remove("dragover")}));drop.addEventListener("drop",e=>handleReference(e.dataTransfer.files&&e.dataTransfer.files[0]));
$("#random-seed").addEventListener("click",()=>$("#seed").value=Math.floor(Math.random()*2147483647));
$("#save-project").addEventListener("click",saveProjectToLibrary);$("#export-project").addEventListener("click",exportProject);
$("#generate").addEventListener("click",()=>{$("#generation-status").textContent="Generation is unavailable: no authenticated GPU worker is connected. Your prompt and reference image have not been uploaded.";toast("Generation safely blocked — no inference engine connected.")});
$("#add-shot").addEventListener("click",addShot);
$("#reset-shots").addEventListener("click",()=>{state.shots=defaultShots();renderAll();renderShotEditor();toast("Storyboard reset to the starter sequence.")});
$("#shot-editor-list").addEventListener("input",e=>{const card=e.target.closest("[data-shot-id]");if(!card)return;const shot=state.shots.find(s=>s.id===card.dataset.shotId);if(!shot||!e.target.dataset.field)return;shot[e.target.dataset.field]=e.target.value;renderShots();updateReadiness()});
$("#shot-editor-list").addEventListener("change",e=>{const card=e.target.closest("[data-shot-id]");if(!card)return;const shot=state.shots.find(s=>s.id===card.dataset.shotId);if(shot&&e.target.dataset.field){shot[e.target.dataset.field]=e.target.value;renderShots()}});
$("#shot-editor-list").addEventListener("click",e=>{const id=e.target.dataset.removeShot;if(!id)return;state.shots=state.shots.filter(s=>s.id!==id);renderAll();renderShotEditor()});
$("#new-project").addEventListener("click",()=>{if(!confirm("Start a new project? Save or export your current draft first if you need it."))return;$("#project-name").value="Untitled cinematic project";["prompt","negative-prompt","subject","environment","seed"].forEach(id=>$("#"+id).value="");["lighting","mood"].forEach(id=>$("#"+id).selectedIndex=0);$("#model").value="auto";$("#aspect").value="16:9";$("#resolution").value="720p";$("#duration").value="5";$("#fps").value="24";$("#quality").value="cinematic";$("#audio").checked=false;$("#refine").checked=true;state.shots=defaultShots();clearReference();renderAll();setView("studio")});
$("#clear-library").addEventListener("click",()=>{if(!confirm("Delete all locally saved RF983 MOTION drafts from this browser? Export any projects you want to keep."))return;localStorage.removeItem(STORAGE_KEY);renderLibrary();toast("Local project library cleared.")});
$("#library-grid").addEventListener("click",e=>{const id=e.target.dataset.loadProject;if(!id)return;const p=getProjects().find(x=>x.id===id);if(!p)return;applyForm(p);saveDraft(true);setView("studio");toast("Project draft opened.")});
document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="s"){e.preventDefault();saveProjectToLibrary()}});
}
function init(){state.shots=defaultShots();state.projects=getProjects();try{const draft=JSON.parse(localStorage.getItem(DRAFT_KEY)||"null");if(draft)applyForm(draft);else renderAll()}catch(e){renderAll()}bindEvents();renderAll()}
init();
})();