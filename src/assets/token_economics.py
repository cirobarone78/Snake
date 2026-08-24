# pyright: strict
"""Does the token actually capture the value the protocol creates? (curated)

This is the question a market-cap screen cannot answer and the one that separates
"a business with a token" from "a ticker with a story". It has no free API, so
this registry is **hand-curated**, one entry per asset, each with the mechanism
and a source. Curated data ages: `verified_on` says when a human last checked.

Why it matters more here than in equities: a shareholder has a *legal* claim on
company profits. A token holder usually has none. Uniswap is the canonical case —
the protocol routes enormous volume, and UNI holders have historically received
nothing from it, because the fee switch governing that distribution stayed off.
Screening crypto on "the protocol earns a lot" without asking "does the token get
any of it" reproduces, in a more sophisticated form, the mistake of ranking coins
by market cap.

Two honesty rules baked into the design:

- **`UNKNOWN` is a real value, and the default.** An asset missing from this
  registry is not scored as "no accrual"; it is scored as not-known, and the
  report says so. Silence is not evidence.
- **No mechanism is ranked as "good".** ``MONETARY`` (Bitcoin) captures no
  protocol fees at all and is the most successful asset in the category; a
  ranking that punished it would be self-evidently broken. The mechanism is
  *described* so the reader can judge it against their own thesis — the score in
  ``fundamentals.py`` uses only "is there a mechanism at all", never a league
  table of which one is best.

Sources are the protocol's own documentation or governance record wherever
possible, because the alternative is repeating what an exchange's marketing page
says about its own token.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ValueAccrual(StrEnum):
    """How protocol value reaches the token holder, if it does."""

    FEE_BURN = "fee_burn"
    """Fees permanently destroy supply, so holders gain by dilution running in
    reverse. Ethereum's EIP-1559 base fee is the reference implementation."""

    STAKING_YIELD = "staking_yield"
    """Fees (and/or issuance) are paid to those who stake the token to secure or
    operate the network. Real cash flow, but partly funded by inflation — which
    is why the emission field matters next to it."""

    BUYBACK = "buyback"
    """The protocol or its issuer uses revenue to buy the token off the market.
    Economically a dividend; legally, usually a promise."""

    WORK_TOKEN = "work_token"
    """The token must be held or staked to *provide* the service, so demand
    scales with usage of the network rather than with speculation on it."""

    GAS_ONLY = "gas_only"
    """Needed to transact, but fees go to validators/miners as income rather than
    accruing to holders. Demand is real; capture is weak."""

    MONETARY = "monetary"
    """The thesis is the asset itself as money — scarcity and settlement
    assurances, not cash flow. Bitcoin. Not worse than the others, different."""

    GOVERNANCE_ONLY = "governance_only"
    """The token votes and nothing else. It may govern a treasury worth billions
    and still pay its holders nothing."""

    NONE = "none"
    """No mechanism connects the token's price to anything the network does."""

    UNKNOWN = "unknown"
    """Not researched, or genuinely unclear. The default — never an accusation."""


class Emission(StrEnum):
    """Direction of supply over time — the other half of the accrual question."""

    DEFLATIONARY = "deflationary"
    CAPPED = "capped"
    LOW_INFLATION = "low_inflation"
    HIGH_INFLATION = "high_inflation"
    UNLOCK_OVERHANG = "unlock_overhang"
    """Large scheduled unlocks still ahead: today's float understates supply."""
    UNKNOWN = "unknown"


class TokenEconomics(BaseModel):
    """Curated economics for one token."""

    symbol: str
    coingecko_id: str
    accrual: ValueAccrual = ValueAccrual.UNKNOWN
    emission: Emission = Emission.UNKNOWN
    what_it_does: str = Field(..., description="One line, in Italian, on the actual product")
    accrual_note: str = Field(
        default="",
        description=(
            "How value reaches (or fails to reach) the holder. Plain prose: this text is "
            "rendered into both Markdown and HTML, so it must carry no format markers."
        ),
    )
    source: str = Field(default="", description="Where a human can verify this")
    verified_on: str = Field(default="", description="ISO date a human last checked")


# Curated 2026-08-24. Ordered roughly by market cap for readability, not by merit.
TOKEN_ECONOMICS: list[TokenEconomics] = [
    TokenEconomics(
        symbol="BTC", coingecko_id="bitcoin",
        accrual=ValueAccrual.MONETARY, emission=Emission.CAPPED,
        what_it_does="Rete di regolamento e riserva di valore, senza emittente.",
        accrual_note="Non cattura ricavi di protocollo: le commissioni vanno ai miner. "
        "La tesi è la scarsità (21M) e la sicurezza del regolamento, non il cash flow.",
        source="https://bitcoin.org/bitcoin.pdf", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="ETH", coingecko_id="ethereum",
        accrual=ValueAccrual.FEE_BURN, emission=Emission.LOW_INFLATION,
        what_it_does="Piattaforma di smart contract su cui gira la maggior parte della DeFi.",
        accrual_note="EIP-1559 brucia la base fee di ogni transazione, e lo staking paga "
        "priority fee + MEV a chi mette ETH a garanzia. Doppio canale di cattura.",
        source="https://eips.ethereum.org/EIPS/eip-1559", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="SOL", coingecko_id="solana",
        accrual=ValueAccrual.STAKING_YIELD, emission=Emission.LOW_INFLATION,
        what_it_does="Layer 1 ad alto throughput, forte su DEX e pagamenti.",
        accrual_note="Metà della base fee è bruciata, il resto va ai validatori insieme "
        "alle priority fee; l'emissione decresce nel tempo verso il 1.5%.",
        source="https://solana.com/docs/economics", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="LINK", coingecko_id="chainlink",
        accrual=ValueAccrual.WORK_TOKEN, emission=Emission.UNLOCK_OVERHANG,
        what_it_does="Oracoli: porta dati esterni (prezzi, eventi) dentro gli smart contract.",
        accrual_note="I node operator mettono LINK a garanzia per fornire il servizio, e "
        "i pagamenti in LINK finanziano il pool di staking. Attenzione: circolante "
        "ancora sotto il totale, quindi c'è emissione residua da assorbire.",
        source="https://chain.link/economics", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="POL", coingecko_id="polygon-ecosystem-token",
        accrual=ValueAccrual.STAKING_YIELD, emission=Emission.HIGH_INFLATION,
        what_it_does="Token di staking dell'ecosistema Polygon (L2 di Ethereum).",
        accrual_note="Si mette a garanzia per validare le catene Polygon e si ricevono "
        "commissioni più emissione. L'emissione programmata (~2% annuo su due canali) "
        "è la parte che lavora contro il detentore.",
        source="https://polygon.technology/papers/pol-whitepaper", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="XRP", coingecko_id="ripple",
        accrual=ValueAccrual.GAS_ONLY, emission=Emission.UNLOCK_OVERHANG,
        what_it_does="Rete di pagamento e regolamento transfrontaliero.",
        accrual_note="Le commissioni sono bruciate ma sono minuscole. Il punto critico è "
        "l'offerta: una quota rilevante è ancora in escrow presso l'emittente e viene "
        "rilasciata nel tempo.",
        source="https://xrpl.org/transaction-cost.html", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="BNB", coingecko_id="binancecoin",
        accrual=ValueAccrual.BUYBACK, emission=Emission.DEFLATIONARY,
        what_it_does="Token della piattaforma Binance e gas della BNB Chain.",
        accrual_note="Burn trimestrale finanziato dall'emittente più burn automatico delle "
        "fee. La cattura è reale ma dipende da un'entità centralizzata e dal suo profilo "
        "regolamentare.",
        source="https://www.bnbchain.org/en/blog/bnb-auto-burn", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="DOGE", coingecko_id="dogecoin",
        accrual=ValueAccrual.NONE, emission=Emission.HIGH_INFLATION,
        what_it_does="Nessun prodotto oltre i pagamenti base; nato come parodia.",
        accrual_note="Nessun meccanismo lega il prezzo a un'attività della rete, e "
        "l'emissione è illimitata (10 miliardi di nuove monete l'anno, per sempre). "
        "Il prezzo dipende interamente dall'attenzione.",
        source="https://github.com/dogecoin/dogecoin", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="ADA", coingecko_id="cardano",
        accrual=ValueAccrual.STAKING_YIELD, emission=Emission.CAPPED,
        what_it_does="Layer 1 di smart contract; adozione DeFi finora modesta.",
        accrual_note="Staking pagato da commissioni e riserva monetaria. La cattura esiste, "
        "ma è proporzionale all'uso della rete, che è la variabile debole.",
        source="https://docs.cardano.org/about-cardano/learn/ada-and-fees",
        verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="XLM", coingecko_id="stellar",
        accrual=ValueAccrual.GAS_ONLY, emission=Emission.CAPPED,
        what_it_does="Rete di pagamenti e emissione di asset, focus rimesse e RWA.",
        accrual_note="Commissioni bassissime e nessuna redistribuzione ai detentori. "
        "Una quota rilevante dell'offerta è controllata dalla fondazione.",
        source="https://developers.stellar.org/docs/learn/fundamentals/lumens",
        verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="LTC", coingecko_id="litecoin",
        accrual=ValueAccrual.MONETARY, emission=Emission.CAPPED,
        what_it_does="Fork di Bitcoin con blocchi più rapidi; nessuna differenziazione forte.",
        accrual_note="Come Bitcoin non cattura ricavi, ma senza l'effetto rete che rende "
        "quella tesi credibile per Bitcoin.",
        source="https://litecoin.org", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="BCH", coingecko_id="bitcoin-cash",
        accrual=ValueAccrual.MONETARY, emission=Emission.CAPPED,
        what_it_does="Fork di Bitcoin con blocchi più grandi, orientato ai pagamenti.",
        accrual_note="Stessa struttura di Bitcoin, frazione dell'adozione e della "
        "sicurezza di hashrate.",
        source="https://bitcoincash.org", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="XMR", coingecko_id="monero",
        accrual=ValueAccrual.MONETARY, emission=Emission.LOW_INFLATION,
        what_it_does="Moneta con privacy obbligatoria a livello di protocollo.",
        accrual_note="Nessuna cattura di ricavi: la tesi è l'uso come contante digitale. "
        "Emissione di coda costante (0.6 XMR/blocco). Rischio distinto: delisting dagli "
        "exchange regolamentati, che ne comprime la liquidità accessibile.",
        source="https://www.getmonero.org/resources/moneropedia/tail-emission.html",
        verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="TRX", coingecko_id="tron",
        accrual=ValueAccrual.FEE_BURN, emission=Emission.DEFLATIONARY,
        what_it_does="Layer 1 usato soprattutto per il transito di stablecoin (USDT).",
        accrual_note="Le commissioni bruciano TRX e il volume di stablecoin è reale. "
        "Il rischio è di governance e concentrazione, non di assenza d'uso.",
        source="https://tronscan.org/#/data/stats2/overview", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="UNI", coingecko_id="uniswap",
        accrual=ValueAccrual.GOVERNANCE_ONLY, emission=Emission.UNLOCK_OVERHANG,
        what_it_does="Il principale exchange decentralizzato per volume.",
        accrual_note="Il caso di scuola: il protocollo genera commissioni enormi, che vanno "
        "ai fornitori di liquidità e non ai detentori di UNI. Il 'fee switch' che "
        "girerebbe una quota al token è oggetto di governance da anni.",
        source="https://gov.uniswap.org", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="AAVE", coingecko_id="aave",
        accrual=ValueAccrual.BUYBACK, emission=Emission.CAPPED,
        what_it_does="Protocollo di prestito on-chain fra i più grandi per depositi.",
        accrual_note="I ricavi finanziano acquisti di AAVE e chi mette il token nel Safety "
        "Module è pagato — ma quello stesso stake è la garanzia che copre eventuali "
        "insolvenze del protocollo.",
        source="https://governance.aave.com", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="ZEC", coingecko_id="zcash",
        accrual=ValueAccrual.MONETARY, emission=Emission.CAPPED,
        what_it_does="Moneta con privacy opzionale basata su prove a conoscenza zero.",
        accrual_note="Nessuna cattura di ricavi. Stesso rischio di delisting della privacy.",
        source="https://z.cash/technology", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="NEAR", coingecko_id="near",
        accrual=ValueAccrual.FEE_BURN, emission=Emission.LOW_INFLATION,
        what_it_does="Layer 1 con forte spinta su AI e astrazione delle catene.",
        accrual_note="Il 70% delle commissioni è bruciato, il resto va ai validatori; "
        "emissione del 5% annuo che lavora in senso opposto.",
        source="https://docs.near.org/protocol/gas", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="SUI", coingecko_id="sui",
        accrual=ValueAccrual.STAKING_YIELD, emission=Emission.UNLOCK_OVERHANG,
        what_it_does="Layer 1 recente, orientato a gaming e applicazioni ad alta frequenza.",
        accrual_note="Staking pagato dalle commissioni, ma meno della metà dell'offerta è "
        "circolante: gli sblocchi programmati sono il fattore dominante sul prezzo.",
        source="https://docs.sui.io/concepts/tokenomics", verified_on="2026-08-24",
    ),
    TokenEconomics(
        symbol="HYPE", coingecko_id="hyperliquid",
        accrual=ValueAccrual.BUYBACK, emission=Emission.UNLOCK_OVERHANG,
        what_it_does="Exchange di derivati on-chain con volumi elevati.",
        accrual_note="Una quota delle commissioni finanzia riacquisti del token — cattura "
        "diretta e insolita nel settore. Contro: circolante intorno a un quarto del totale, "
        "quindi sblocchi molto pesanti davanti, e codice del motore non pubblico.",
        source="https://hyperfoundation.org/stats", verified_on="2026-08-24",
    ),
]

_BY_SYMBOL: dict[str, TokenEconomics] = {t.symbol: t for t in TOKEN_ECONOMICS}
_BY_ID: dict[str, TokenEconomics] = {t.coingecko_id: t for t in TOKEN_ECONOMICS}


def get_economics(symbol: str | None = None, coingecko_id: str | None = None) -> TokenEconomics | None:
    """Curated economics for a token, or ``None`` when it is not in the registry.

    ``None`` means *not researched*, which the caller must render as unknown —
    never as "no value accrual".
    """
    if symbol is not None:
        found = _BY_SYMBOL.get(symbol.upper())
        if found is not None:
            return found
    if coingecko_id is not None:
        return _BY_ID.get(coingecko_id)
    return None


def covered_symbols() -> list[str]:
    """Symbols the registry covers, so a report can say what it did not check."""
    return sorted(_BY_SYMBOL)
