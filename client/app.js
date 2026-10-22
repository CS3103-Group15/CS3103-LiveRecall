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

function handleCaptionUpdate(msg) {
  const existing = captions.get(msg.segment);
  if (existing) {
    if (existing.final) {
      return;
    }
    if (msg.revision <= existing.revision) {
      return;
    }
  }
  let row;
  if (existing) {
    row = existing.element;
  } else {
    row = document.createElement("div");
    liveEl.appendChild(row);
  }
  row.className = msg.final ? "caption final" : "caption provisional";
  row.textContent = msg.text;
  captions.set(msg.segment, {
    revision: msg.revision,
    final: msg.final,
    text: msg.text,
    source_ts: msg.source_ts,
    element: row
  });
  if (msg.final) {
    storeFinalCaption(msg);
  }
  // const shouldAutoScroll = liveEl.scrollHeight - liveEl.scrollTop - liveEl.clientHeight < 40;
  // if (shouldAutoScroll) {
  //   liveEl.scrollTop = liveEl.scrollHeight;
  // }
  liveEl.scrollTop = liveEl.scrollHeight;
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
        recallEl.textContent =
            `No finalized captions in the last ${seconds} seconds.`;
        return;
    }

    for (const caption of recent) {
        const row = document.createElement("div");
        row.className = "recall-caption";

        const timestamp = document.createElement("span");
        timestamp.className = "recall-time";

        timestamp.textContent =
            new Date(caption.source_ts * 1000)
                .toLocaleTimeString();

        const text = document.createElement("span");
        text.textContent = caption.text;

        row.append(timestamp, text);
        recallEl.appendChild(row);
    }
}

// function appendNaively(msg) {
//   const row = document.createElement("div");
//   row.className = "naive-line";
//   const state = msg.final ? "FINAL" : "PROVISIONAL";
//   row.textContent = `[${state}] segment ${msg.segment} rev ${msg.revision}: ${msg.text}`;
//   liveEl.appendChild(row);
//   liveEl.scrollTop = liveEl.scrollHeight;
// }

function connect() {
  statusEl.textContent = "connecting";
  ws = new WebSocket(WS_URL);

  ws.addEventListener("open", () => {
    statusEl.textContent = "connected";
    ws.send(JSON.stringify({
      type: "CLIENT_HELLO",
      client_id: numericClientId(),
      session: "L1",
      last_segment: 0,       // TODO: resume latest finalized state
      last_revision: 0,
      history_seconds: 30
    }));
  });

  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === "CAPTION_UPDATE") {
      handleCaptionUpdate(msg);
    } else if (msg.type === "HISTORY") {
      console.log(`HISTORY with ${msg.items?.length ?? 0} item(s)`, msg);
      // TODO: merge history without stale/duplicate final captions.
    }
  });

  ws.addEventListener("close", () => {
    statusEl.textContent = "disconnected";
    // TODO: automatic reconnect after a short delay, using finalized resume state.
  });

  ws.addEventListener("error", () => {
    statusEl.textContent = "connection error";
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
