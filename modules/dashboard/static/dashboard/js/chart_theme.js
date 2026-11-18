// Chart.js colours from the palette (core/css/tokens.css), so every
// dashboard shows a metric in the same colour and a retheme needs no JS change.
window.InkHiveChart = {
  series(metric, label, data) {
    const css = getComputedStyle(document.documentElement);
    return {
      label,
      data,
      backgroundColor: css.getPropertyValue(`--chart-${metric}`).trim(),
      borderColor: css.getPropertyValue(`--chart-${metric}-edge`).trim(),
      borderWidth: 2,
      borderRadius: 6,
    };
  },
};
