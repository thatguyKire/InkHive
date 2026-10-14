// Live refresh of the attendance table (moved out of the template for CSP).
(function(){
  const actions = document.querySelector('.card-actions');
  const url = actions?.getAttribute('data-json-url');
  if (!url) return;
  const table = document.getElementById('attendanceTable');
  const lastSpan = document.getElementById('att-last-updated');
  function fmt(ts){
    if (!ts) return '';
    try { const d = new Date(ts); return d.toLocaleString(); } catch { return ts; }
  }
  async function tick(){
    try {
      const res = await fetch(url, { headers: { 'Accept': 'application/json' }});
      const data = await res.json();
      if (!data.ok) return;
      const rows = Array.from(table.querySelectorAll('tbody tr'));
      const map = new Map(rows.map(r => [String(r.getAttribute('data-user-id')), r]));
      (data.participants || []).forEach(p => {
        const r = map.get(String(p.user_id));
        if (!r) return;
        const cells = r.querySelectorAll('td');
        // cells: 0=name,1=email,2=joined,3=last_active
        if (p.joined_at) cells[2].textContent = fmt(p.joined_at);
        cells[3].textContent = fmt(p.last_active) || fmt(p.joined_at);
      });
      if (lastSpan && data.now) lastSpan.textContent = fmt(data.now);
    } catch {}
  }
  tick();
  setInterval(tick, 10000); // update every 10s
})();
