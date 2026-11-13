(() => {
  "use strict";

  const NOT_READY = "عقل Jon2 غير جاهز للرد";
  const Jon2Chat = {
    name: "Jon2 AI",
    version: "1.1.0",

    async sendMessage(message) {
      const text = String(message || "").trim();
      if (!text) throw new Error("اكتب رسالتك الأول.");

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text })
        });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
          const detail = typeof data.detail === "string"
            ? data.detail
            : (data.detail && typeof data.detail.message === "string"
              ? data.detail.message : "");
          throw new Error(detail || data.error || NOT_READY);
        }

        const reply = typeof data.reply === "string" ? data.reply.trim() : "";
        if (!reply || data.response_mode !== "jon2_original_model_only") {
          throw new Error(NOT_READY);
        }
        return reply;
      } catch (error) {
        throw new Error(error?.message || NOT_READY);
      }
    }
  };

  window.Jon2Chat = Jon2Chat;
})();
