# 🇦🇷 ARS Dashboard

Static single-page dashboard (just `index.html`) showing live Argentine market data and a EUR→ARS conversion calculator. Everything runs in the browser — no backend.

## What it shows

- **Acciones (BCBA):** YPFD, GGAL — last price, % change, bid/ask — via [data912.com](https://data912.com)
- **Dólar:** Oficial (BNA), MEP/Bolsa, Blue, Cripto, Tarjeta — via [dolarapi.com](https://dolarapi.com)
- **Euro:** oficial venta/compra + 7-day trend sparkline — live from [dolarapi.com](https://dolarapi.com), history from [argentinadatos.com](https://argentinadatos.com)
- **USDT/ARS:** Binance, Astropay + others, with the best-paying exchange highlighted — via [criptoya.com](https://criptoya.com)
- **Calculadora "¿Conviene?":** compares two paths to turn Payoneer EUR into ARS:
  - **A · Astropay** — send EUR to Astropay (fee) → sell EUR→ARS
  - **B · Binance** — buy USDT with Payoneer card (fee) → sell USDT→ARS
  - Rate fields auto-fill from live data and are fully editable. EUR→USDT comes from Binance `EURUSDT`; the Astropay EUR→ARS field is seeded with an estimate — replace it with your real rate.

Auto-refreshes every 60s.

## Run locally

Just open `index.html` in a browser, or:

```bash
cd ars-dashboard && python3 -m http.server 8000
# then open http://localhost:8000
```

## Deploy to GitHub Pages

```bash
cd ars-dashboard
git init && git add . && git commit -m "ARS dashboard"
gh repo create ars-dashboard --public --source=. --push
gh api repos/{owner}/ars-dashboard/pages -X POST -f source[branch]=main -f source[path]=/
```

Or via the UI: push the repo → **Settings → Pages → Source: `main` / root**. The site appears at `https://<user>.github.io/ars-dashboard/`.

> Data is delayed and APIs are third-party. Verify before operating with real money.
