(()=>{"use strict";
const KEY="jon2_studio_projects_v1";
const defaults={"index.html":{type:"html",content:"<!doctype html>\n<html lang=\"ar\" dir=\"rtl\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n<title>مشروعي الأول</title>\n<link rel=\"stylesheet\" href=\"style.css\">\n</head>\n<body>\n<main class=\"card\">\n<h1>أهلًا بك في مشروعي!</h1>\n<p>ابدأ تعديل ملفاتك من Jon2 Studio.</p>\n<button id=\"hello\">اضغط هنا</button>\n</main>\n<script src=\"script.js\"><\\/script>\n</body>\n</html>"},"style.css":{type:"css",content:"body{margin:0;min-height:100vh;display:grid;place-items:center;background:#eef2ff;font-family:Arial,sans-serif}.card{background:white;padding:36px;border-radius:20px;box-shadow:0 15px 45px #23315b22;text-align:center}h1{color:#425bd5}button{border:0;border-radius:10px;padding:12px 20px;background:#526de5;color:white;cursor:pointer}"},"script.js":{type:"js",content:"document.getElementById('hello')?.addEventListener('click',()=>{\n alert('مرحبًا بك في Jon2 Studio!');\n});"}};
let project={name:"مشروعي الأول",files:structuredClone(defaults)},active="index.html";
const HISTORY_KEY="jon2_studio_agent_history_v1";let agentHistory=[];
function remember(){try{agentHistory.push(JSON.stringify(project));if(agentHistory.length>12)agentHistory.shift();localStorage.setItem(HISTORY_KEY,JSON.stringify(agentHistory));}catch(e){}}
function restoreAgentHistory(){try{const h=JSON.parse(localStorage.getItem(HISTORY_KEY)||"[]");if(Array.isArray(h))agentHistory=h.slice(-12);}catch(e){agentHistory=[];}}
const $=id=>document.getElementById(id);
const validPath=n=>typeof n==="string"&&n.length<=100&&/^[a-zA-Z0-9][a-zA-Z0-9._/-]*$/.test(n)&&!n.startsWith("/")&&!n.split("/").some(p=>!p||p==="."||p===".."||p.startsWith("."));
const kind=n=>{const e=n.split(".").pop().toLowerCase();return e==="html"?"html":e==="css"?"css":e==="js"?"js":"text";};
function save(){try{localStorage.setItem(KEY,JSON.stringify(project));$("saveState").textContent="تم الحفظ محليًا";}catch(e){$("saveState").textContent="تعذر الحفظ محليًا";}}
function load(){try{const p=JSON.parse(localStorage.getItem(KEY)||"null");if(!p||!p.files)return;const files={};for(const [n,f] of Object.entries(p.files)){if(validPath(n)&&f&&typeof f.content==="string")files[n]={type:kind(n),content:f.content.slice(0,250000)};}if(Object.keys(files).length)project={name:String(p.name||"مشروعي").slice(0,60),files};}catch(e){console.warn("Studio local restore failed",e);}}
function read(){if(project.files[active])project.files[active].content=$("codeEditor").value;}
function lines(){$("lineNumbers").textContent=Array.from({length:Math.max(1,$("codeEditor").value.split("\n").length)},(_,i)=>i+1).join("\n");}
function render(){const list=$("fileList");list.replaceChildren();Object.keys(project.files).forEach(n=>{const b=document.createElement("button");b.className="file-item"+(n===active?" active":"");b.textContent=(kind(n)==="html"?"◇ ":kind(n)==="css"?"▤ ":kind(n)==="js"?"⌘ ":"▧ ")+n;b.onclick=()=>{read();active=n;render();};list.append(b);});$("projectName").textContent=project.name;$("activeFile").textContent=active;const glyph=$("fileGlyph");if(glyph)glyph.textContent=kind(active)==="html"?"◇":kind(active)==="css"?"▤":kind(active)==="js"?"⌘":"▧";$("languageLabel").textContent=kind(active).toUpperCase();$("codeEditor").value=project.files[active].content;lines();save();}
function build(){let h=project.files["index.html"]?.content||"<!doctype html><html><body></body></html>";const c=project.files["style.css"]?.content||"",j=project.files["script.js"]?.content||"";if(c){const style="<style>\n"+c.split("</style").join("<\\/style")+"\n</style>";const re=new RegExp("</head>","i");h=re.test(h)?h.replace(re,style+"\n</head>"):style+h;}if(j){const script="<script>\n"+j.split("</script").join("<\\/script")+"\n<\\/script>";const re=new RegExp("</body>","i");h=re.test(h)?h.replace(re,script+"\n</body>"):h+script;}return h;}
function preview(){read();save();$("preview").srcdoc=build();}
function download(n,c,t){const u=URL.createObjectURL(new Blob([c],{type:t})),a=document.createElement("a");a.href=u;a.download=n;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
$("codeEditor").addEventListener("input",()=>{read();lines();save();});$("codeEditor").addEventListener("scroll",()=>{$("lineNumbers").scrollTop=$("codeEditor").scrollTop;});$("codeEditor").addEventListener("keydown",e=>{if(e.key==="Tab"){e.preventDefault();e.target.setRangeText("  ",e.target.selectionStart,e.target.selectionEnd,"end");e.target.dispatchEvent(new Event("input"));}});
$("runCode").onclick=preview;$("refreshPreview").onclick=preview;$("downloadFile").onclick=()=>{read();download(active,project.files[active].content,"text/plain;charset=utf-8");save();};$("downloadProject").onclick=()=>{read();download("jon2-project.json",JSON.stringify({format:"jon2-studio-project-v1",name:project.name,files:project.files},null,2),"application/json");save();};
$("addFile").onclick=()=>{const n=prompt("اسم الملف (مثل app.js أو notes.txt):");if(!n)return;if(!validPath(n)||project.files[n]){alert("اسم غير صالح أو الملف موجود بالفعل.");return;}read();project.files[n]={type:kind(n),content:""};active=n;render();};
$("renameProject").onclick=()=>{const n=prompt("اسم المشروع:",project.name);if(n&&n.trim()){project.name=n.trim().slice(0,60);save();render();}};
$("newProject").onclick=()=>{if(!confirm("إنشاء مشروع جديد؟ سيتم استبدال المشروع المحفوظ على هذا المتصفح."))return;project={name:"مشروع جديد",files:structuredClone(defaults)};active="index.html";render();preview();};
window.Jon2Studio={
 getSnapshot:()=>({name:project.name,activeFile:active,files:Object.fromEntries(Object.entries(project.files).map(([n,f])=>[n,{type:f.type,content:f.content}]))}),
 applyAgentChanges:(changes)=>{
  if(!Array.isArray(changes)||changes.length>10)return{ok:false,message:"عدد التغييرات غير صالح."};
  const seen=new Set(),normalized=[];
  for(const item of changes){
   if(!item||!validPath(item.path)||typeof item.content!=="string"||item.content.length>250000||seen.has(item.path))return{ok:false,message:"رفضت مساحة العمل تغييرًا غير صالح أو مسارًا مكررًا. لم يتم تطبيق أي تغيير."};
   seen.add(item.path);normalized.push({path:item.path,content:item.content});
  }
  const additions=normalized.filter(x=>!project.files[x.path]).length;
  if(Object.keys(project.files).length+additions>40)return{ok:false,message:"لا يمكن تطبيق التغييرات لأنها ستتجاوز حد 40 ملفًا."};
  if(!normalized.length)return{ok:true,changed:[]};
  const candidate=Object.fromEntries(Object.entries(project.files).map(([name,file])=>[name,{type:file.type,content:file.content}]));
  for(const item of normalized)candidate[item.path]={type:kind(item.path),content:item.content};
  const total=Object.values(candidate).reduce((sum,file)=>sum+file.content.length,0);
  if(total>1000000)return{ok:false,message:"حجم المشروع بعد التعديل يتجاوز حد الفحص والحفظ الآمن (1MB). لم يتم تطبيق أي تغيير."};
  if(window.Jon2Brain&&typeof window.Jon2Brain.analyze==="function"){
   const before=window.Jon2Brain.analyze(project.files),after=window.Jon2Brain.analyze(candidate);
   const known=new Set((before.issues||[]).filter(issue=>issue.level==="error").map(issue=>[issue.file,issue.code,issue.message].join("|")));
   const introduced=(after.issues||[]).filter(issue=>issue.level==="error"&&!known.has([issue.file,issue.code,issue.message].join("|")));
   if(introduced.length)return{ok:false,message:"أوقف الفحص الوقائي تطبيق التعديلات لوجود خطأ بنيوي جديد: "+introduced.slice(0,3).map(issue=>issue.file+" — "+issue.message).join("؛ ")+" . لم يتم تطبيق أي تغيير."};
  }
  remember();
  for(const item of normalized)project.files[item.path]={type:kind(item.path),content:item.content};
  active=normalized[normalized.length-1].path;
  render();preview();
  return{ok:true,changed:normalized.map(x=>x.path)};
 },
 createAgentFile:(name,content)=>{if(!validPath(name)||Object.keys(project.files).length>=40||project.files[name]||typeof content!=="string"||content.length>250000)return{ok:false,message:"اسم الملف غير صالح أو موجود، أو تم تجاوز الحد الآمن."};remember();project.files[name]={type:kind(name),content};active=name;render();preview();return{ok:true,message:"تم إنشاء "+name+" داخل مساحة العمل المحلية."};},
 updateAgentFile:(name,content)=>{if(!project.files[name]||typeof content!=="string"||content.length>250000)return{ok:false,message:"الملف غير موجود أو المحتوى يتجاوز الحد."};remember();project.files[name].content=content;active=name;render();preview();return{ok:true,message:"تم تحديث "+name+" مع حفظ نسخة سابقة للتراجع."};},
 undoAgentChange:()=>{const old=agentHistory.pop();if(!old)return{ok:false,message:"لا توجد تغييرات للتراجع عنها."};try{project=JSON.parse(old);localStorage.setItem(HISTORY_KEY,JSON.stringify(agentHistory));active=project.files[active]?active:Object.keys(project.files)[0];render();preview();return{ok:true,message:"تم التراجع عن آخر تغيير."};}catch(e){return{ok:false,message:"تعذر استعادة النسخة السابقة."};}}
};
restoreAgentHistory();load();render();preview();
})();