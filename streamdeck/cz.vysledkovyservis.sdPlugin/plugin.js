// Výsledkový servis – Stream Deck plugin (classic HTML/JS, no build step).
// Talks to the local Flask app over HTTP (/control, /status) and to Stream Deck over WebSocket.

const ACTION = "cz.vysledkovyservis";

// Map each action UUID to the command it sends and the label shown on the key.
// cmd is either a fixed query string, or a function(status) -> query string.
const ACTIONS = {
    [`${ACTION}.view.results`]:    { label: "Tabulka",   query: "view=results" },
    [`${ACTION}.view.racers`]:     { label: "Lišta",     query: "view=racers" },
    [`${ACTION}.view.total`]:      { label: "Celkové",   query: "view=total" },
    [`${ACTION}.broadcast.toggle`]:{ label: "",          query: (s) => s.is_running ? "action=stop" : "action=start" },
    [`${ACTION}.race.load`]:       { label: "",          query: (s, set) => `race=${encodeURIComponent(set.race || "")}&action=start` },
    [`${ACTION}.category.next`]:   { label: "Kategorie ▶", query: "category=next" },
    [`${ACTION}.category.prev`]:   { label: "◀ Kategorie", query: "category=prev" },
    [`${ACTION}.discipline.next`]: { label: "Disciplína ▶", query: "discipline=next" },
    [`${ACTION}.discipline.prev`]: { label: "◀ Disciplína", query: "discipline=prev" },
    [`${ACTION}.discipline.show`]: { label: "", query: "" },   // display-only: shows the current discipline
    [`${ACTION}.page.next`]:       { label: "Strana ▶", query: "page=next" },
    [`${ACTION}.page.prev`]:       { label: "◀ Strana", query: "page=prev" },
};

let ws = null;
let pluginUUID = null;
let host = "127.0.0.1:5100";              // overridable via global settings (Property Inspector)
const contexts = {};                       // context -> { action, settings }
let lastStatus = { ok: false, is_running: false, view: "none" };

function baseUrl() { return `http://${host}`; }

function send(obj) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); }

function setTitle(context, title) {
    send({ event: "setTitle", context, payload: { title: String(title), target: 0 } });
}
function setState(context, state) {
    send({ event: "setState", context, payload: { state } });
}
function showAlert(context) { send({ event: "showAlert", context }); }
function showOk(context) { send({ event: "showOk", context }); }

// ---- HTTP to the Flask app ----
async function callControl(query) {
    const res = await fetch(`${baseUrl()}/control?${query}`, { cache: "no-store" });
    return res.json();
}
async function fetchStatus() {
    const res = await fetch(`${baseUrl()}/status`, { cache: "no-store" });
    return res.json();
}

// ---- Render every visible key from the latest status ----
function renderAll() {
    const s = lastStatus;
    for (const [context, info] of Object.entries(contexts)) {
        const def = ACTIONS[info.action];
        if (!def) continue;

        if (info.action === `${ACTION}.view.results`) {
            setState(context, s.view === "results" ? 1 : 0);
            setTitle(context, "Tabulka");
        } else if (info.action === `${ACTION}.view.racers`) {
            setState(context, s.view === "racers" ? 1 : 0);
            setTitle(context, "Lišta");
        } else if (info.action === `${ACTION}.view.total`) {
            setState(context, s.view === "total" ? 1 : 0);
            setTitle(context, "Celkové");
        } else if (info.action === `${ACTION}.broadcast.toggle`) {
            setState(context, s.is_running ? 1 : 0);
            setTitle(context, s.is_running ? "● VYSÍLÁ" : "Spustit");
        } else if (info.action === `${ACTION}.race.load`) {
            setTitle(context, "Závod\n" + (info.settings.race || "—"));
        } else if (info.action === `${ACTION}.category.next`) {
            setTitle(context, def.label + "\n" + clip(cycle(s.categories, s.category, "next")));
        } else if (info.action === `${ACTION}.category.prev`) {
            setTitle(context, def.label + "\n" + clip(cycle(s.categories, s.category, "prev")));
        } else if (info.action === `${ACTION}.discipline.next`) {
            setTitle(context, def.label + "\n" + clip(cycle(s.disciplines, s.discipline, "next")));
        } else if (info.action === `${ACTION}.discipline.prev`) {
            setTitle(context, def.label + "\n" + clip(cycle(s.disciplines, s.discipline, "prev")));
        } else if (info.action === `${ACTION}.discipline.show`) {
            setTitle(context, s.discipline || "—");
        } else if (info.action === `${ACTION}.page.next`) {
            setTitle(context, def.label + "\n" + (parseInt(s.page || "1", 10) + 1));
        } else if (info.action === `${ACTION}.page.prev`) {
            setTitle(context, def.label + "\n" + Math.max(1, parseInt(s.page || "1", 10) - 1));
        } else {
            setTitle(context, def.label);
        }
    }
}

function clip(text) {
    if (!text) return "—";
    return text.length > 10 ? text.slice(0, 9) + "…" : text;
}

// Next/previous item in a list, wrapping around – mirrors the server's cycle_value.
// Used so the "next/prev" keys can preview the value they will switch TO.
function cycle(list, current, dir) {
    if (!Array.isArray(list) || !list.length) return current;
    let i = list.indexOf(current);
    if (i < 0) i = 0;
    i = (i + (dir === "next" ? 1 : -1) + list.length) % list.length;
    return list[i];
}

// Poll the app for live state so the keys reflect reality even when changed elsewhere.
async function pollLoop() {
    try {
        lastStatus = await fetchStatus();
    } catch (e) {
        lastStatus = { ok: false, is_running: false, view: "none" };
    }
    renderAll();
}
setInterval(pollLoop, 1200);

// ---- Stream Deck entry point ----
function connectElgatoStreamDeckSocket(inPort, inUUID, inRegisterEvent, inInfo) {
    pluginUUID = inUUID;
    ws = new WebSocket("ws://127.0.0.1:" + inPort);

    ws.onopen = () => {
        send({ event: inRegisterEvent, uuid: inUUID });
        send({ event: "getGlobalSettings", context: inUUID });
        pollLoop();
    };

    ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data);
        const { event, action, context } = msg;
        const payload = msg.payload || {};

        if (event === "didReceiveGlobalSettings") {
            if (payload.settings && payload.settings.host) host = payload.settings.host;
            return;
        }
        if (event === "willAppear") {
            contexts[context] = { action, settings: payload.settings || {} };
            renderAll();
            return;
        }
        if (event === "willDisappear") {
            delete contexts[context];
            return;
        }
        if (event === "didReceiveSettings") {
            if (contexts[context]) contexts[context].settings = payload.settings || {};
            renderAll();
            return;
        }
        if (event === "keyDown") {
            handleKeyDown(action, context, payload.settings || {});
            return;
        }
    };
}

async function handleKeyDown(action, context, settings) {
    const def = ACTIONS[action];
    if (!def) return;
    const query = typeof def.query === "function" ? def.query(lastStatus, settings) : def.query;
    try {
        lastStatus = await callControl(query);
        showOk(context);
        renderAll();
    } catch (e) {
        showAlert(context);   // app not running / wrong host:port
    }
}

window.connectElgatoStreamDeckSocket = connectElgatoStreamDeckSocket;
