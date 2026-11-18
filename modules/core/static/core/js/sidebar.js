// App-shell navigation: collapsible rail on desktop, slide-in drawer on phones,
// and the current page marked in the menu. Styles live in core/css/base.css.
document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const toggleBtn = document.getElementById("toggleBtn");
  const mobileBtn = document.getElementById("mobileNavBtn");
  const backdrop = document.getElementById("sidebarBackdrop");
  if (!sidebar) return;

  const STORAGE_KEY = "inkhive.sidebarCollapsed";
  const phone = window.matchMedia("(max-width: 768px)");

  // ----- Desktop: collapse to an icon rail, remembered per browser -----
  function setCollapsed(collapsed) {
    sidebar.classList.toggle("collapsed", collapsed);
    if (toggleBtn) {
      toggleBtn.setAttribute("aria-expanded", String(!collapsed));
      toggleBtn.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
    }
  }

  let remembered = false;
  try { remembered = localStorage.getItem(STORAGE_KEY) === "1"; } catch (e) { /* storage blocked */ }
  if (remembered) {
    // Restore without animating the sidebar shut on every page load.
    document.documentElement.classList.add("no-shell-motion");
    setCollapsed(true);
    requestAnimationFrame(() => requestAnimationFrame(() =>
      document.documentElement.classList.remove("no-shell-motion")));
  }

  toggleBtn?.addEventListener("click", () => {
    const collapsed = !sidebar.classList.contains("collapsed");
    setCollapsed(collapsed);
    try { localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0"); } catch (e) { /* storage blocked */ }
  });

  // ----- Phone: drawer -----
  function setDrawer(open) {
    sidebar.classList.toggle("open", open);
    backdrop?.classList.toggle("show", open);
    mobileBtn?.setAttribute("aria-expanded", String(open));
    mobileBtn?.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    document.body.style.overflow = open ? "hidden" : "";
    if (open) sidebar.querySelector(".menu-btn")?.focus();
  }

  mobileBtn?.addEventListener("click", () => setDrawer(!sidebar.classList.contains("open")));
  backdrop?.addEventListener("click", () => setDrawer(false));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && sidebar.classList.contains("open")) {
      setDrawer(false);
      mobileBtn?.focus();
    }
  });
  // Following a link closes the drawer (the bell and chat buttons stay on the page).
  sidebar.addEventListener("click", (e) => {
    if (phone.matches && e.target.closest("a.menu-btn[href]:not([href='#'])")) setDrawer(false);
  });
  phone.addEventListener("change", (e) => { if (!e.matches) setDrawer(false); });

  // ----- Current page -----
  const path = window.location.pathname;
  let best = null;
  sidebar.querySelectorAll("a.menu-btn[href]").forEach((link) => {
    const href = link.getAttribute("href");
    if (!href || href === "#") return;
    if (path === href || path.startsWith(href)) {
      if (!best || href.length > best.getAttribute("href").length) best = link;
    }
  });
  best?.setAttribute("aria-current", "page");
});
