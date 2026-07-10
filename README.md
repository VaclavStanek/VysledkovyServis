# Výsledkový servis 🚒

Výsledkový **overlay pro OBS** pro hasičské soutěže. Stahuje XML z
[hasicovo.cz](https://pozarnisport.hasicovo.cz), parsuje výsledky a zobrazuje je
jako broadcast grafiku, kterou promítneš do OBS.

Nahrazuje dřívější řešení přes Singular Live – vše teď běží **lokálně** jako
samostatná Mac aplikace (nativní okno, žádný prohlížeč ani cloud).

Podporované typy závodů: jednotlivci, jednotlivci‑víceboj (dorost), CTIF, Plamen,
Dorost (týmy), TFA.

> 📖 Vývoj, architektura a build/release: viz **[DEVELOPMENT.md](DEVELOPMENT.md)**.

---

## 📥 Stažení a instalace (macOS)

1. Otevři **[stránku Releases](https://github.com/VaclavStanek/VysledkovyServis/releases/latest)**.
2. V sekci **Assets** stáhni soubor **`VysledkovyServis.dmg`**.
3. Otevři stažené DMG a **přetáhni „Výsledkový servis"** do složky **Aplikace**.
4. **První spuštění** (jednorázově): aplikace není notarizovaná Applem, takže ji macOS
   napoprvé zablokuje. Postup:
   - Otevři appku dvojklikem. Objeví se dialog *„Apple se nepodařilo ověřit, že soubor
     Výsledkový servis neobsahuje malware…"*. **Klikni na „Hotovo"** (v žádném případě
     ne na „Přesunout do koše"!).
   - Otevři **Nastavení systému → Soukromí a zabezpečení**, sjeď úplně dolů. Uvidíš řádek
     *„Výsledkový servis byl zablokován…"* a vedle tlačítko **„Přesto otevřít"** – klikni.
   - Zadej heslo / Touch ID a v posledním dialogu klikni ještě jednou na **„Přesto otevřít"**.
   - Appka se spustí a **příště už jde normálně dvojklikem** – hláška se víc neukáže.

   Stačí udělat **jednou**. Žádný Terminál ani příkazy nejsou potřeba.

   > Na novějším macOS se „Přesto otevřít" v *prvním* dialogu schválně neukazuje – Apple
   > ho přesunul do Nastavení → Soukromí, aby to nešlo odkliknout omylem. Proto ty dva kroky.

> Proč to tak je: bez placeného Apple Developer ID ($99/rok) a notarizace macOS
> nenotarizovanou staženou appku napoprvé zablokuje – proto ten jednorázový krok
> „Přesto otevřít". Appka je ad-hoc podepsaná a `codesign --verify --strict` prochází,
> takže ji macOS nehlásí jako „poškozenou". Aktualizace kódu už pak appka řeší sama –
> nové DMG je potřeba jen zřídka.

---

## Pro uživatele (operátor u OBS)

1. Spusť **Výsledkový servis.app** (z Aplikací nebo Docku). Otevře se nativní okno
   s ovládáním. Aplikace se při startu sama tiše aktualizuje.
2. V ovládání vyber **závod** (ID/URL z hasicovo.cz), **kategorii**, **disciplínu**
   a **co zobrazit** (výsledková tabulka / lišta závodníků / celkové výsledky).
3. Klikni **„Otevřít overlay"** → otevře se druhé okno s grafikou (zelené
   klíčovací pozadí). Dej ho na fullscreen.
4. V **OBS** sejmi to okno (window/display capture) a přidej filtr **Chroma Key
   (zelená)**. Hotovo.

**Jmenovka (lower third):** sekce „Jmenovka" – ruční jmenovka nezávislá na závodu
(jméno + stát s vlaječkou + funkce, nebo vlastní text). Připravené jmenovky se ukládají.

**Zdroj z Google Tabulky (běžící tým):** v „Vybrat závod" přepni na **📊 Google
Tabulka** – místo hasicovo se „kdo právě běží" tahá z tabulky (přes odkaz na Apps
Script). Do lišty ukáže vlajku + startovní číslo + tým; přepínáš kategorii/disciplínu,
auto/ruční výběr. Tabulka zůstává soukromá, nepotřebuje klíč.

**Aktualizace:** menu **Aktualizace → Zkontrolovat aktualizace** (projeví se po
zavření a opětovném otevření appky).

**První spuštění z DMG na cizím Macu:** appka není notarizovaná, takže macOS ji
napoprvé zablokuje → **pravý klik na app → Otevřít** (nebo System Settings →
Soukromí a zabezpečení → „Otevřít přesto").

---

## Pro vývojáře (rychlý start)

```bash
pip install -r requirements.txt
python3 AdvancedResultWriting.py        # dev režim v prohlížeči
```

- Ovládání: <http://127.0.0.1:5000/>
- Overlay: <http://127.0.0.1:5000/overlay>

Proměnné prostředí:
- `HV_PORT` – port serveru (výchozí `5000`; nativní app používá `5100`)
- `HV_DEBUG=1` – Flask debug + autoreload

**Sestavení Mac aplikace + DMG:**

```bash
./build_app.sh        # výstup v dist/
```

---

## Overlay – parametry URL

- `/overlay` – chroma‑key zelené pozadí (výchozí)
- `/overlay?transparent=1` – průhledné pozadí (OBS browser source)
- `/overlay?bg=RRGGBB` – vlastní barva pozadí
- `/overlay?pagesec=N` – sekund na stránku (výchozí 8); tabulka stránkuje po 10 řádcích

---

## Ovládání hardwarem (Stream Deck / Companion)

Appka jde ovládat z **Elgato Stream Decku** (vlastní plugin) i z **Bitfocus
Companion 4.x** (vlastní modul). Tlačítka se barví podle stavu (aktivní pohled
červeně, běžící vysílání zeleně) a u „další/předchozí" ukazují hodnotu, na kterou
přepnou. Adresa appky je `127.0.0.1:5100` (nativní app) / `:5000` (dev).

**Stream Deck:**
- V appce menu **Stream Deck → Nainstalovat plugin do Stream Decku** (zkopíruje
  plugin a restartuje Stream Deck). Pak v Stream Decku přetáhni akce z kategorie
  „Výsledkový servis" a v Property Inspectoru zkontroluj adresu.

**Bitfocus Companion (4.x):**
- V appce menu **Companion → Návod k nastavení** (otevře postup) a **Připravit
  modul** (uloží `.tgz`). V Companionu pak *Connections → + Add → Import custom
  module* a zadej adresu.

### Přímé HTTP (`/control`) pro jiný HW / pokročilé

Vše stojí na jednom GET endpointu **`/control`** – jde volat z čehokoliv, co umí
HTTP požadavek.

**Co zobrazit (jedno tlačítko = jeden pohled):**
- `…/control?view=results` – výsledková tabulka
- `…/control?view=racers` – lišta závodníků
- `…/control?view=total` – celkové výsledky

**Přepínání výběru:**
- `…/control?category=next` / `…?category=prev` – další/předchozí kategorie
- `…/control?discipline=next` / `…?discipline=prev` – další/předchozí disciplína
  (u zdroje Google Tabulka přepíná disciplíny tabulky, u kategorie totéž)
- `…/control?page=next` / `…?page=prev` / `…?page=3` – stránka tabulky

**Jmenovka:**
- `…/control?nameplate=toggle` (nebo `show` / `hide`) – promítnout/skrýt jmenovku
  (obsah se nastaví v panelu)

**Vysílání:**
- `…/control?action=start` – spustí vysílání aktuálního závodu
- `…/control?action=stop` – zastaví a vyčistí overlay

**Kombinace v jednom tlačítku** (parametry jdou spojit přes `&`):
- `…/control?race=532&action=start&view=results` – načti závod 532, spusť a ukaž tabulku
- `…/control?view=racers&category=next` – přepni na lištu a posuň kategorii

Endpoint vrací JSON se stavem (`is_running`, `view`, `category`, `discipline`,
`page`) – plugin si z něj může číst zpětnou vazbu.
