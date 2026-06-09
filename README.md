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
   napoprvé zablokuje s hláškou „od neidentifikovaného vývojáře". Postup:
   - Zkus appku otevřít dvojklikem (objeví se blokovací dialog – ten zavři).
   - Otevři **Nastavení systému → Soukromí a zabezpečení**, sjeď dolů a u zprávy o
     zablokované aplikaci klikni na **„Přesto otevřít"**.
   - Potvrď a zadej heslo. Hotovo – appka se spustí a příště už jde normálně dvojklikem.

   Stačí udělat **jednou**. Žádný Terminál ani příkazy nejsou potřeba.

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

## Ovládání přes Stream Deck (a jiné HW/HTTP)

Vše jde ovládat přes jeden GET endpoint **`/control`** – stačí tlačítku ve Stream
Decku nastavit URL. Použij akci/plugin, který volá HTTP na pozadí (např. *BarRaider
Web Requests* / *API Ninja*), aby se neotvíral prohlížeč.

Adresa serveru je `http://127.0.0.1:5100` (nativní app) nebo `:5000` (dev).

**Co zobrazit (jedno tlačítko = jeden pohled):**
- `…/control?view=results` – výsledková tabulka
- `…/control?view=racers` – lišta závodníků
- `…/control?view=total` – celkové výsledky

**Přepínání výběru:**
- `…/control?category=next` / `…?category=prev` – další/předchozí kategorie
- `…/control?discipline=next` / `…?discipline=prev` – další/předchozí disciplína
- `…/control?page=next` / `…?page=prev` / `…?page=3` – stránka tabulky

**Vysílání:**
- `…/control?action=start` – spustí vysílání aktuálního závodu
- `…/control?action=stop` – zastaví a vyčistí overlay

**Kombinace v jednom tlačítku** (parametry jdou spojit přes `&`):
- `…/control?race=532&action=start&view=results` – načti závod 532, spusť a ukaž tabulku
- `…/control?view=racers&category=next` – přepni na lištu a posuň kategorii

Endpoint vrací JSON se stavem (`is_running`, `view`, `category`, `discipline`,
`page`) – plugin si z něj může číst zpětnou vazbu.
