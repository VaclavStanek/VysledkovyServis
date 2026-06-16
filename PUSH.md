# Jak pushovat na GitHub

## Problém
Repo je `VaclavStanek/VysledkovyServis`. macOS Keychain může mít uložený špatný
účet (`MichalHimerVUT`), který nemá push práva → 403.

## Řešení: push přes token z .env

1. Vyplň `.env` (soubor není na gitu):
   ```
   GITHUB_USER=MichalHimer        # nebo jiný účet s push právy
   GITHUB_TOKEN=ghp_xxxxxxxxxxxx  # https://github.com/settings/tokens, scope: repo
   ```

2. Claude při každém pushu načte `.env` a použije token:
   ```bash
   source .env && git push https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/VaclavStanek/VysledkovyServis.git main
   ```

## Jak Claude pushuje (instrukce pro příští session)

**Vždy před `git push`:**
1. Zkontroluj `VERSION` – schéma `RRRR.MM.DD[.N]`. Pokud dnešní datum ještě není,
   nastav `RRRR.MM.DD.1`. Pokud je, zvedni `.N` o 1. Vždy commitni VERSION jako
   samostatný commit „Bump X.Y.Z" hned před pushem (in-app updater porovnává číslo).
2. Načti `.env` (`source .env`)
3. Zkontroluj, že `GITHUB_TOKEN` není prázdný – pokud je, řekni uživateli ať ho doplní
4. Použij URL s tokenem (viz výše), **nikdy** holý `git push`

Token vydrží dokud ho uživatel nezruší. Při expiraci nebo 403 – znovu na
https://github.com/settings/tokens vygenerovat nový a zapsat do `.env`.

## Verze Companion pluginu

Verze pluginu je v `companion-modules/vysledkovyservis/package.json` → `"version"`.
Změna vyžaduje rebuild:
```bash
cd companion-modules/vysledkovyservis
# uprav package.json version
npm run build
cp vysledkovyservis-<verze>.tgz ../vysledkovyservis.tgz
rm vysledkovyservis-<verze>.tgz
```
Pak commitni `main.js` + `package.json` + `../vysledkovyservis.tgz` a pushni jako obvykle.
