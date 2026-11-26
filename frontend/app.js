const prompt=document.querySelector('#prompt');
const count=document.querySelector('#count');
const imageInput=document.querySelector('#image');
const preview=document.querySelector('#preview');
const notice=document.querySelector('#notice');
let previewUrl=null;
prompt.addEventListener('input',()=>count.textContent=`${prompt.value.length} / 1800`);
imageInput.addEventListener('change',()=>{
  if(previewUrl) URL.revokeObjectURL(previewUrl);
  preview.replaceChildren();
  const file=imageInput.files?.[0];
  if(!file){preview.classList.add('hidden');return;}
  if(!['image/png','image/jpeg','image/webp'].includes(file.type)){notice.textContent='Please choose a JPG, PNG or WEBP image.';imageInput.value='';return;}
  previewUrl=URL.createObjectURL(file);
  const img=document.createElement('img');img.alt='Selected visual reference';img.src=previewUrl;preview.append(img);preview.classList.remove('hidden');
});
document.querySelector('#mode').addEventListener('change',e=>{
 notice.textContent=e.target.value==='image'?'Image-to-video is planned. Add a reference image above; generation is not active yet.':'Generation engine is not connected. This prototype does not submit or store your prompt.';
});
document.querySelector('#enhance').addEventListener('click',()=>{
 notice.textContent='Prompt guide: describe (1) subject and action, (2) setting, (3) camera framing and movement, (4) lighting, (5) visual texture, and (6) mood. Keep action physically clear and chronological.';
});
document.querySelector('#generate').addEventListener('click',()=>{
 notice.textContent=prompt.value.trim()?'Studio interface is ready, but no inference worker is connected. Your prompt and reference image have not been uploaded.':'Add a scene description first. No generation request has been sent.';
});
window.addEventListener('beforeunload',()=>{if(previewUrl)URL.revokeObjectURL(previewUrl);});
