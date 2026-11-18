// Toasts: flash messages rendered by core/partials/toasts.html, plus
// window.InkHive.toast(text, level, { persist }) for scripts (look: base.css,
// motion: motion.css). A toast closes when its countdown bar finishes, so
// hovering it pauses the countdown. Flash-message errors, and script toasts
// with persist: true, stay until closed.
(function () {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const LEVELS = new Set(["info", "success", "warning", "error"]);

  function stack() {
    let el = document.getElementById("toastStack");
    if (!el) {
      el = document.createElement("div");
      el.className = "toast-stack";
      el.id = "toastStack";
      el.setAttribute("aria-live", "polite");
      document.body.appendChild(el);
    }
    return el;
  }

  function close(toast) {
    if (toast.classList.contains("is-closing")) return;
    toast.classList.add("is-closing");
    toast.classList.remove("is-open");
    const remove = () => toast.remove();
    toast.addEventListener("transitionend", remove, { once: true });
    setTimeout(remove, 600); // in case transitionend never fires
  }

  function open(toast) {
    toast.querySelector(".toast-close")?.addEventListener("click", () => close(toast));
    const timer = toast.querySelector(".toast-timer");
    if (timer) {
      timer.addEventListener("animationend", () => close(toast), { once: true });
      if (reduceMotion) setTimeout(() => close(toast), 6000);
    }
    // Next frame, so the closed state paints first and the transition runs.
    requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add("is-open")));
  }

  function toast(text, level = "info", { persist = false } = {}) {
    if (!LEVELS.has(level)) level = "info";
    const el = document.createElement("div");
    el.className = `toast toast--${level}`;
    el.setAttribute("role", level === "error" ? "alert" : "status");
    const p = document.createElement("p");
    p.className = "toast-text";
    p.textContent = text;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "toast-close";
    button.setAttribute("aria-label", "Dismiss");
    button.textContent = "×";
    el.append(p, button);
    if (!persist) {
      const timer = document.createElement("span");
      timer.className = "toast-timer";
      timer.setAttribute("aria-hidden", "true");
      el.appendChild(timer);
    }
    stack().appendChild(el);
    open(el);
    return el;
  }

  window.InkHive = Object.assign(window.InkHive || {}, { toast });
  document.querySelectorAll("#toastStack .toast").forEach(open);
})();
