# Jon2 Kaggle Remote Control Bridge (Arabic)

## الحالة
هذه إضافة أولية آمنة بنمط **pull**: جلسة Kaggle النشطة تسحب ملفات مهام JSON من مستودع GitHub خاص، تنفذ أوامر تشخيصية محددة فقط، ثم تكتب النتائج والإيصالات إلى المستودع نفسه.

هذا ليس تحكمًا دائمًا أو وصولًا مباشرًا إلى حساب Kaggle. يجب أن تكون جلسة Notebook قيد التشغيل، وقد تنتهي وفق حدود Kaggle.

## المعمارية المطلوبة
- مستودع تحكم GitHub **خاص مستقل**، وليس المستودع العام أو أي مستودع عام.
- Kaggle Secrets:
  - `JON2_BRIDGE_TOKEN`: Fine-grained PAT لمستودع التحكم الخاص فقط، بصلاحية Contents: Read and write وMetadata: Read.
  - `JON2_BRIDGE_REPO`: اسم المستودع بصيغة `owner/private-repo`.
  - `JON2_BRIDGE_BRANCH`: فرع قناة التحكم الذي يحتوي `bridge/inbox` و`bridge/outbox` و`bridge/receipts`. في الإعداد الحالي استخدم `setup/kaggle-bridge-control-plane`. إذا حُذفت القيمة، يستخدم الجسر `main`.
- شغّل Notebook `notebooks/Jon2_Kaggle_Remote_Bridge.ipynb` في Kaggle بعد ربط الـSecrets.
- ينشئ مرسل المهام ملفًا جديدًا مثل `bridge/inbox/audit-001.json`.
- يقرأ الجسر النتائج من `bridge/outbox/audit-001.json` وإيصال التنفيذ من `bridge/receipts/audit-001.json`.

## شكل المهمة
```json
{
  "id": "audit-001",
  "command": "audit_environment",
  "args": {}
}
```

المهمة ملف جديد لا يُعدّل بعد إنشائه. استخدم معرفًا فريدًا لكل مهمة.

## الأوامر المتاحة في الإصدار الأول
- `audit_environment`: إصدارات Python/PyTorch، CUDA، وعدد الملفات ومسارات عينة.
- `list_training_files`: يسرد ملفات TXT/JSONL/JSON وأحجامها وبصماتها.
- `checkpoint_metadata`: يقرأ metadata الآمن من checkpoint باستخدام `weights_only=True` ولا يصدّر tensors.
- `sha256_file`: يحسب بصمة ملف داخل `/kaggle/input` أو `/kaggle/working`.

## حدود أمان مقصودة
- لا يوجد `eval` أو `exec` أو أوامر shell أو تنفيذ كود وارد.
- لا يوجد تدريب أو تغيير أوزان أو كتابة checkpoints.
- لا يوجد حذف أو رفع بيانات تدريب أو نشر.
- لا يُقبل إلا مستودع تحكم خاص؛ يتوقف الجسر إذا اكتشف أن المستودع عام.
- يمكن تحديد فرع قناة التحكم عبر `JON2_BRIDGE_BRANCH`؛ لا يلزم دمج PR إعداد المجلدات في `main`.
- كتابة النتائج قابلة لإعادة المحاولة: إذا كانت النتيجة الموجودة مطابقة، لا يعيد الجسر كتابتها؛ وإذا اختلفت يرفض الاستبدال.
- مسارات الملفات محصورة في `/kaggle/input` و`/kaggle/working`.
- لا تضع PAT في الكود أو في المحادثة أو في مخرجات Notebook.
- لا تمنح PAT صلاحيات Actions أو Administration أو Workflows.
- لا تضع بيانات تدريب أو أوزان داخل مستودع التحكم.

## ما لم يتم تفعيله بعد
لا يمكن إنشاء قناة أوامر حقيقية من ChatGPT إلى Kaggle حتى:
1. تنشئ/تحدد مستودع تحكم خاصًا وتمنح GitHub connector صلاحية الوصول إليه.
2. تضيف السرّين إلى Kaggle Secrets.
3. تشغّل Notebook في جلسة Kaggle.

لا توجد خدمة inbound أو جلسة Kaggle دائمة. أي مهمة ستنتظر حتى تكون Notebook تعمل.
