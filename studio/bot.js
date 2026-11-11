(()=>{"use strict";
const STORAGE_KEY="jon2_bot_log_v1";
const host=document.createElement("section");host.className="bot-panel";
host.innerHTML='<div class="bot-head"><div class="bot-avatar">J2</div><div><b>Jon2 Bot</b><small>مساعد البرمجة · سجل محفوظ وأدوات تطوير</small></div><span class="bot-state" id="botState">● يفحص الاتصال</span></div><div class="bot-body"><div class="bot-welcome"><b>أهلًا! أنا Jon2 Bot 🤖</b><p>أفحص مشروعك، أكتب الكود، أصلح الأخطاء، وأحفظ سجل المحادثات على هذا الجهاز.</p></div><div class="bot-controls"><button type="button" id="botScan">فحص المشروع</button><button type="button" id="botRepair">إصلاحات آمنة</button><button type="button" id="botUndo">تراجع</button><button type="button" id="botLog">سجل المحادثات</button><button type="button" id="botExport">تنزيل السجل</button><button type="button" id="botClear">مسح السجل</button></div><div class="bot-controls bot-tools"><button type="button" data-task="راجع الكود الحالي واكتشف الأخطاء المنطقية والبرمجية، ثم أصلح الأخطاء المؤكدة فقط.">مراجعة وإصلاح الكود</button><button type="button" data-task="حسّن أداء المشروع وسرعة تحميله واستهلاك الذاكرة، مع الحفاظ على الوظائف والتصميم الحاليين.">تحسين الأداء</button><button type="button" data-task="راجع أمان المشروع وابحث عن الثغرات ومخاطر إدخال البيانات والتعامل مع الملفات، ثم اقترح إصلاحات آمنة.">فحص الأمان</button></div><div id="botReport" class="bot-report" aria-live="polite"></div><div id="botLogPanel" class="bot-report" hidden></div><div id="botMessages" class="bot-messages" aria-live="polite"></div><form id="botForm" class="bot-form"><input id="botInput" maxlength="4000" placeholder="اكتب طلب برمجي أو فكرة تريد تنفيذها..." autocomplete="off" aria-label="اطلب من Jon2 Bot"><button type="submit" id="botSend">تنفيذ</button></form><p class="bot-safety">سجل المحادثات محفوظ محليًا في هذا المتصفح. عند استخدام المساعد، يُرسل الطلب والملفات ذات الصلة إلى Cloudflare Workers AI. لا ترسل كلمات مرور أو مفاتيح سرية.</p></div>';
const anchor=document.querySelector(".preview-panel");if(anchor)anchor.after(host);else document.querySelector("main")?.append(host);
const $=id=>host.querySelector("#"+id),messages=$("botMessages"),report=$("botReport"),input=$("botInput"),send=$("botSend"),state=$("botState"),logPanel=$("botLogPanel");
function loadLog(){try{const v=JSON.parse(localStorage.getItem(STORAGE_KEY)||"[]");return Array.isArray(v)?v.filter(x=>x&&typeof x.text==="string"&&typeof x.who==="string").slice(-80):[]}catch{return[]}}
let log=loadLog();
const history=log.slice(-8).map(x=>({role:x.who==="assistant"?"assistant":"user",content:x.text.slice(0,1200)}));
function persist(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify(log.slice(-80)))}catch{state.textContent="● تعذر حفظ السجل"}}
function snapshot(){return window.Jon2Studio?.getSnapshot?.()||{files:{},activeFile:null};}
function say(t,who,save=true){const p=document.createElement("p");p.className="bot-msg "+who;p.textContent=t;messages.append(p);messages.scrollTop=messages.scrollHeight;if(save){log.push({who,text:t,time:new Date().toISOString()});log=log.slice(-80);persist();}}
function renderLog(){logPanel.replaceChildren();logPanel.hidden=false;const head=document.createElement("div");head.className="bot-report-head";head.textContent="آخر "+log.length+" رسالة محفوظة على هذا الجهاز";logPanel.append(head);log.slice(-12).reverse().forEach(x=>{const item=document.createElement("article");item.className="bot-issue";const b=document.createElement("b");b.textContent=(x.who==="user"?"أنت":"Jon2 Bot")+" · "+new Date(x.time).toLocaleString("ar-EG");const p=document.createElement("p");p.textContent=x.text.slice(0,500);item.append(b,p);logPanel.append(item)});}
function setBusy(on){send.disabled=on;input.disabled=on;send.textContent=on?"يعمل...":"تنفيذ";state.textContent=on?"● ينفذ الطلب":"● جاهز";}
function scan(){const result=window.Jon2Brain.analyze(snapshot().files);report.replaceChildren();const h=document.createElement("div");h.className="bot-report-head";h.textContent=result.summary;report.append(h);(result.issues||[]).forEach(x=>{const a=document.createElement("article");a.className="bot-issue "+x.level;const b=document.createElement("b");b.textContent=(x.level==="error"?"خطأ":x.level==="warning"?"تحذير":"ملاحظة")+" · "+x.file;const p=document.createElement("p");p.textContent=x.message+(x.detail?" — "+x.detail:"");a.append(b,p);report.append(a);});return result;}
function repair(){const changes=window.Jon2Brain.repair(snapshot().files);if(!changes.length){say("لم أجد إصلاحات آلية آمنة من الأنواع المدعومة. لم أغيّر أي ملف.","assistant");return;}let done=0;for(const c of changes){const r=window.Jon2Studio.updateAgentFile(c.name,c.after);if(r.ok){done++;say("تم إصلاح "+c.name+": "+c.reason,"assistant");}}say("اكتمل تطبيق "+done+" إصلاحات محلية. استخدم «تراجع» لاستعادة النسخة السابقة.","assistant");scan();}
function validPath(name){return typeof name==="string"&&name.length<=100&&/^[a-zA-Z0-9][a-zA-Z0-9._/-]*$/.test(name)&&!name.startsWith("/")&&!name.split("/").some(p=>!p||p==="."||p===".."||p.startsWith("."));}
async function askAgent(task){
 const snap=snapshot(),files=snap.files||{};
 const payload={task,files,activeFile:snap.activeFile||"",history:history.slice(-4)};
 const response=await fetch("/api/agent",{method:"POST",credentials:"same-origin",headers:{"content-type":"application/json"},body:JSON.stringify(payload)});
 let data={};try{data=await response.json()}catch{}
 if(!response.ok){const detail=typeof data.detail==="string"?data.detail.slice(0,220):"";throw new Error((data.error||("تعذر الاتصال بالوكيل (HTTP "+response.status+")."))+(detail?"\nالتفاصيل التقنية: "+detail:""));}
 if(!Array.isArray(data.changes)||typeof data.message!=="string")throw new Error("وصل رد غير مكتمل من الوكيل.");
 const changed=[];
 for(const item of data.changes){
  if(!validPath(item.path)||typeof item.content!=="string")throw new Error("رفضت الواجهة مسار ملف غير آمن. لم أطبق هذا التغيير.");
  const current=snapshot().files||{};
  const result=current[item.path]?window.Jon2Studio.updateAgentFile(item.path,item.content):window.Jon2Studio.createAgentFile(item.path,item.content);
  if(!result.ok)throw new Error("تعذر تطبيق "+item.path+": "+result.message+"\nقد تكون بعض التغييرات السابقة قد طُبقت بالفعل.");
  changed.push(item.path);
 }
 let answer=data.message;
 if(changed.length)answer+="\n\nالملفات التي تم تحديثها: "+changed.join("، ")+". راجع المعاينة والملفات الآن.";
 else answer+="\n\nلم يتم تعديل أي ملف.";
 say(answer,"assistant");
 history.push({role:"user",content:task},{role:"assistant",content:answer});
 if(history.length>8)history.splice(0,history.length-8);
 if(changed.length)scan();
}
function localCommand(q){
 if(/^(فحص|حلل|راجع|اكتشف الأخطاء|تحليل المشروع)/.test(q)){const r=scan();say("انتهى الفحص. عدد المشكلات المحددة: "+(r.issues||[]).length+".","assistant");return true;}
 if(/^(إصلاحات آمنة|اصلح الأخطاء الآمنة|إصلاح محلي)/.test(q)){repair();return true;}
 if(/^(تراجع|الغاء آخر|استرجع)$/.test(q)){const r=window.Jon2Studio.undoAgentChange();say(r.message,"assistant");return true;}
 if(/^(السجل|سجل المحادثات)$/.test(q)){renderLog();return true;}
 return false;
}
$("botScan").addEventListener("click",()=>{const r=scan();say("اكتمل الفحص. المشكلات: "+(r.issues||[]).length+".","assistant");});
$("botRepair").addEventListener("click",repair);
$("botUndo").addEventListener("click",()=>{const r=window.Jon2Studio.undoAgentChange();say(r.message,"assistant");});
$("botLog").addEventListener("click",()=>{if(!logPanel.hidden)logPanel.hidden=true;else renderLog();});
$("botExport").addEventListener("click",()=>{const blob=new Blob([JSON.stringify(log,null,2)],{type:"application/json"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download="jon2-chat-history.json";a.click();URL.revokeObjectURL(url);say("تم تجهيز نسخة قابلة للتنزيل من سجل المحادثات.","assistant");});
$("botClear").addEventListener("click",()=>{if(!confirm("هل تريد مسح سجل المحادثات المحفوظ على هذا الجهاز؟"))return;log=[];history.length=0;persist();messages.replaceChildren();logPanel.replaceChildren();logPanel.hidden=true;say("تم مسح سجل المحادثات المحلي.","assistant");});
host.querySelectorAll("[data-task]").forEach(btn=>btn.addEventListener("click",()=>{input.value=btn.dataset.task;input.focus()}));
$("botForm").addEventListener("submit",async e=>{e.preventDefault();const q=input.value.trim();if(!q)return;say(q,"user");input.value="";if(localCommand(q))return;setBusy(true);try{await askAgent(q);}catch(err){say("لم أتمكن من تنفيذ الطلب: "+String(err.message||err),"assistant");state.textContent="● يحتاج مراجعة";}finally{setBusy(false);}});
log.forEach(x=>say(x.text,x.who,false));
state.textContent="● جاهز";
if(!log.length)say("Jon2 Bot جاهز. سجل المحادثات سيبقى محفوظًا على هذا المتصفح حتى تمسحه أو تحذف بيانات الموقع.","assistant");
})();