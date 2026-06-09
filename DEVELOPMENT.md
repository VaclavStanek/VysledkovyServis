# Vývojářská dokumentace – Výsledkový servis

Tento dokument popisuje, jak appka funguje uvnitř, jak se staví a vydává, a na co
si dát pozor. Cílem je, aby na to mohl navázat kdokoliv (i jiný programátor).

---

## 1. Co to je a jak to teče (big picture)

Flask aplikace v Pythonu. Každou sekundu stáhne XML export závodu z hasicovo.cz,
naparsuje ho do jednotného dictu a ten servíruje overlay grafice.

```
hasicovo.cz (XML)
      │  requests.get (každou 1 s, vlákno run_script)
      ▼
  parser.py → parsing_*.py        ← přeloží XML na "result" dict
      │
      ▼
  latest_data (globální proměnná v paměti)
      │  GET /data (JSON)
      ▼
  templates/overlay.html          ← vykreslí tabulku/lištu (polling 800 ms)
      │  okno v OBS → chroma key
      ▼
     OBS
```

Dříve se `result` posílal do Singular Live; **Singular je pryč**, grafiku
vykreslujeme sami v `overlay.html`.

---

## 2. Mapa souborů

**Jádro appky (Flask):**
- `AdvancedResultWriting.py` – hlavní soubor: Flask routy, vlákno `run_script`
  (polling + parsing), workaround na koncové „a", konfigurace závodu.
- `parser.py` – rozcestník: podle typu závodu (`raceType`/`raceName`) zavolá
  správný parser a vrátí seznam disciplín pro UI.
- `parsing_single.py` – jednotlivci (a TFA).
- `parsing_single_multidiscipline.py` – jednotlivci dorost (100 m př. + 100 m PHP).
- `parsing_ctif.py` – CTIF týmy.
- `parsing_plamen.py` – Plamen týmy.
- `parsing_dorost.py` – Dorost týmy.

**Frontend (Jinja šablony):**
- `templates/index.html` – ovládací UI (výběr závodu/kategorie/disciplíny/pohledu,
  vlastní dropdowny, výběr ořezu „a").
- `templates/overlay.html` – samotná grafika do OBS (vykreslení + stránkování + pozadí).

**Mac aplikace (obal):**
- `app_boot.py` – vstupní bod pro PyInstaller. Připraví/aktualizuje kód, spustí
  Flask na pozadí a zobrazí ovládání v **nativním okně** (pywebview/WKWebView).
- `updater.py` – self‑update: stáhne ZIP z veřejného GitHubu (bez gitu) a přepíše
  kód v zapisovatelné složce.
- `build_app.sh` – sestaví `.app` (zabalený Python přes PyInstaller) a DMG.
- `icon.icns` – ikona appky.
- `VERSION` – textová verze (zobrazuje se v UI, hlásí ji updater).
- `requirements.txt` – závislosti (Flask, requests, xmltodict, pywebview).

**Runtime data:**
- `config.json` – poslední použité XML URL (`last_url`). Mění se za běhu;
  při aktualizaci se **zachovává** (není přepisován updaterem).

**Legacy / nepoužívané (lze ignorovat, dříve Docker server):**
- `Dockerfile`, `entrypoint.sh` – staré nasazení na cloud server (už se nepoužívá).
- `hasici.xml`, `test.txt` – ukázková data.

---

## 3. Dva režimy běhu

**A) Vývoj v prohlížeči** – `python3 AdvancedResultWriting.py`
- Běží na portu `5000` (`HV_PORT`), `HV_DEBUG=1` zapne autoreload.
- Ovládání i overlay otevřeš v prohlížeči. Tlačítko „Otevřít overlay" zde dělá
  `window.open` popup (fallback, protože není nativní okno).

**B) Nativní Mac aplikace** – `Výsledkový servis.app` (přes `app_boot.py`)
- Flask běží **na pozadí** na portu `5100`, GUI vlastní hlavní vlákno (požadavek macOS).
- Ovládání se zobrazí v nativním okně (pywebview). „Otevřít overlay" zavolá
  `window.pywebview.api.open_overlay()` → druhé nativní okno s overlayem.
- Aktualizace je v nativním menu **Aktualizace → Zkontrolovat aktualizace**.

Detekci režimu v `index.html` řeší kontrola `window.pywebview`.

---

## 4. Jak funguje nativní app a self‑update

Kód běží ze **zapisovatelné složky**, ne z vnitřku `.app` (ten je read‑only kvůli
Gatekeeperu). Tok při startu (`app_boot.py`):

1. **Seed** – při prvním spuštění zkopíruje kód z bundlu (`appsrc/`) do
   `~/Library/Application Support/VysledkovyServis/app/`.
2. **Auto‑update** – tiše stáhne nejnovější ZIP z GitHubu a přepíše kód (kromě
   `config.json`). Když selže (není net), pokračuje na stávající verzi.
3. **Server** – spustí `AdvancedResultWriting.py` z té složky (vlákno, port 5100).
4. **Okno** – zobrazí ovládání v pywebview okně.

`updater.py`:
- Stahuje `…/VysledkovyServis/archive/refs/heads/main.zip` přes **requests**
  (NE urllib – python.org urllib selhává na TLS „CERTIFICATE_VERIFY_FAILED";
  requests používá certifi).
- `CODE_ITEMS` = soubory, které se seedují/aktualizují. `PRESERVE` = `config.json`
  (uživatelská data, nepřepisovat).
- `app_boot.py` **není** v `CODE_ITEMS` → změny v něm vyžadují nový build a DMG.

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
- `tableContentVysledky` – řádky výsledkové/celkové tabulky.
- `tableContentAktualniZavodnici` – aktuálně běžící (lišta závodníků).

Plus metadata: `raceName`, `racePlace`, `category`, `selected_event`, …

Řádky obsahují např. `name`, `SDH`, `selectedEventOrder`/`order`/`totalOrder`,
`attempt1_…`, `selectedEventBestPoints`, `isRunning`, `backgroundColor` apod.
Pole se liší podle typu závodu – viz konkrétní `parsing_*.py`.

> **Přidání nového typu závodu / pohledu:** napiš parser, zaregistruj ho v
> `parser.py`, nastav příslušné `*Visible` flagy a v `overlay.html` přidej větev
> ve `buildView()` se sloupci.

---

## 6. Overlay (templates/overlay.html)

- Pulluje `/data` každých 800 ms; překresluje jen při změně dat.
- `buildView(d)` podle `*Visible` flagů vybere typ pohledu a sloupce.
- **Stránkování:** max 10 řádků na stránku, automatické přepínání po 8 s
  (`?pagesec=N`). Hlavička je ukotvená nahoře a při stránkování se nehýbe;
  animují se jen řádky (režimy `full`/`rows-only`/`no-anim`).
- **Pozadí:** výchozí chroma‑key zelená `#00b140`; `?transparent=1` (OBS browser
  source) nebo `?bg=RRGGBB`.
- Medaile (zlatá/stříbrná/bronz) pro pořadí 1–3.

---

## 7. Workaround na koncové „a" v názvech

hasicovo.cz občas přidá na konec **všech** názvů týmů písmeno „a"
(`Velenkaa` místo `Velenka`). Řeší to v `AdvancedResultWriting.py`:
- `all_names_end_with_a(race_data)` – detekce (true jen když na „a" končí
  úplně všechny názvy).
- `strip_trailing_a_from_result(result)` – ořízne koncové „a" jen z pole `name`.
- Režim `strip_mode`: `auto` (default, ořízne jen při detekci) / `on` / `off`,
  volitelný v UI (sekce „Oprava názvů").

---

## 8. Build & release (jak vydat opravu)

**Běžná oprava kódu** (Python/HTML/parsery):
1. Uprav kód, otestuj `python3 AdvancedResultWriting.py`.
2. `git push` do `main` repa **VysledkovyServis**.
3. Operátoři dostanou novou verzi automaticky při příštím startu appky
   (nebo přes menu Aktualizace). **DMG se znovu stavět nemusí.**
4. Doporučeno: bumpni `VERSION` (ať je vidět, že update proběhl).

**Změna obalu** (`app_boot.py`, závislosti, balení, ikona):
1. `./build_app.sh` → vznikne `dist/Výsledkový servis.app` a `dist/VysledkovyServis.dmg`.
2. Appka se podepisuje **ad‑hoc bez `--deep`** (`--deep` na macOS 26 padá SIGBUSem).
3. **Vydej nové DMG přes GitHub Releases** (odtud si ho uživatelé stahují – viz
   návod v README):
   ```bash
   gh release create v$(cat VERSION) "dist/VysledkovyServis.dmg" \
       --title "v$(cat VERSION)" --notes "Popis změn"
   # nová verze stejného tagu: gh release upload v$(cat VERSION) dist/VysledkovyServis.dmg --clobber
   ```
   Asset **musí** zůstat pojmenovaný `VysledkovyServis.dmg` (návod v README na něj odkazuje).
   Auto‑update kódu funguje dál i bez nového DMG – nové DMG je potřeba jen při změně obalu.

Build vyžaduje Python s knihovnami (`/usr/local/bin/python3`, python.org 3.11
universal2). Build je teď **arm64**; pro Intel zkus `--target-arch universal2`.

---

## 9. Repozitáře

- **VysledkovyServis** (veřejný) – aktivní, zdroj pravdy, sem se pushuje a odtud
  se appka aktualizuje. ZIP: `…/archive/refs/heads/main.zip`.
- **HasiciVysledkovky** (privátní, archivovaný) – původní repo. Zůstává privátní,
  protože jeho git historie obsahuje staré Singular tokeny. Nepublikovat.

---

## 10. Známé věci / na co pozor

- **Gatekeeper (macOS 26):** appka není notarizovaná → DMG poslané jinému uživateli
  se napoprvé zablokuje (pravý klik → Otevřít). Čisté řešení = Apple Developer ID
  ($99/rok) + notarizace.
- **`codesign --deep`** na macOS 26 padá SIGBUSem – podepisovat bez něj.
- **urllib + TLS** na python.org Pythonu selhává (chybí CA) – proto updater i app
  používají `requests` (certifi).
- **Internet:** appka potřebuje net kvůli XML (a CDN fontům/Bootstrapu). Overlay
  ale renderuje lokálně, takže krátký výpadek nezhasne grafiku (drží poslední data).
- **Architektura buildu** je arm64; na Intel Macu zatím nepoběží (viz §8).

---

## 11. Možné další kroky (roadmap)

- Podpis Developer ID + notarizace (odstranění Gatekeeper kroku).
- Universal2 build (Intel + Apple Silicon).
- Verzování přes git tagy + zobrazení „je k dispozici novější verze".
- Úklid legacy souborů (`Dockerfile`, `entrypoint.sh`, `hasici.xml`, `test.txt`).
- Drobné: konfigurace `pagesec`/počtu řádků v UI.
