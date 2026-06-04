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

## Pro uživatele (operátor u OBS)

1. Spusť **Výsledkový servis.app** (z plochy nebo Docku). Otevře se nativní okno
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
