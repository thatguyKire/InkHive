document.addEventListener("DOMContentLoaded", () => {
  const host = document.getElementById("teacherPerformanceGraph");
  if (!host) return;

  const raw = document.getElementById("teacher_perf_data");
  let data = { labels: [], uploads: [], messages: [], strokes: [] };
  if (raw) {
    try { data = JSON.parse(raw.textContent); } catch {}
  }

  const canvas = document.createElement("canvas");
  host.textContent = "";
  host.appendChild(canvas);

  new Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [
        InkHiveChart.series("uploads", "Uploads", data.uploads),
        InkHiveChart.series("messages", "Messages", data.messages),
        InkHiveChart.series("strokes", "Strokes", data.strokes),
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        y: { beginAtZero: true }
      },
      plugins: {
        legend: { position: "top" }
      }
    }
  });
});