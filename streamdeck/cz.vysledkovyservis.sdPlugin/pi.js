// Property Inspector for the Výsledkový servis plugin.
// - host:port is stored as GLOBAL settings (shared by all buttons)
// - race number is stored per-button (only for the "Načíst a spustit závod" action)

let ws = null;
let piUUID = null;
let actionInfo = null;

const hostInput = document.getElementById("host");
const raceInput = document.getElementById("race");
const raceItem = document.getElementById("raceItem");

function send(obj) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); }

function saveGlobal() {
    send({ event: "setGlobalSettings", context: piUUID, payload: { host: hostInput.value.trim() || "127.0.0.1:5100" } });
}
function saveSettings() {
    const settings = (actionInfo && actionInfo.payload && actionInfo.payload.settings) || {};
    settings.race = raceInput.value.trim();
    send({ event: "setSettings", context: piUUID, payload: settings });
}

hostInput.addEventListener("change", saveGlobal);
raceInput.addEventListener("change", saveSettings);

function connectElgatoStreamDeckSocket(inPort, inUUID, inRegisterEvent, inInfo, inActionInfo) {
    piUUID = inUUID;
    actionInfo = JSON.parse(inActionInfo);

    // Show the race-number field only for the race.load action
    if (actionInfo.action === "cz.vysledkovyservis.race.load") {
        raceItem.style.display = "block";
        const s = (actionInfo.payload && actionInfo.payload.settings) || {};
        raceInput.value = s.race || "";
    }

    ws = new WebSocket("ws://127.0.0.1:" + inPort);
    ws.onopen = () => {
        send({ event: inRegisterEvent, uuid: inUUID });
        send({ event: "getGlobalSettings", context: inUUID });
    };
    ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data);
        if (msg.event === "didReceiveGlobalSettings") {
            const g = (msg.payload && msg.payload.settings) || {};
            hostInput.value = g.host || "127.0.0.1:5100";
        }
    };
}

window.connectElgatoStreamDeckSocket = connectElgatoStreamDeckSocket;
