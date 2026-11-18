document.addEventListener("DOMContentLoaded", () => {
  try {
    const bellBtn = document.getElementById("notifBell");
    const panel = document.getElementById("notificationsPanel");
    const badge = document.getElementById("notifBadge");
    const dot = document.getElementById("notifDot");
    const list = panel?.querySelector(".notif-list");

    if (!bellBtn || !panel) {
      console.warn("Notifications: '#notifBell' or '#notificationsPanel' not found.");
      return;
    }


    function getCookie(name) {
      const m = document.cookie.match(`(^|;)\\s*${name}\\s*=\\s*([^;]+)`);
      return m ? m.pop() : "";
    }

    function showUnread(count) {
      if (!badge) return;
      if (count > 0) {
        const previous = Number(badge.textContent) || 0;
        badge.textContent = String(count);
        badge.classList.remove("hidden");
        if (count > previous && previous > 0) {
          // Replay the pop when more notifications arrive (see motion.css).
          badge.classList.remove("is-bumped");
          void badge.offsetWidth;
          badge.classList.add("is-bumped");
        }
      } else {
        badge.classList.add("hidden");
        badge.textContent = "";
      }
    }

    function renderTitleBody(rawContent) {
      const text = String(rawContent || "").trim();
      if (!text) return { title: "", body: "" };
      const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
      let title = lines.length ? lines[0] : text.slice(0, 80);
      if (title.length > 80) title = title.slice(0, 80) + "…";
      const body = lines.length > 1 ? lines.slice(1).join(" ") : (text.length > title.length ? text.slice(title.length).trim() : "");
      return { title, body };
    }

    const seenIds = new Set();

    function prependItem(item) {
      if (!list || !item) return;
      if (seenIds.has(String(item.id))) return; // dedupe
      seenIds.add(String(item.id));
      const { title, body } = renderTitleBody(item.content);
      const tag = item.session_id ? 'Announcement' : '';
      const div = document.createElement("div");
      div.className = "notification-item";
      div.setAttribute("data-id", item.id);

      const entry = document.createElement('div');
      entry.className = 'notif-entry';

      const titleDiv = document.createElement('div');
      titleDiv.className = 'notif-title';
      const strong = document.createElement('strong');
      strong.textContent = title;
      titleDiv.appendChild(strong);
      if (tag) {
        const tagSpan = document.createElement('span');
        tagSpan.className = 'notif-tag';
        tagSpan.textContent = ' ' + tag;
        titleDiv.appendChild(tagSpan);
      }
      entry.appendChild(titleDiv);

      if (body) {
        const bodyDiv = document.createElement('div');
        bodyDiv.className = 'notif-body';
        bodyDiv.textContent = body;
        entry.appendChild(bodyDiv);
      }

      const timeEl = document.createElement('time');
      timeEl.className = 'notif-time';
      timeEl.textContent = new Date(item.created_at || Date.now()).toLocaleString();
      entry.appendChild(timeEl);

      div.appendChild(entry);
      list.prepend(div);
      while (list.children.length > 50) list.removeChild(list.lastChild);
    }

    async function refreshCount() {
      try {
        const r = await fetch("/notifications/unread-count/", { credentials: "same-origin" });
        if (!r.ok) return;
        const d = await r.json();
        showUnread(d.count || 0);
      } catch (e) {
        console.warn("Notifications: refreshCount failed", e);
      }
    }

    async function bootstrapList() {
      if (!list) return;
      try {
        const r = await fetch("/notifications/latest/", { credentials: "same-origin" });
        if (!r.ok) return;
        const d = await r.json();
        if (Array.isArray(d.items)) {
          // Clear & rebuild without losing dedupe memory? Keep seenIds; avoid re-adding existing
          while (list.firstChild) list.removeChild(list.firstChild);
          const known = new Set(seenIds);
          seenIds.clear();
          // Reverse items so that when we prepend them one by one, the newest ends up at the top
          // (Assuming d.items comes as [Newest, ..., Oldest])
          // 1. Prepend Oldest -> [Oldest]
          // 2. Prepend Newer -> [Newer, Oldest]
          // 3. Prepend Newest -> [Newest, Newer, Oldest]
          d.items.slice().reverse().forEach(it => prependItem(it));
          if (!d.items.length) {
            const empty = document.createElement("p");
            empty.className = "notif-empty";
            empty.textContent = "You're all caught up.";
            list.appendChild(empty);
          }
          // Only items that arrived since the last poll get the entrance animation.
          if (known.size) {
            list.querySelectorAll(".notification-item").forEach(el => {
              if (!known.has(el.dataset.id)) el.classList.add("is-new");
            });
          }
        }
      } catch (e) {
        console.warn("Notifications: bootstrapList failed", e);
      }
    }

    async function markAllRead() {
      try {
        await fetch("/notifications/mark-all-read/", {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-CSRFToken": getCookie("csrftoken") }
        });
      } catch (e) {}
      showUnread(0);
    }

    // Next to the bell, kept inside the viewport (below it when there is no room beside it).
    function placePanel() {
      const gap = 10;
      const rect = bellBtn.getBoundingClientRect();
      const width = panel.offsetWidth;
      let left = rect.right + gap;
      let top = rect.top;
      if (left + width > window.innerWidth - gap) {
        left = Math.max(gap, Math.min(rect.left, window.innerWidth - width - gap));
        top = rect.bottom + gap;
      }
      top = Math.max(gap, Math.min(top, window.innerHeight - panel.offsetHeight - gap));
      panel.style.left = `${left}px`;
      panel.style.top = `${top}px`;
    }

    // Toggle dropdown (stopPropagation to prevent immediate close)
    bellBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const opened = panel.classList.toggle("show");
      bellBtn.setAttribute("aria-expanded", opened ? "true" : "false");
      
      if (opened) {
        placePanel();
        markAllRead();
      }
    });

    // Close when clicking outside
    document.addEventListener("click", (e) => {
      if (!panel.classList.contains("show")) return;
      if (!e.target.closest("#notificationsPanel") && !e.target.closest("#notifBell")) {
        panel.classList.remove("show");
        bellBtn.setAttribute("aria-expanded", "false");
      }
    });

    function startPollingLoop() {
      refreshCount();
      bootstrapList();
      setInterval(() => {
        refreshCount();
        bootstrapList();
      }, 5000); // always keep a 5s poll
    }

    // init
    startPollingLoop();
    if (window.DEBUG) console.debug("Notifications: Bell initialized");
  } catch (err) {
    console.error("Notifications: initialization error", err);
  }
});