document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-qq-ai-widget]").forEach((widget) => {
    const trigger = widget.querySelector(".qq-ai-trigger");
    const panel = widget.querySelector(".qq-ai-panel");
    const composer = widget.querySelector(".qq-ai-composer");
    const messageInput = composer.querySelector("input");
    const systemButton = widget.querySelector("[data-qq-ai-system]");
    const chatButton = widget.querySelector("[data-qq-ai-chat]");
    const close = () => {
      widget.classList.remove("is-open");
      trigger.setAttribute("aria-expanded", "false");
      panel.setAttribute("aria-hidden", "true");
    };
    trigger.addEventListener("click", () => {
      const opening = !widget.classList.contains("is-open");
      widget.classList.toggle("is-open", opening);
      trigger.setAttribute("aria-expanded", String(opening));
      panel.setAttribute("aria-hidden", String(!opening));
    });
    document.addEventListener("click", (event) => {
      if (!widget.contains(event.target)) close();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") close();
    });
    widget.querySelectorAll(".qq-ai-suggestions button").forEach((question) => {
      question.addEventListener("click", () => {
        messageInput.value = question.textContent;
        messageInput.focus();
      });
    });
    composer.addEventListener("submit", (event) => {
      event.preventDefault();
      messageInput.value = "";
    });
    systemButton.addEventListener("click", () => widget.classList.add("is-system"));
    chatButton.addEventListener("click", () => widget.classList.remove("is-system"));
  });
});
