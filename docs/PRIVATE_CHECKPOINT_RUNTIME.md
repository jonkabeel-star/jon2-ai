# تشغيل Jon2 من ملف أوزان خاص دون Kaggle

## مبدأ الأمان

- لا تضع `jon2-last.pt` داخل Git أو صورة Docker.
- لا تستخدم Kaggle CLI أو `KAGGLE_API_TOKEN` في تشغيل الخادم.
- ضع checkpoint على جهاز الخادم في مجلد خاص، ثم اربطه داخل الحاوية عند المسار `/app/model-weights/jon2-last.pt`.
- قيمة SHA256 المعتمدة حاليًا: `edf96971187f93642f36282e270c2d2f3a6db39565b30d7898e856a49e0eaec2`.
- أي اختلاف في البصمة يوقف التشغيل قبل تحميل النموذج.

## تشغيل محلي على جهاز Linux/macOS يملك Python/Docker

من جذر المستودع، وبعد نقل الملف الخاص إلى مجلد محلي خارج المستودع مثل `~/jon2-private-weights/`:

```sh
mkdir -p ~/jon2-private-weights
# ضع jon2-last.pt يدويًا في هذا المجلد الخاص، ولا ترفعه إلى GitHub
docker build -t jon2-private-api .
docker run --rm -p 8000:8000 \
  -v "$HOME/jon2-private-weights:/app/model-weights:ro" \
  -e JON2_PRELOAD_MODEL=true \
  jon2-private-api
```

افتح `http://127.0.0.1:8000/api/health/live` ثم `http://127.0.0.1:8000/api/health`.
المتوقع قبل مراجعة الجودة: `model_loaded=true` إذا تم التحميل بنجاح، لكن `chat_ready=false` و`release_approved=false`.

## اختبار الاستدلال العربي

داخل بيئة الحاوية أو بيئة Python المثبتة، شغّل:

```sh
python /app/ai_engine/verify_runtime.py
```

الاختبار يرسل سؤالًا بالفصحى، وسؤالًا بالمصرية، وسؤالًا حسابيًا. نجاحه يعني أن النموذج أنتج نصًا واجتاز فحص سلامة سطحيًا فقط؛ لا يعني أن الإجابات صحيحة أو مفهومة. راجع الإجابات يدويًا.

لا يقوم الاختبار بتغيير `JON2_INFERENCE_TESTED` أو `JON2_QUALITY_REVIEW_PASSED` أو `JON2_CHAT_RELEASE_APPROVED`.

## ربط Safari

- عند فتح الموقع من نفس خادم FastAPI، يكتشف `index.html` عنوان `location.origin` تلقائيًا.
- عند استضافة الواجهة على نطاق مختلف، اضبط `window.JON2_API_BASE_URL` إلى أصل خادمك عبر ملف إعداد خاص بالبيئة، مع السماح بذلك الأصل في CORS.
- واجهة Safari تستخدم `/api/health` و`/api/chat` من الخادم نفسه.
- الخادم يرفض `/api/chat` حتى تكون بوابات الاعتماد الثلاثة مفعلة بعد الاختبار والمراجعة البشرية.

## ما لا يفعله هذا التغيير

هذا التعديل يجهز برنامج الخادم ومسار الأوزان والربط والاختبار. لا ينشئ معالج CPU أو جهازًا يعمل على مدار الساعة. يجب تشغيل Docker على جهاز تملكه ويظل متصلًا بالشبكة للوصول إليه من أجهزة أخرى. لا يمكن لـ iPhone/a-Shell وحده تشغيل PyTorch CPU server بهذا الإعداد.

لا تفتح المحادثة العامة لمجرد أن `/api/health/live` يعرض `alive`؛ هذا فحص حياة للخادم فقط.