# Companion modul – Výsledkový servis

Nativní modul pro **Bitfocus Companion 4.x**. Ovládá výsledkový overlay přes stejné
HTTP API jako Stream Deck plugin (`/control`, `/status`) – akce, **feedback** (tlačítka
mění barvu podle stavu) a **proměnné** (aktuální i následující kategorie/disciplína/strana).

## Požadavky

- Bitfocus Companion **4.x** (běží na Node 22)
- Node.js + npm (kvůli `npm install`)
- Běžící aplikace **Výsledkový servis** (nativní app: `127.0.0.1:5100`)

## Sestavení

```bash
cd companion-modules/vysledkovyservis
npm install
npm run build
```

Build vytvoří složku `pkg/` (hotový modul) a balíček **`vysledkovyservis-<verze>.tgz`**.

## Instalace do Companionu (4.x)

**Nejjednodušší – z aplikace Výsledkový servis:**

1. V appce menu **Companion → Připravit modul pro Companion…** → ulož soubor
   (appka ho rovnou odhalí ve Finderu).
2. V Companionu **Connections → + Add connection → Import custom module** → vyber
   uložený soubor.
3. Přidej připojení **„Výsledkový servis"** a zadej **adresu** `127.0.0.1:5100`.

> Appka nese předsestavený `.tgz`, takže nemusíš nic buildit. Tahle sekce (build)
> je jen pro vývoj/úpravy modulu.

**Varianta A – import ručně sestaveného balíčku:**

1. V Companionu **Connections → + Add connection → Import custom module**
   (nebo *Settings → Modules → Import*).
2. Vyber vygenerovaný **`vysledkovyservis-1.0.0.tgz`**.
3. Přidej připojení **„Výsledkový servis"** a v nastavení zadej **adresu**
   `host:port` (default `127.0.0.1:5100`).

**Varianta B – vývojová cesta (auto-načítání při úpravách):**

1. **Settings → Developer modules path** nastav na složku
   `…/VysledkovyServis/companion-modules/vysledkovyservis`
   (Companion v ní najde sestavený podadresář `pkg`).
2. Pro průběžné úpravy spusť `npm run dev` (přebuilduje při změně).
3. **Connections → Add connection** → **„Výsledkový servis"**.

> `runtime.apiVersion` v manifestu doplní build sám podle nainstalované verze
> `@companion-module/base` (v2.x pro Companion 4.x), takže ho neřeš ručně.

## Akce

| Akce | Co dělá |
|------|---------|
| Pohled: Výsledková tabulka / Lišta / Celkové | přepne overlay na daný pohled |
| Kategorie / Disciplína / Strana: další / předchozí | cykluje výběr |
| Vysílání: spustit / zastavit / přepnout | ovládá vysílání do overlaye |
| Načíst a spustit závod | načte závod podle čísla a spustí |

## Feedback (barvy tlačítek)

- **Pohled je aktivní** → tlačítko zčervená, když je daný pohled v overlayi aktivní.
- **Vysílá data** → tlačítko zezelená, když overlay vysílá.

## Proměnné (pro text na tlačítkách)

Nahraď `vysledkovyservis` názvem svého připojení, pokud ho přejmenuješ:

- `$(vysledkovyservis:category)` / `category_next` / `category_prev`
- `$(vysledkovyservis:discipline)` / `discipline_next` / `discipline_prev`
- `$(vysledkovyservis:page)` / `page_next` / `page_prev`
- `$(vysledkovyservis:view)`, `$(vysledkovyservis:is_running)`

Např. tlačítko „další disciplína" s náhledem cíle: text
`Disciplína ▶\n$(vysledkovyservis:discipline_next)`.

## Presety

V záložce **Presets → Výsledkový servis** jsou hotová tlačítka (pohledy s červeným
zvýrazněním, vysílání se zeleným, cyklování kategorie/disciplíny/strany) – stačí
přetáhnout na tlačítko.
