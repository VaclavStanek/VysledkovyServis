# Stream Deck plugin – Výsledkový servis

Ovládání overlaye přímo z Elgato Stream Decku. Tlačítka **svítí podle aktuálního
stavu** (aktivní pohled je červený, běžící vysílání bliká „● VYSÍLÁ") a u kategorií
/ disciplín / stránek ukazují aktuální výběr. Žádné psaní URL.

## Tlačítka (akce)

| Akce | Co dělá |
|------|---------|
| Výsledková tabulka | přepne overlay na výsledkovou tabulku |
| Lišta závodníků | přepne na lištu aktuálních závodníků |
| Celkové výsledky | přepne na celkové výsledky |
| Další / Předchozí kategorie | cykluje kategorie (ukazuje aktuální) |
| Další / Předchozí disciplína | cykluje disciplíny (ukazuje aktuální) |
| Další / Předchozí strana | stránkuje tabulku (ukazuje číslo) |
| Spustit / Zastavit vysílání | přepíná vysílání; zelená = spustit, červená = vysílá |
| Načíst a spustit závod | načte závod podle čísla (v nastavení tlačítka) a spustí |

## Instalace

```bash
./install.sh
```

Skript zkopíruje plugin do složky Stream Decku a restartuje aplikaci. Pak plugin
najdeš v seznamu akcí v kategorii **„Výsledkový servis"** – akce přetáhneš na
tlačítka.

Ruční instalace: zkopíruj složku `cz.vysledkovyservis.sdPlugin` do
`~/Library/Application Support/com.elgato.StreamDeck/Plugins/` a restartuj Stream Deck.

## Nastavení

V nastavení libovolného tlačítka (Property Inspector) je pole **host:port** –
adresa Výsledkového servisu. Je **společná pro všechna tlačítka**.

- Nativní aplikace na stejném Macu: `127.0.0.1:5100` (výchozí)
- Dev režim: `127.0.0.1:5000`
- Z jiného počítače: `IP-toho-Macu:5100` (app musí poslouchat na `0.0.0.0` –
  spusť ji s `HV_HOST=0.0.0.0`)

U akce **„Načíst a spustit závod"** je navíc pole na číslo závodu z hasicovo.cz.

## Jak to funguje

Plugin volá HTTP endpoint `/control` lokální Flask aplikace a každou ~1,2 s čte
`/status` pro zpětnou vazbu na tlačítkách. Žádný cloud, vše po localhostu.
