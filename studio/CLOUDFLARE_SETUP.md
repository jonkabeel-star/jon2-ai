# إعداد Jon2 Studio ووكيل البرمجة على Cloudflare

هذا المشروع مستقل عن موقع Jon2 AI الأساسي. لا تغيّر إعدادات الموقع الأصلي.

## إعداد النشر الحالي
- Git branch: `jon2-studio-private-bootstrap`
- Pages project: `jon2-studio`
- Build command: فارغ
- Build output directory: `studio`
- Root directory: جذر المستودع
- ملف `studio/_routes.json` يجعل Pages Functions تعمل على مسارات `/api/*) فقط حتى لا تمر طلبات الملفات الثابتة عبر Function.

## أولًا: حماية الموقع
1. افتح Cloudflare Dashboard ثم **Workers & Pages → jon2-studio**.
2. افتح إعدادات Access/Zero Trust واحمِ عنوان الإنتاج `jon2-studio.pages.dev` وأي عناوين معاينة تستخدمها.
3. أنشئ سياسة **Allow** لحسابك أنت فقط. لا تستخدم Everyone أو سياسة عامة.
4. اختبر في نافذة خاصة دون تسجيل دخول: يجب منع الوصول.
5. سجّل الدخول بالحساب المسموح وتأكد من فتح الاستوديو.

## ثانيًا: ربط Workers AI المجاني
1. من مشروع Pages افتح **Settings → Functions → Bindings**.
2. اختر **Add binding → Workers AI**.
3. اسم المتغير (Variable name) يجب أن يكون بالضبط: `AI`.
4. احفظ التغيير.
5. لا تفعّل Workers Paid، ولا تضف وسيلة دفع، ولا تستخدم نموذجًا يتطلب خطة مدفوعة.

النموذج المحدد في الكود هو `@cf/zai-org/glm-4.7-flash`. تسرد Cloudflare هذا النموذج ضمن Workers AI، وتذكر أن Workers Free يتضمن 10,000 Neurons يوميًا دون رسوم. إذا انتهت الحصة، يجب أن يفشل الطلب بدلًا من الترقية أو الدفع.

## ثالثًا: متغيرات تحقق Cloudflare Access
من **Settings → Environment variables** في مشروع Pages، أضف المتغيرين التاليين في Production وPreview:

- `ACCESS_TEAM_DOMAIN`: اسم نطاق فريق Access، مثل `your-team.cloudflareaccess.com` من دون https.
- `ACCESS_AUD`: قيمة Audience (AUD) الخاصة بتطبيق Access الذي يحمي Jon2 Studio.

هذه القيم ليست كلمات مرور. لا ترسلها في المحادثة. لا تضف JWT أو مفاتيح خاصة إلى GitHub.

## رابعًا: إعادة النشر والاختبار
1. احفظ إعدادات Binding والمتغيرات.
2. أعد نشر Pages من الفرع `jon2-studio-private-bootstrap`.
3. افتح `/api/agent` بعد تسجيل الدخول؛ يجب أن يعرض حالة الخدمة.
4. افتح الاستوديو واطلب من Jon2 Bot إنشاء صفحة بسيطة.
5. تأكد أن الملفات الجديدة ظهرت في قائمة الملفات وأن المعاينة تحدّثت.
6. افتح الموقع في نافذة خاصة دون تسجيل الدخول؛ يجب أن يمنع Access الوصول.

## حدود واضحة
- حد Workers AI المجاني الحالي: 10,000 Neurons يوميًا. يعاد ضبطه يوميًا حسب توقيت Cloudflare؛ ليس استخدامًا غير محدود ولا ضمانًا مدى الحياة.
- عند نفاد الحصة، قد يتوقف الذكاء حتى إعادة الضبط.
- الوكيل يقرأ الملفات التي يرسلها المحرر إلى Cloudflare AI، لذلك لا ترسل أسرارًا أو بيانات خاصة.
- ينشئ ويحدّث ملفات مشروع المتصفح؛ لا يحذف ملفات، ولا يشغّل Python/Node أو أوامر Linux، ولا ينشئ خوادم أو قواعد بيانات، ولا ينشر مواقع المستخدم تلقائيًا.
- ملفات المشاريع تبقى في localStorage على المتصفح الحالي. صدّر نسخة JSON احتياطية.
- لا تدمج PR #40 في `main` دون موافقة صريحة.
