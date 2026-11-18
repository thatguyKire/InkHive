document.addEventListener("DOMContentLoaded", () => {
  const host = document.getElementById("participationGraph");
  if (!host) return;
  const raw = document.getElementById("student_perf_data");
  let data = { labels: [], strokes: [], uploads: [] };
  if (raw) { try { data = JSON.parse(raw.textContent); } catch {} }

  const canvas = document.createElement("canvas");
  host.textContent = "";
  host.appendChild(canvas);

  new Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [
        InkHiveChart.series("strokes", "Strokes", data.strokes),
        InkHiveChart.series("uploads", "Uploads", data.uploads)
      ]
    },
    options: { responsive:true, maintainAspectRatio:false, scales:{ y:{ beginAtZero:true } } }
  });
});