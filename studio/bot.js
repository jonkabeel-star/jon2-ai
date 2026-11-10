(()=>{"use strict";
const host=document.createElement("section");host.className="bot-panel";host.innerHTML='<div class="bot-head"><div class="bot-avatar">J2</div><div><b>Jon2 Bot</b><small>مساعد الاستوديو · إصدار محلي أولي</small></div><span class="bot-state">● يعمل محليًا</span></div><div class="bot-body"><div class="bot-welcome"><b>أهلًا! أنا Jon2 Bot 🤖</b><p>أقدر أساعدك بإرشادات البرمجة وأمثلة جاهزة. هذه النسخة لا تتصل بنموذج ذكاء اصطناعي بعد.</p></div><div id="botMessages" class="bot-messages" aria-live="polite"></div><div class="bot-suggestions"><button type="button" data-q="اكتب لي صفحة HTML بسيطة">إنشاء صفحة HTML</button><button type="button" data-q="اشرح لي HTML وCSS وJavaScript">شرح لغات الويب</button><button type="button" data-q="كيف أصلح خطأ في الكود؟">مساعدة في إصلاح خطأ</button></div><form id="botForm" class="bot-form"><input id="botInput" maxlength="1000" placeholder="اكتب سؤالك هنا..." autocomplete="off" aria-label="رسالتك إلى Jon2 Bot"><button type="submit">إرسال</button></form></div>';
const anchor=document.querySelector(".preview-panel");if(anchor)anchor.after(host);else document.querySelector("main")?.append(host);
const messages=host.querySelector("#botMessages"),input=host.querySelector("#botInput");
function say(text,who){const p=document.createElement("p");p.className="bot-msg "+who;p.textContent=text;messages.append(p);messages.scrollTop=messages.scrollHeight;}
function answer(q){const s=q.toLowerCase();if(/html|صفحة|موقع|ويب/.test(s))return "لبداية صفحة ويب: أنشئ index.html واكتب الهيكل الأساسي، ثم اربط style.css للتصميم وscript.js للتفاعل. أقدر أجهز لك مثالًا، لكن لا أستطيع إدخال الكود في ملفاتك تلقائيًا في هذه النسخة.";
if(/css|تصميم|لون|شكل/.test(s))return "CSS مسؤول عن شكل الصفحة. ابدأ بتنسيق body، ثم استخدم Flexbox أو Grid لترتيب العناصر، وأضف media queries لدعم الهاتف.";
if(/javascript|جافاسكربت|تفاعل|زر/.test(s))return "JavaScript يضيف التفاعل. اربط الزر عبر addEventListener، واستخدم textContent لتحديث النص بأمان بدل إدخال HTML غير موثوق.";
if(/خطأ|اصلح|إصلاح|bug|error/.test(s))return "لأساعدك في إصلاح الخطأ: انسخ رسالة الخطأ كاملة مع الجزء المرتبط من الكود. سأشرح السبب وأقترح نسخة مصححة؛ راجعها قبل تشغيلها.";
if(/اشرح|تعلم|يعني/.test(s))return "أكيد. اكتب اسم التقنية أو الصق الكود الذي تريد فهمه، وسأقسم الشرح إلى خطوات بسيطة مع مثال.";
return "وصلني سؤالك. هذه النسخة تعمل دون اتصال بنموذج لغوي، لذلك لا أستطيع فهم الأسئلة المفتوحة أو توليد حلول عامة بعد. أرسل سؤالًا عن HTML أو CSS أو JavaScript أو الصق رسالة خطأ.";
}
function send(q){q=q.trim();if(!q)return;say(q,"user");say(answer(q),"assistant");}
host.querySelector("#botForm").addEventListener("submit",e=>{e.preventDefault();send(input.value);input.value="";input.focus();});
host.querySelectorAll("[data-q]").forEach(b=>b.addEventListener("click",()=>send(b.dataset.q)));
})();