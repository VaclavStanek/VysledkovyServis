# Výsledkový servis 🚒

Lokální výsledkový **overlay pro OBS** pro hasičské soutěže. Stahuje XML z
[hasicovo.cz](https://pozarnisport.hasicovo.cz), parsuje výsledky a zobrazuje je
jako broadcast grafiku, kterou lze promítnout do OBS (chroma-key zelené pozadí
nebo průhledné pozadí jako browser source).

Podporované typy závodů: jednotlivci, jednotlivci-víceboj (dorost), CTIF, Plamen, Dorost (týmy), TFA.

## Spuštění (vývoj)

```bash
pip install -r requirements.txt
python3 AdvancedResultWriting.py
```

- Ovládání: <http://127.0.0.1:5000/>
- Overlay pro OBS: <http://127.0.0.1:5000/overlay>

Konfigurace přes proměnné prostředí:
- `HV_PORT` – port serveru (výchozí `5000`)
- `HV_DEBUG=1` – vývojový režim s autoreloadem

## Overlay

- `/overlay` – chroma-key zelené pozadí (klíčuje se v OBS)
- `/overlay?transparent=1` – průhledné pozadí (OBS browser source)
- `/overlay?bg=RRGGBB` – vlastní barva pozadí
- `/overlay?pagesec=N` – sekund na stránku (výchozí 8); tabulka stránkuje po 10 řádcích

## Ovládání

Na stránce `/` vybereš závod (ID/URL z hasicovo.cz), kategorii, disciplínu a co
zobrazit (výsledková tabulka / lišta závodníků / celkové výsledky). Overlay se
aktualizuje automaticky.
