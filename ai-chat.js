(() => {
  "use strict";

  const Jon2Chat = {
    name: "Jon2 AI",
    version: "1.0.0",

    async sendMessage(message) {
      const text = String(message || "").trim();

      if (!text) {
        throw new Error("اكتب رسالتك الأول.");
      }

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ message: text })
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
          throw new Error(
            data.error || "خدمة المحادثة غير متصلة حاليًا."
          );
        }

        return data.reply || data.response || "لم يصل رد من الذكاء الاصطناعي.";
      } catch (error) {
        throw new Error(
          error.message || "تعذر الاتصال بخدمة المحادثة."
        );
      }
    }
  };

  window.Jon2Chat = Jon2Chat;
})();
