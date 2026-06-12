# CLAUDE.md – Výsledkový servis

Pokyny pro práci na tomhle projektu. **Plný kontext (architektura, build, gotchas)
je v [DEVELOPMENT.md](DEVELOPMENT.md) – přečti si ho dřív, než začneš.**

## Co to je
Flask appka (Python) zabalená do macOS `.app`. Stahuje XML z hasicovo.cz, parsuje
výsledky a servíruje overlay grafiku do OBS (chroma‑key/transparent). Ovládá se
z nativního okna i hardwarem (Elgato Stream Deck plugin, Bitfocus Companion modul)
přes HTTP `/control` + `/status`. Cílová platforma: **macOS, arm64**.

## Rychlý start
```bash
pip install -r requirements.txt
python3 AdvancedResultWriting.py     # dev v prohlížeči, port 5000 (nativní app: 5100)
# ovládání http://127.0.0.1:5000/  | overlay http://127.0.0.1:5000/overlay
./build_app.sh                        # sestaví .app + DMG do dist/
```

## Architektura v kostce (detail v DEVELOPMENT.md §4)
- `app_boot.py` = **tenký launcher** zapečený v `.app`. Mění se zřídka.
- `app_ui.py` = **veškeré nativní UI** (menu, okna, instalátory). Je v `CODE_ITEMS`
  → **aktualizuje se přes in‑app update bez nové `.app`.**
- `updater.py` = self‑update z GitHubu (`main.zip`). `CODE_ITEMS` = co se aktualizuje,
  `PRESERVE` = `config.json`.
- Hardware: `streamdeck/…sdPlugin/` (HTML/JS, bez buildu), `companion-modules/`
  (Node, `@companion-module/base` v2).

## Verzování a nasazení (pravidla – DEVELOPMENT.md §11)
- `VERSION` = zdroj pravdy, schéma **`RRRR.MM.DD[.N]`** (`.N` = víc vydání týž den).
  Bumpni při každém vydání.
- Tag = `v<VERSION>`, GitHub Release se stejným tagem, asset **vždy**
  `VysledkovyServis.dmg`.
- **Rozhodni před vydáním:**
  - Měnil jsi jen `CODE_ITEMS` (web, overlay, parsery, `app_ui.py`, SD plugin,
    Companion `.tgz`)? → **bump VERSION + push do `main`. DMG netřeba** (in‑app update).
  - Měnil jsi `app_boot.py` / `requirements.txt` / `icon.icns`? → **nutný nový DMG**
    (`./build_app.sh` + `gh release create`).

## Konvence a pravidla
- **Necommituj `config.json`** (runtime stav – poslední závod). Při stage to vynech.
- **Push/release jen na vyžádání.** Když na `main`, branchuj? – repo pracuje přímo
  na `main` (zdroj pro auto‑update), takže push na `main` je tu standard, ale dělej
  ho až po souhlasu uživatele.
- Commit messages česky, krátké a věcné (viz git historie).
- Po změně **Companion modulu**: bump `package.json` `version`, `npm run build`,
  zkopíruj nový `.tgz` do `companion-modules/vysledkovyservis.tgz`, commitni (DEVELOPMENT.md §9).
- **Stream Deck ikony jen PNG** (SVG se nevykreslí).
- Nedotýkej se `CFBundleExecutable` / ASCII jména binárky v `build_app.sh` (kvůli
  „appka je poškozená", DEVELOPMENT.md §11). Podpis inside‑out, **NE `--deep`**.

## Časté úkoly → kde
- Nový typ závodu/pohledu → parser + `parser.py` + `*Visible` flag + `overlay.html` `buildView()`.
- Stránkování / pozadí overlaye → `templates/overlay.html` (DEVELOPMENT.md §6).
- Menu / okna / instalátory → `app_ui.py` (jde přes in‑app update).
- Build/podpis → `build_app.sh` (DEVELOPMENT.md §11).

## Repozitáře
- **VysledkovyServis** (veřejný) = aktivní, sem se pushuje, odtud se appka aktualizuje.
- **HasiciVysledkovky** (privátní, archiv) = původní, **nepublikovat** (staré tokeny v historii).
