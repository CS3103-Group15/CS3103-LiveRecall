/*
 * Working but deliberately naive LiveRecall browser starter.
 *
 * Provided mechanical behavior:
 *   - opens a WebSocket
 *   - sends CLIENT_HELLO
 *   - visibly appends every received CAPTION_UPDATE
 *   - displays whether an update is provisional/final
 *
 * Graded TODOs:
 *   - replace revisions rather than appending duplicates
 *   - maintain >=60 s of finalized local state
 *   - implement 30 s default recall + 15/30/60 s views
 *   - automatic reconnect + correct resume state
 *   - HISTORY merge/deduplication
 *   - usable final UI
 */

const WS_URL = "ws://127.0.0.1:8765";
const statusEl = document.getElementById("status");
const liveEl = document.getElementById("live");
const recallEl = document.getElementById("recall");

const captions = new Map();
const finalizedHistory = new Map();

const LOCAL_RETENTION_SECONDS = 70
const LIVE_DISPLAY_SECONDS = 15;

let ws;

let reconnectTimer = null;
let reconnectAttempts = 0;

let lastFinalSegment = 0;
let lastFinalRevision = 0;

const HISTORY_REQUEST_SECONDS = 60;

const BASE_RECONNECT_MS = 500;
const MAX_RECONNECT_MS = 5000;


function numericClientId() {
  const key = "liverecall-client-id";

  let value = sessionStorage.getItem(key);

  if (!value) {
    value = String(Math.floor(100000 + Math.random() * 900000));
    sessionStorage.setItem(key, value);
  }

  return Number(value);
}


function remove_old_entries() {
  const now = Date.now() / 1000;
  const cutoff = now - LOCAL_RETENTION_SECONDS;

  for (const [segment, caption] of finalizedHistory) {
    if (caption.source_ts < cutoff) {
      finalizedHistory.delete(segment);
    }
  }

  const liveCutoff = now - LIVE_DISPLAY_SECONDS;

  for (const [segment, caption] of captions) {
    if (caption.final && caption.source_ts < liveCutoff) {
      caption.element.remove();
      captions.delete(segment);
    }
  }
}


function storeFinalCaption(msg) {
  if (!msg.final) {
    return;
  }

  const existing = finalizedHistory.get(msg.segment);

  if (existing) {
    return;
  }

  finalizedHistory.set(msg.segment, {
    segment: msg.segment,
    revision: msg.revision,
    source_ts: msg.source_ts,
    text: msg.text,
    final: true
  });

  remove_old_entries();
}


function updateFinalCheckpoint(msg) {
  if (!msg.final) {
    return;
  }

  if (msg.segment > lastFinalSegment || (msg.segment === lastFinalSegment && msg.revision > lastFinalRevision)) {
    lastFinalSegment = msg.segment;
    lastFinalRevision = msg.revision;
  }
}


function handleCaptionUpdate(msg) {
  if (msg.segment <= lastFinalSegment) {
    return;
  }

  const existing = captions.get(msg.segment);
  if (existing) {
    if (existing.final) {
      return;
    }

    if (msg.revision <= existing.revision) {
      return;
    }
  }

  const now = Date.now() / 1000;
  const liveCutoff = now - LIVE_DISPLAY_SECONDS;
  const shouldDisplayLive = msg.source_ts >= liveCutoff;

  let row = existing?.element ?? null;

  if (shouldDisplayLive) {
    if (!row) {
      row = document.createElement("div");
      liveEl.appendChild(row);
    }

    row.className = msg.final
        ? "caption final"
        : "caption provisional";

    row.textContent = msg.text;

  } else if (row) {
    row.remove();
    row = null;
  }

  if (row) {
    captions.set(msg.segment, {
        revision: msg.revision,
        final: msg.final,
        text: msg.text,
        source_ts: msg.source_ts,
        element: row
    });
  } else {
    captions.delete(msg.segment);
  }

  if (msg.final) {
    storeFinalCaption(msg);
    updateFinalCheckpoint(msg);
  }

  const shouldAutoScroll = liveEl.scrollHeight - liveEl.scrollTop - liveEl.clientHeight < 60;
  if (shouldAutoScroll) {
    liveEl.scrollTop = liveEl.scrollHeight;
  }
}


function getRecentCaptions(seconds) {
  remove_old_entries();

  const now = Date.now() / 1000;
  const cutoff = now - seconds;

  return Array.from(finalizedHistory.values())
      .filter(caption => caption.source_ts >= cutoff)
      .sort((a, b) => a.segment - b.segment);
}


function showRecall(seconds = 30) {
  const recent = getRecentCaptions(seconds);

  // Clear the previous recall display.
  recallEl.replaceChildren();

  if (recent.length === 0) {
    recallEl.textContent = `No finalized captions in the last ${seconds} seconds.`;
    return;
  }

  for (const caption of recent) {
    const row = document.createElement("div");
    row.className = "recall-caption";

    const timestamp = document.createElement("span");
    timestamp.className = "recall-time";

    timestamp.textContent = new Date(caption.source_ts * 1000).toLocaleTimeString();

    const text = document.createElement("span");
    text.textContent = caption.text;

    row.append(timestamp, text);
    recallEl.appendChild(row);
  }
}


function handleHistory(msg) {
  for (const item of msg.items) {
    if (!item || item.final !== true) {
      continue;
    }

    handleCaptionUpdate(item);
  }

  console.log(`Recovered ${msg.items.length} history item(s)`);
}


function scheduleReconnect() {
  if (reconnectTimer !== null) {
    return;
  }

  const exponentialDelay = Math.min(BASE_RECONNECT_MS * (2 ** reconnectAttempts),MAX_RECONNECT_MS);

  // Small random jitter prevents many clients
  // reconnecting at exactly the same moment.
  const delay = exponentialDelay * (0.8 + Math.random() * 0.4);

  reconnectAttempts += 1;

  statusEl.textContent = "reconnecting";

  reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connect();
  }, delay);
}


function connect() {
  statusEl.textContent = reconnectAttempts > 0 ? "reconnecting" : "connecting";

  const socket = new WebSocket(WS_URL);
  ws = socket;

  socket.addEventListener("open", () => {
    if (ws !== socket) return;

    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }

    reconnectAttempts = 0;

    statusEl.textContent = "connected";

    socket.send(JSON.stringify({
      type: "CLIENT_HELLO",
      client_id: numericClientId(),
      session: "L1",
      last_segment: lastFinalSegment,
      last_revision: lastFinalRevision,
      history_seconds: HISTORY_REQUEST_SECONDS
    }));
  });

  socket.addEventListener("message", (event) => {
    if (ws !== socket) return;

    const msg = JSON.parse(event.data);

    if (msg.type === "CAPTION_UPDATE") {
      handleCaptionUpdate(msg);
    } else if (msg.type === "HISTORY") {
      handleHistory(msg);
    }
  });

  socket.addEventListener("close", () => {
    if (ws !== socket) return;

    statusEl.textContent = "disconnected";

    scheduleReconnect();
  });

  socket.addEventListener("error", () => {
    if (ws !== socket) return;

    statusEl.textContent = "connection error";

    socket.close()
  });
}


for (const button of document.querySelectorAll("button[data-seconds]")) {
  button.addEventListener("click", () => {
    const seconds = Number(button.dataset.seconds);
    showRecall(seconds);
  });
}

connect();

setInterval(remove_old_entries, 3000);
