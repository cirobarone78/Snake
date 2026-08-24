# Piano di accumulo

## Quota da 10€: **LINK**

Motivo: è leggermente sotto peso rispetto al target.

> ⚠️ I pesi qui sotto sono **stimati** replicando il piano dalla data di inizio: il sistema non conosce le quantità realmente possedute. Inserendole in `config/dca_plan.yaml` (`holdings_units`) lo scarto dal target diventa esatto.

| # | Asset | Peso ora | Target | Scarto | Posizione nel range | Punteggio |
|---|-------|----------|--------|--------|---------------------|-----------|
| 1 | LINK | 30.0% | 33.3% | +3.3 pp | 93% | 1.000 |
| 2 | SOL | 32.3% | 33.3% | +1.0 pp | 94% | 0.500 |
| 3 | POL | 37.6% | 33.3% | -4.3 pp | 100% | 0.000 |

### Cosa dice la verifica storica

Backtest sui flussi reali (2020-04-10 → 2026-08-24, 77 acquisti, commissioni 0.5%):

- **Rendimento: nessun vantaggio.** Rapporto con la divisione in parti uguali 1.013 sul periodo completo, ma 1.19 nella prima metà e 0.91 nella seconda: si alterna, quindi è rumore. Contro 200 estrazioni casuali sta al 54.5° percentile.
- **Allocazione: vantaggio reale e stabile.** Distanza finale dal target 80 pp contro 102 pp della divisione fissa; nella metà out-of-sample 5.3 pp contro 30.5 pp.
- **Comprare il più forte è la strategia peggiore**: 40.5° percentile, sotto il caso.

## Candidate per un accumulo a lungo termine

Monete che superano i filtri meccanici. Nessun giudizio di merito: sono i nomi da studiare, non da comprare al buio.

| # | Asset | Cap. | Liquidità | Età min. | Da max | Note |
|---|-------|------|-----------|----------|--------|------|
| 1 | XRP (XRP) | $93.7B | 5.7% | 12.3 anni | -59% | - |
| 2 | DOGE (Dogecoin) | $14.3B | 6.5% | 11.3 anni | -87% | meme coin |
| 3 | LTC (Litecoin) | $4.1B | 9.2% | 11.6 anni | -87% | - |
| 4 | XLM (Stellar) | $6.9B | 4.2% | 11.5 anni | -77% | real world assets |
| 5 | BNB (BNB) | $93.5B | 1.0% | 8.8 anni | -49% | token di exchange |
| 6 | TRX (TRON) | $32.6B | 1.1% | 8.8 anni | -20% | diversifica |
| 7 | ADA (Cardano) | $8.3B | 6.7% | 6.5 anni | -93% | - |
| 8 | XMR (Monero) | $7.9B | 1.2% | 11.6 anni | -47% | privacy |
| 9 | BCH (Bitcoin Cash) | $5.5B | 3.7% | 7.7 anni | -93% | diversifica |
| 10 | ZEC (Zcash) | $14.2B | 9.3% | 2.1 anni | -74% | privacy |

### Escluse dal filtro

- capitalizzazione sotto la soglia: 27
- stablecoin o token ancorato: 21
- volume troppo basso rispetto alla capitalizzazione: 9
- già in portafoglio: 5

## Limiti

- La regola sulla quota satellite NON ha battuto la divisione in parti uguali: sul campione completo è al 54° percentile contro 200 estrazioni casuali. Serve a mantenere l'allocazione, non a guadagnare di più.
- Comprare l'asset più forte del momento ('momentum') è risultato peggiore del caso (40° percentile): è l'istinto più comune ed è quello che ha reso meno.
- Le candidate sono filtrate su criteri meccanici (dimensione, liquidità, età minima dimostrabile). Nessun giudizio su tecnologia, team o prospettive.
- Survivorship bias: la classifica di oggi contiene solo chi è sopravvissuto. Gran parte della top 100 del 2018 non esiste più, e quelle monete non compaiono in questi dati.
- Su orizzonti di 5-10 anni le singole altcoin hanno un tasso di mortalità storicamente alto. La soglia di capitalizzazione è un indizio di solidità, non una garanzia.

> Contenuto educativo, non consulenza finanziaria. Nessuna previsione: la scelta proposta serve a rispettare l'allocazione decisa, non a indovinare quale asset salirà.
