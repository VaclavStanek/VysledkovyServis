# Vývojářská dokumentace – Výsledkový servis

Jak appka funguje uvnitř, jak se staví a vydává, a na co si dát pozor. Cílem je, aby
na to mohl navázat kdokoliv další. Aktuální verze v době psaní: **2026.06.11.3**.

> 🛠 **Udržuj tuhle dokumentaci aktuální.** Při každé netriviální změně (architektura,
> build/podpis, verzování, nový endpoint/pohled/parser, Stream Deck/Companion, známé
> problémy) **rovnou aktualizuj `DEVELOPMENT.md` i `CLAUDE.md`** ve stejném commitu.
> Zastaralá dokumentace je horší než žádná – nová session se podle ní řídí.

---

## 1. Co to je a jak to teče (big picture)

Flask aplikace v Pythonu zabalená do macOS `.app`. Každou ~1 s stáhne XML export
závodu z hasicovo.cz, naparsuje ho do jednotného dictu a ten servíruje overlay
grafice (browser source v OBS). Ovládá se z nativního okna; navíc jde ovládat
**hardwarem** (Elgato Stream Deck plugin nebo Bitfocus Companion modul) přes lokální
HTTP API.

```
hasicovo.cz (XML)
      │  requests.get (každou ~1 s, vlákno run_script)
      ▼
  parser.py → parsing_*.py        ← přeloží XML na "result" dict
      │
      ▼
  latest_data (globální proměnná v paměti)
      │  GET /data (JSON)            GET /control , /status  ◄── Stream Deck / Companion
      ▼
  templates/overlay.html          ← vykreslí tabulku/lištu (polling 300 ms)
      │  okno v OBS → chroma key / transparent
      ▼
     OBS
```

Dříve se `result` posílal do Singular Live; **Singular je pryč**, grafiku
vykreslujeme sami v `overlay.html`.

---

## 2. Mapa souborů

**Jádro appky (Flask):**
- `AdvancedResultWriting.py` – hlavní soubor: Flask routy, vlákno `run_script`
  (polling + parsing), workaround na koncové „a", stav (vybraný závod/kategorie/
  disciplína/pohled, `auto_paging`), `/control` + `/status` pro hardware.
- `parser.py` – rozcestník: podle `raceType`/`raceName` zavolá správný parser a
  vrátí seznam disciplín pro UI.
- `parsing_single.py` – jednotlivci (a TFA).
- `parsing_single_multidiscipline.py` – jednotlivci dorost (100 m př. + 100 m PHP).
- `parsing_ctif.py` / `parsing_plamen.py` / `parsing_dorost.py` – týmové závody.

**Frontend (Jinja šablony):**
- `templates/index.html` – ovládací UI (výběr závodu/kategorie/disciplíny/pohledu,
  vlastní dropdowny, ořez „a", přepínač auto‑stránkování, stažení klíčovacího pozadí).
- `templates/overlay.html` – grafika do OBS (vykreslení + stránkování + pozadí).
- `templates/companion.html` – návod krok za krokem na nastavení Companion modulu
  (otevírá se z menu appky, route `/companion`).

**Mac aplikace (obal):**
- `app_boot.py` – **tenký, stabilní launcher** = PyInstaller vstupní bod. Seed/update
  kódu, spuštění Flasku, pak předá řízení `app_ui.py`. Mění se zřídka (viz §4).
- `app_ui.py` – **aktualizovatelné nativní UI**: menu, okna, `Api` (pywebview),
  instalátory Stream Deck pluginu / Companion modulu, generátor klíčovacího PNG.
  Je v `CODE_ITEMS` → mění se přes in‑app update bez nové `.app`.
- `updater.py` – self‑update: stáhne ZIP z veřejného GitHubu (bez gitu) a přepíše
  kód v zapisovatelné složce; `latest_version()` čte vzdálenou `VERSION`.
- `build_app.sh` – sestaví `.app` (zabalený Python přes PyInstaller) a DMG + podpis.
- `icon.icns` – ikona appky (aktuálně **tyrkysová** s plamenem; jen v buildu, neupdatuje se).
  Přebarvení: `python3 tools/recolor_app_icon.py <stupně>` (rotace odstínu, plamen zůstává).
- `tools/` – pomocné skripty: `gen_streamdeck_icons.py` (PNG ikony pluginu),
  `recolor_app_icon.py` (přebarvení `icon.icns`).
- `VERSION` – textová verze (zobrazuje se v UI, hlásí ji updater).
- `requirements.txt` – závislosti (Flask, requests, xmltodict, pywebview).
- `VysledkovyServis.spec` – PyInstaller spec (v `.gitignore`; build jede přes
  `build_app.sh`, ne přes spec – spec je jen pro pohodlí/paritu).

**Hardware ovládání:**
- `streamdeck/cz.vysledkovyservis.sdPlugin/` – Elgato Stream Deck plugin (viz §8).
- `streamdeck/install.sh` – ruční instalace pluginu (appka má i tlačítko v menu).
- `companion-modules/vysledkovyservis/` – zdroj Bitfocus Companion modulu (viz §9).
- `companion-modules/vysledkovyservis.tgz` – **předsestavený** balíček modulu
  (commitnutý; zabaluje se do `.app` pro instalaci z menu).

**Runtime data:**
- `config.json` – poslední použité XML URL (`last_url`). Mění se za běhu;
  při aktualizaci se **zachovává** (`PRESERVE`, neupravuje ho updater). Necommitovat.

**Legacy / nepoužívané (lze ignorovat, dříve Docker server):**
- `Dockerfile`, `entrypoint.sh`, `hasici.xml`, `test.txt`.

---

## 3. Dva režimy běhu

**A) Vývoj v prohlížeči** – `python3 AdvancedResultWriting.py`
- Port `5000` (`HV_PORT`), `HV_DEBUG=1` zapne autoreload, `HV_HOST=0.0.0.0`
  vystaví na LAN. Ovládání i overlay otevřeš v prohlížeči.
- **Tady neexistuje nativní okno ani menu** (žádný pywebview) → menu Aktualizace/
  Stream Deck/Companion nejsou; stahování pozadí jede přes canvas fallback.
- Detekci režimu v `index.html` řeší kontrola `window.pywebview`.

**B) Nativní Mac aplikace** – `Výsledkový servis.app` (přes `app_boot.py`)
- Flask běží **na pozadí** na portu `5100`, GUI vlastní hlavní vlákno (macOS).
- Ovládání v nativním okně (pywebview/WKWebView). „Otevřít overlay" → druhé nativní
  okno přes `window.pywebview.api.open_overlay()`.
- Nativní menu: **Aktualizace**, **Stream Deck**, **Companion**.

---

## 4. Architektura nativní appky: launcher + app_ui + self‑update

Kód běží ze **zapisovatelné složky**, ne z vnitřku `.app` (ten je read‑only kvůli
Gatekeeperu/podpisu). Klíčové rozdělení (od verze 2026.06.11.2):

- **`app_boot.py` = tenký launcher** zapečený v `.app`. Je stabilní a mění se jen
  výjimečně. Při startu:
  1. **Seed** – při prvním spuštění zkopíruje kód z bundlu (`appsrc/`) do
     `~/Library/Application Support/VysledkovyServis/app/` (`updater.ensure_seeded`).
  2. **Auto‑update** – tiše (a **bezpodmínečně** při každém startu) stáhne nejnovější
     ZIP z GitHubu a přepíše `CODE_ITEMS` (kromě `PRESERVE`). Když selže (není net),
     pokračuje na stávající verzi.
  3. **Server** – spustí `AdvancedResultWriting.py` z code_dir (vlákno, port 5100).
  4. **UI** – `run_ui()` načte `app_ui.py` **z code_dir** přes `importlib` a zavolá
     `app_ui.run(URL, PORT, bundled_src, code_dir)`.

- **`app_ui.py` = veškeré nativní UI** (menu, okna, `Api`, instalátory). Je v
  `CODE_ITEMS`, takže se **aktualizuje přes in‑app update**: změníš menu/okno →
  uživatel ho dostane po restartu appky, **bez nové `.app`**.

- **Pojistka proti „zacihlení":** když updatovaný `app_ui.py` selže při načtení,
  `run_ui()` spadne zpět na kopii `app_ui.py` **zabalenou v bundlu** (`bundled_src`).
  Rozbitý update tedy appku nezasekne.

**Co se aktualizuje JAK:**

| Změna | Doručení |
|-------|----------|
| Web panel, overlay, parsery (`templates/`, `parsing_*`, `AdvancedResultWriting.py`) | ✅ in‑app update |
| Nativní menu/okna/instalátory (`app_ui.py`) | ✅ in‑app update |
| Soubory Stream Deck pluginu (`streamdeck/`) | ✅ in‑app update (+ reinstal do SD z menu) |
| Companion modul (`companion-modules/vysledkovyservis.tgz`) | ✅ in‑app update (+ re‑import v Companionu) |
| **Launcher `app_boot.py`** | ❌ nová `.app` |
| **Nová Python knihovna** (závislost) | ❌ nová `.app` |
| **Ikona `icon.icns`** | ❌ nová `.app` |

> `app_ui.py` smí používat **jen knihovny už zabalené v `.app`** (pywebview + stdlib).
> Přidat novou závislost nebo měnit launcher = nový build. `updater` je efektivně
> „připnutý" na bundlovou verzi (importuje ho launcher i app_ui) – mění se zřídka,
> nová API v updateru pak chtějí nový build.

**`updater.py` detaily:**
- Stahuje `…/VysledkovyServis/archive/refs/heads/main.zip` přes **requests**
  (NE urllib – python.org urllib selhává na TLS „CERTIFICATE_VERIFY_FAILED"; requests
  používá certifi).
- `CODE_ITEMS` – seznam seedovaných/aktualizovaných položek: `AdvancedResultWriting.py`,
  `app_ui.py`, všechny `parsing_*`, `parser.py`, `updater.py`, `requirements.txt`,
  `VERSION`, `templates`, `streamdeck`, `companion-modules`.
- `PRESERVE = {config.json}` – uživatelská data, nepřepisovat.
- `latest_version()` – stáhne jen `raw.githubusercontent.com/.../main/VERSION` a porovná
  s lokální → menu „Zkontrolovat aktualizace" buď řekne „máš aktuální verzi", nebo
  nabídne tlačítko ke stažení nové (přes `window.confirm`).

---

## 5. Struktura "result" dictu (parser → overlay)

Každý `parsing_*.py` vrací dict se dvěma druhy klíčů:

**Viditelnost pohledu** (overlay podle nich vybere, co kreslit):
`racersResultTableVisible`, `racersListVisible`, `singlesMultieventListVisible`,
`singlesMultieventTotalTableVisible`, `CTIFListVisible`, `CTIFResultTableVisible`,
`plamenListVisible`, `plamenResultTableVisible`, `totalResultsTableVisible`,
`dorostTableVisible`, `dorostListVisible`, `dorostTotalResultsTableVisible`,
`TFAListVisible`, `TFATableVisible`, `penaltyPointsDiscipline` aj.

**Obsah tabulek** (JSON string `{"content": [...]}`):
- `tableContentVysledky` – řádky výsledkové/celkové tabulky (**všechny**, viz §6).
- `tableContentAktualniZavodnici` – aktuálně běžící (lišta závodníků).

Plus metadata: `raceName`, `racePlace`, `category`, `categoryCustom`, `selected_event`.
A **stránkování** (injektuje `publish_current` v `AdvancedResultWriting.py`):
`autoPaging` (bool) a `selectedPage` (int).

> **Přidání nového typu závodu / pohledu:** napiš parser, zaregistruj ho v
> `parser.py` + `determine_event_list`, nastav příslušné `*Visible` flagy a v
> `overlay.html` přidej větev ve `buildView()` se sloupci.

---

## 6. Overlay (templates/overlay.html) + model stránkování

- Pulluje `/data` každých **300 ms** (POLL_MS), z **Web Workeru** (OBS jinak škrtí
  `setInterval` na 1×/s). Překresluje jen při změně dat (signature = raw JSON).
- `buildView(d)` podle `*Visible` flagů vybere typ pohledu a sloupce.
- **Pozadí:** výchozí chroma‑key zelená `#00b140`; `?transparent=1` (OBS browser
  source) nebo `?bg=RRGGBB`. Medaile (zlatá/stříbrná/bronz) pro pořadí 1–3.

**Model stránkování (důležité, sjednoceno 2026.06.11.1):**
- **Server posílá VŠECHNY řádky** kategorie. Dřívější krájení po 20 v
  `parsing_single*` bylo odstraněno – stránkuje výhradně overlay.
- Overlay dělí na stránky po `PAGE_SIZE = 10`.
- `auto_paging` (server global, default zapnuto, přepíná se v panelu):
  - **zapnuto** → overlay automaticky rotuje stránky po `PAGE_MS` (default 8 s,
    `?pagesec=N`).
  - **vypnuto** → rotace stojí; zobrazená stránka = `selectedPage` (řízeno polem
    „Stránka" v panelu nebo Stream Deck/Companion tlačítky „strana"). V overlayi
    `manualPage`/`autoPaging` přicházejí z `/data`.
- Hlavička je ukotvená nahoře; při stránkování se nehýbe (režimy `full`/`rows-only`/
  `no-anim`), animují se jen řádky.
- **Lišta závodníků** (lower third) ukazuje v hlavičce **kategorii a disciplínu**
  („kategorie — disciplína"), ne název závodu (změna 2026.06.11.3).

---

## 7. Ovládací panel (templates/index.html)

- Výběr závodu přes modal (`/race_info` náhled → `/start_race` spustí vysílání).
- Live změny jdou přes `/apply_settings` (AJAX, bez reloadu) – vlákno čte globály
  každou smyčku, takže není potřeba restart.
- Výběr kategorie/disciplíny (vlastní dropdowny), výběr pohledu (segmentované dlaždice,
  single‑select), stránka tabulky + **přepínač „Automaticky přepínat stránky"**
  (`auto_paging`).
- **Oprava názvů** – `strip_mode` (auto/on/off), viz §10.
- **Pozadí pro klíčování** – stáhne jednolitou klíčovací barvu jako PNG. V nativní
  appce přes `window.pywebview.api.save_background` (WKWebView neumí `<a download>`
  z blobu) → uloží Python (`app_ui._solid_png`, vlastní PNG enkodér ze stdlib, žádný
  Pillow). V prohlížeči fallback přes canvas.
- „Odkaz do OBS" zkopíruje `…/overlay?transparent=1`.

---

## 8. Stream Deck plugin (streamdeck/)

Ovládání overlaye z Elgato Stream Decku. Plugin (classic HTML/JS, **bez buildu**)
mluví s appkou přes HTTP `/control` (akce) a `/status` (zpětná vazba ~1,2 s) a se
Stream Deckem přes WebSocket.

- **Akce:** pohledy (výsledky/lišta/celkové), kategorie/disciplína/strana další/
  předchozí, spustit/zastavit vysílání, načíst závod podle čísla, „Aktuální disciplína"
  (jen zobrazení). Tlačítka „další/předchozí" **ukazují hodnotu, na kterou přepnou**
  (helper `cycle()` ze seznamů ve `/status`).
- **Stav na tlačítkách:** aktivní pohled = červené, běžící vysílání = „● VYSÍLÁ".
- **Adresa appky** (`host:port`, default `127.0.0.1:5100`) se nastavuje v Property
  Inspectoru (globální pro všechna tlačítka). CORS řeší `@app.after_request` v Flasku.
- **Ikony MUSÍ být PNG** (`icons/*.png` + `@2x`). **SVG se ve Stream Decku
  nevykresluje.** Regeneruj přes **`python3 tools/gen_streamdeck_icons.py`** (jednolité
  dlaždice: šedá idle / červená active / zelená start + „VS").
- **Instalace:** appka má menu **Stream Deck → Nainstalovat plugin** (zkopíruje
  složku do `~/Library/Application Support/com.elgato.StreamDeck/Plugins/` a restartuje
  Stream Deck). Ručně: `streamdeck/install.sh`. Po in‑app updatu appky je potřeba
  plugin do SD **znovu nainstalovat z menu** (update jen stáhne soubory do code_dir).

---

## 9. Bitfocus Companion modul (companion-modules/)

> ⚠️ **KNOWN ISSUE:** Companion modul zatím **nefunguje** – naimportuje se, ale
> v Companionu 4.x se nepřipojí / nechová správně, i po opravě init crashe
> (`setPresetDefinitions`) ve verzi modulu 1.0.1. Příčina nepotvrzena. Netvrdit, že
> funguje, dokud to není ověřené naživo. Stream Deck cesta (§8) funguje. Viz §13/§14.

Nativní modul pro **Bitfocus Companion 4.x** (`@companion-module/base` **v2**).
Ovládá overlay přes stejné HTTP API (`/control`, `/status`).

- **Akce / feedback / proměnné:** přepínání pohledů/kategorie/disciplíny/strany,
  start/stop/toggle vysílání, načíst závod; feedback „aktivní pohled" (červená) a
  „vysílá" (zelená); proměnné `$(vysledkovyservis:category|discipline|page|…_next|…_prev)`.
- **Config pole `host`** (`127.0.0.1:5100`) v `getConfigFields()`. Polling `/status` 1 s.

**Gotchas base v2 (Companion 4.x) – jinak se modul nenačte / nepřipojí:**
- **Žádný `runEntrypoint`** (byl v v1). Modul `export default` třídu – host si
  instanci vytvoří sám.
- `companion/manifest.json` musí mít root **`"type": "connection"`** a
  `runtime.type: "node22"`, `api: "nodejs-ipc"`. `apiVersion`/`entrypoint`/`version`
  **dosadí build** podle nainstalované base (manuálně neřešit).
- **`setPresetDefinitions` má v base v2 DVA argumenty** `(structure, presets)`.
  Volání s jedním shodí `init()` → červený vykřičník a nejde zadat IP/port.
  *(Aktuálně presety vyhozené – akce/feedback/proměnné stačí; doplnit lze později
  ve správném formátu.)*
- Build: `npm install && npm run build` (`@companion-module/tools`,
  `companion-module-build`) → `pkg/` + `vysledkovyservis-<verze>.tgz`.

**Instalace pro uživatele (Companion nemá auto‑load složku jako Stream Deck):**
- Appka veze předsestavený `.tgz`. Menu **Companion → Připravit modul** ho uloží
  (a odhalí ve Finderu), **Návod k nastavení** otevře `/companion`.
- V Companionu: *Connections → + Add → Import custom module* → vybrat `.tgz` →
  přidat připojení a zadat adresu.

**Při změně modulu:** uprav `companion-modules/vysledkovyservis/main.js`, **bumpni
`package.json` `version`**, `npm run build`, zkopíruj nový `.tgz` do
`companion-modules/vysledkovyservis.tgz` (commitnout), pak commit/push (in‑app update
ho doručí). `node_modules/`, `pkg/`, `*.tgz` uvnitř modulu jsou gitignored.

---

## 10. Workaround na koncové „a" v názvech

hasicovo.cz občas přidá na konec **všech** názvů týmů písmeno „a" (`Velenkaa` místo
`Velenka`). Řeší to `AdvancedResultWriting.py`:
- `all_names_end_with_a()` – detekce (true jen když na „a" končí úplně všechny názvy).
- `strip_trailing_a_from_result()` – ořízne koncové „a" jen z pole `name`.
- `strip_mode`: `auto` (default) / `on` / `off`, volitelný v UI (sekce „Oprava názvů").

---

## 11. Build & release

### Verzování (pravidla)
- **`VERSION`** = jediný zdroj pravdy. Schéma **`RRRR.MM.DD`** + volitelně `.N` pro
  víc vydání týž den (`2026.06.11`, `2026.06.11.1`, `2026.06.11.2`, …). Bumpni při
  **každém** vydání, které má jít k uživatelům přes update‑check.
- **Git tag** = `v<VERSION>` (např. `v2026.06.11.3`). **GitHub Release** používá
  stejný tag, asset **vždy** `VysledkovyServis.dmg`.
- `updater.latest_version()` porovná `VERSION` z `main` s lokální → menu
  „Zkontrolovat aktualizace" podle toho hlásí „máš aktuální verzi" nebo nabídne update.
- Auto‑update na startu appky stahuje `main` **bezpodmínečně** (i bez bumpu) – bump
  je hlavně pro viditelnost v update‑checku a pro Release.

### Rozhodovací strom: stačí push, nebo musím nový DMG?
- Měnil jsi **JEN** soubory v `CODE_ITEMS` (web panel, overlay, parsery,
  `app_ui.py`, Stream Deck plugin, Companion `.tgz`, `updater.py`)?
  → **bump `VERSION` + `git push` do `main`.** Hotovo, **DMG netřeba** – doručí se
  in‑app updatem (po restartu appky). Volitelně vydej i Release pro čistou instalaci.
- Měnil jsi **`app_boot.py`** (launcher), **`requirements.txt`** (nová závislost)
  nebo **`icon.icns`**? → **MUSÍŠ zbuildit a vydat nový DMG** (jinak se změna
  k uživatelům nedostane – tyhle věci nejsou v `CODE_ITEMS`).

### Postup vydání (checklist)
1. Otestuj (`python3 AdvancedResultWriting.py`).
2. Bumpni `VERSION`.
3. `git add … && git commit && git push origin main`.
4. Potřebuješ nový DMG (viz strom výše)? → `./build_app.sh`.
5. `gh release create v$(cat VERSION) "dist/VysledkovyServis.dmg" --target main --title "v$(cat VERSION)" --notes "…"`.
6. Ověř: `gh release list` (nová = Latest), `codesign --verify --strict "dist/Výsledkový servis.app"`.

---

**Běžná oprava kódu / UI / pluginu / modulu** (vše v `CODE_ITEMS`):
1. Uprav, otestuj (`python3 AdvancedResultWriting.py`).
2. Bumpni `VERSION` (ať update‑check ukáže novou verzi).
3. `git push` do `main`. Uživatelé dostanou změnu při příštím startu appky
   (auto‑update) nebo přes menu Aktualizace. **DMG se stavět nemusí.**

**Změna obalu** (`app_boot.py` launcher, závislosti, ikona):
1. `./build_app.sh` → `dist/Výsledkový servis.app` + `dist/VysledkovyServis.dmg`.
2. Vydej DMG přes GitHub Releases (asset **musí** být `VysledkovyServis.dmg`):
   ```bash
   gh release create v$(cat VERSION) "dist/VysledkovyServis.dmg" \
       --target main --title "v$(cat VERSION)" --notes "Popis změn"
   ```

**Co build dělá (`build_app.sh`) – a proč:**
- `--add-data` zabaluje do `appsrc/`: hlavní Python + `app_ui.py` + parsery +
  `templates` + `streamdeck/...sdPlugin` + `companion-modules/vysledkovyservis.tgz`
  + `updater.py` + `VERSION`. `--collect-all webview`.
- **Podpis (ad‑hoc, inside‑out):** binárka se jmenuje **ASCII** `VysledkovyServis`
  (NE „Výsledkový servis"). Důvod: diakritika v `CFBundleExecutable` → Unicode
  normalizace NFD(disk) vs NFC(Info.plist) → codesign zapečetí hlavní binárku jako
  resource → kruhová cdhash závislost → Gatekeeper hlásí **„appka je poškozená"**.
  ASCII jméno to odstraní; hezký název pro UI se vrátí přes `CFBundleDisplayName` +
  přejmenování bundlu.
- Podepisuje se **inside‑out**: nejdřív `*.dylib`/`*.so`, pak frameworky (konkrétní
  verze, pak celý framework), nakonec vnější bundle. Před podpisem `xattr -cr`.
  **`codesign --verify --strict` musí projít** (build TVRDĚ spadne, jinak by vznikl
  „poškozený" bundle). **NE `--deep`** (na novějším macOS padá SIGBUSem).
- Build vyžaduje `PY=/usr/local/bin/python3` (python.org 3.11 universal2). Aktuálně
  **arm64**; pro Intel zkus `--target-arch universal2`.

> Appka **není notarizovaná** → DMG poslané jinému uživateli se napoprvé zablokuje
> (pravý klik → Otevřít, nebo „Otevřít přesto"). Čisté řešení = Apple Developer ID
> ($99/rok) + notarizace.

---

## 12. Repozitáře

- **VysledkovyServis** (veřejný) – aktivní, zdroj pravdy; sem se pushuje a odtud se
  appka aktualizuje. ZIP: `…/archive/refs/heads/main.zip`. Verze přes GitHub Releases
  (tag `v<VERSION>`, asset `VysledkovyServis.dmg`).
- **HasiciVysledkovky** (privátní, archivovaný) – původní repo. Zůstává privátní,
  protože git historie obsahuje staré Singular tokeny. **Nepublikovat.**

---

## 13. Známé věci / na co pozor

- ⚠️ **KNOWN ISSUE – Companion modul nefunguje:** v Companionu 4.x se modul
  naimportuje, ale **nepřipojí / nechová správně**, i po opravě init crashe (v1.0.1).
  Příčina nepotvrzena, k dořešení (§9, §14). **Stream Deck funguje.**
- **Gatekeeper:** appka není notarizovaná → první spuštění chce „Otevřít přesto".
- **`codesign --deep`** padá SIGBUSem – podepisovat inside‑out bez něj (viz §11).
- **ASCII jméno binárky** je nutné kvůli „appka je poškozená" (viz §11).
- **urllib + TLS** na python.org Pythonu selhává – updater i app používají `requests`
  (certifi).
- **Nativní změny vyžadují nový build** jen u `app_boot.py`, nové závislosti a ikony;
  zbytek (vč. menu v `app_ui.py`) jde přes in‑app update (viz §4).
- **Stream Deck ikony jen PNG** (SVG se nevykreslí).
- **Companion = base v2** (žádný `runEntrypoint`, `type:connection`, `node22`,
  `setPresetDefinitions` 2 argumenty) – viz §9.
- **Předsestavený Companion `.tgz`** je build artefakt v gitu – nezapomenout ho
  přebuildit + commitnout při změně modulu (viz §9).
- **Internet:** appka potřebuje net kvůli XML (a CDN fontům/Bootstrapu). Overlay
  renderuje lokálně → krátký výpadek nezhasne grafiku (drží poslední data).
- **`config.json`** je runtime stav (poslední závod) – necommitovat.

---

## 14. Roadmap

- ⚠️ **Vyřešit nefunkční Companion modul** (§9, §13) – ověřit naživo v Companionu 4.x,
  najít příčinu (entry/`.default`, config, lifecycle) a opravit.
- Podpis Developer ID + notarizace (odstranění Gatekeeper kroku).
- Universal2 build (Intel + Apple Silicon).
- Companion presety ve správném base‑v2 formátu (`structure` + `presets`).
- „Je k dispozici novější verze" i pro web panel (teď jen v nativním menu).
- Úklid legacy souborů (`Dockerfile`, `entrypoint.sh`, `hasici.xml`, `test.txt`).
- Drobné: konfigurace `pagesec`/počtu řádků v UI.
