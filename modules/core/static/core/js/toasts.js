// Flash messages as toasts (markup: core/partials/toasts.html, look: base.css,
// motion: motion.css). A toast closes when its countdown bar finishes, so
// hovering it pauses the countdown. Errors stay until closed.
(function () {
  const stack = document.getElementById("toastStack");
  if (!stack) return;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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

  stack.querySelectorAll(".toast").forEach(open);
})();
