// Reads the whiteboard page settings from the inert JSON block rendered by
// Django ({{ board_config|json_script:"board-config" }}) and exposes them as
// the globals the board scripts expect. Must load before whiteboard.js.
(function () {
  "use strict";
  const el = document.getElementById("board-config");
  let cfg = {};
  try { cfg = JSON.parse(el ? el.textContent : "{}"); } catch (e) { console.error("Bad board config", e); }
  window.CAN_DRAW = !!cfg.canDraw;
  window.IS_TEACHER = !!cfg.isTeacher;
  window.CHAT_ENABLED = cfg.chatEnabled !== false;
  window.CURRENT_SESSION_ID = cfg.sessionId || "";
  window.CURRENT_USER_ID = cfg.userId || "";
  window.SNAPSHOT_URL = cfg.snapshotUrl || "";
  window.RECORD_STROKE_URL = cfg.recordStrokeUrl || "";
})();
