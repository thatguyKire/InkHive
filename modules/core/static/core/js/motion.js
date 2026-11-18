// Count-up numbers for core/css/motion.css: an element with [data-count-up]
// counts from 0 to its own value the first time it is on screen. Without
// this script (or with reduced motion) the number simply shows as is.
(function () {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function countUp(el) {
    const text = el.textContent.trim();
    const target = Number(text.replace(/,/g, ""));
    if (!Number.isFinite(target) || target <= 0 || reduceMotion) return;
    const decimals = (text.split(".")[1] || "").length;
    const duration = Math.min(1200, 500 + target * 15);
    const start = performance.now();
    el.style.fontVariantNumeric = "tabular-nums";
    function frame(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      el.textContent = (target * eased).toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      });
      if (t < 1) requestAnimationFrame(frame);
      else el.textContent = text;
    }
    el.textContent = "0";
    requestAnimationFrame(frame);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const counters = document.querySelectorAll("[data-count-up]");
    if (!counters.length) return;
    if (!("IntersectionObserver" in window)) { counters.forEach(countUp); return; }
    const seen = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        seen.unobserve(entry.target);
        countUp(entry.target);
      });
    }, { threshold: 0.6 });
    counters.forEach((el) => seen.observe(el));
  });
})();
