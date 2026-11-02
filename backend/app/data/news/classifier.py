"""
NEPTUNE News Event & Asset Relevance Classifier (`classifier.py`)

Deterministic, rule-based classification engine implementing the 15-Category
Event Taxonomy and 6-Tier Asset Relevance Classification per Milestone 4.6.2 Section 4.
Governed by: Rule S-05, Rule S-08, ADR-023, ADR-024.
"""
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.data.news.models import EventCategory, RelevanceClassification


class DeterministicNewsClassifier:
    """
    Transparent, deterministic rule-based event and relevance classifier.
    Version: v1.0.0-deterministic
    """

    VERSION = "v1.0.0-deterministic"

    # Asset Recognition Patterns
    BTC_PATTERNS = [
        re.compile(r"\b(BTC|BITCOIN|SATOSHI|LIGHTNING NETWORK)\b", re.IGNORECASE),
        re.compile(r"\b(BTCUSDT|BTCUSDC|BTCFDUSD)\b", re.IGNORECASE),
    ]
    ETH_PATTERNS = [
        re.compile(r"\b(ETH|ETHEREUM|ETHER|VITALIK|EIP|ERC-20|ERC20)\b", re.IGNORECASE),
        re.compile(r"\b(ETHUSDT|ETHUSDC|ETHFDUSD)\b", re.IGNORECASE),
    ]
    BNB_DIRECT_PATTERNS = [
        re.compile(r"\b(BNB BURN|AUTO-BURN|QUARTERLY BURN|BEP-20|BEP20|BEP-2|BNB CHAIN|BUILD AND BUILD|BINANCE COIN|BSC ECOSYSTEM)\b", re.IGNORECASE),
        re.compile(r"\b(BNBUSDT|BNBUSDC|BNBFDUSD)\b", re.IGNORECASE),
    ]
    BINANCE_EXCHANGE_PATTERNS = [
        re.compile(r"\b(BINANCE|CHANGPENG ZHAO|CZ|RICHARD TENG|BINANCE\.COM)\b", re.IGNORECASE),
    ]

    # Major Altcoin Patterns (OTHER_ASSET)
    OTHER_ASSET_PATTERNS = [
        re.compile(r"\b(SOL|SOLANA|XRP|RIPPLE|ADA|CARDANO|DOGE|DOGECOIN|AVAX|AVALANCHE|DOT|POLKADOT|MATIC|POLYGON|LINK|CHAINLINK|PEPE|SHIB|SHIBA|SUI|APT|APTOS|TON|TONCOIN|NEAR|RENDER|FET|TAO|WIF|BONK|FLOKI)\b", re.IGNORECASE),
    ]

    # Event Category Patterns (ordered by specificity)
    CATEGORY_PATTERNS: List[Tuple[EventCategory, List[re.Pattern]]] = [
        (
            EventCategory.MONETARY_POLICY,
            [
                re.compile(r"\b(FOMC|FEDERAL RESERVE|THE FED|INTEREST RATE|RATE HIKE|RATE CUT|JEROME POWELL|POWELL|CENTRAL BANK|ECB|BOJ|QUANTITATIVE EASING|FED FUNDS RATE|MONETARY POLICY)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.MACROECONOMIC,
            [
                re.compile(r"\b(CPI|INFLATION|NONFARM PAYROLL|NFP|UNEMPLOYMENT RATE|GDP|CONSUMER PRICE INDEX|PRODUCER PRICE INDEX|PPI|RECESSION|JOBLESS CLAIMS|TREASURY YIELD)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.ETF_INSTITUTIONAL_FLOW,
            [
                re.compile(r"\b(SPOT BITCOIN ETF|SPOT ETHEREUM ETF|SPOT ETF|ETFS|BLACKROCK|IBIT|FIDELITY|FBTC|GRAYSCALE|GBTC|ETHA|19B-4|S-1 APPROVAL|INSTITUTIONAL INFLOW|INSTITUTIONAL OUTFLOW|ETF FLOWS)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.SECURITY_INCIDENT,
            [
                re.compile(r"\b(HACK|EXPLOIT|DRAIN|DRAINED|STOLEN|VULNERABILITY|COMPROMISED|ATTACK|BREACH|PHISHING|FLASH LOAN ATTACK|MALICIOUS|SECURITY INCIDENT|PRIVATE KEY LEAK)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.REGULATORY,
            [
                re.compile(r"\b(SEC|CFTC|DOJ|REGULATION|REGULATORY|LAWSUIT|SUED|ENFORCEMENT|COMPLIANCE|SUBPOENA|BAN|BANNED|SANCTIONS|FINCEN|FCA|ESMA|LEGAL ACTION|SETTLEMENT|GUILTY PLEA|CFTC CHARGES)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.EXCHANGE_SOLVENCY,
            [
                re.compile(r"\b(PROOF OF RESERVES|POR|SOLVENCY|INSOLVENT|BANK RUN|COLLAPSE|BANKRUPTCY|CHAPTER 11|DEFICIT|RESERVE RATIO|MERKLE TREE AUDIT|LIQUIDITY CRISIS)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.EXCHANGE_OPERATIONAL,
            [
                re.compile(r"\b(WALLET MAINTENANCE|SYSTEM UPGRADE|SCHEDULED UPGRADE|MAINTENANCE|SUSPEND DEPOSITS|RESUME DEPOSITS|TEMPORARILY SUSPEND|SYSTEM DOWNTIME|API UPGRADE|WALLET UPGRADE|TRADING SUSPENSION)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.PROTOCOL_UPGRADE,
            [
                re.compile(r"\b(HARD FORK|SOFT FORK|HALVING|HALVEMENT|DENCUN|EIP-4844|TAPROOT|SHANGHAI|THE MERGE|BEACON CHAIN|NETWORK UPGRADE|MAINNET LAUNCH|TESTNET UPGRADE|BITCOIN CORE)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.NETWORK_OUTAGE,
            [
                re.compile(r"\b(OUTAGE|NETWORK OUTAGE|DOWNTIME|NETWORK CONGESTION|BLOCK PRODUCTION HALTED|CHAIN REORG|NODE FAILURE|RPC OUTAGE)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.ASSET_DELISTING,
            [
                re.compile(r"\b(DELIST|DELISTING|WILL DELIST|REMOVAL OF (?:SPOT )?TRADING PAIRS|REMOVAL OF.*?PAIRS|CEASE TRADING|TERMINATION OF TRADING)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.ASSET_LISTING,
            [
                re.compile(r"\b(WILL LIST|NEW LISTING|ADDS TRADING PAIRS|NOW AVAILABLE ON|SEED TAG|INNOVATION ZONE|SPOT LISTING|FUTURES LISTING|LISTS|EXPANDS TRADING CHOICES)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.MARKET_STRUCTURE,
            [
                re.compile(r"\b(LEVERAGE|MARGIN REQUIREMENT|MAKER FEE|TAKER FEE|ZERO-FEE|FEE STRUCTURE|TICK SIZE|FUNDING RATE|LIQUIDATION ENGINE|ORDER BOOK DEPTH|COLLATERAL RATIO)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.LARGE_CAPITAL_FLOW,
            [
                re.compile(r"\b(WHALE|TREASURY TRANSFER|LARGE TRANSFER|MINTED|BURNED|TOKEN BURN|AUTO-BURN|QUARTERLY BURN|BURNING|SUPPLY REDUCTION|OTC DESK|TETHER MINTS|USDC MINTS)\b", re.IGNORECASE),
            ],
        ),
    ]

    def classify_article(
        self,
        title: str,
        body_text: Optional[str] = None,
        source: str = "",
        pairs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Deterministically classify an article into (EventCategory, RelevanceClassification, affected_assets).
        """
        combined_text = f"{title} {body_text or ''}".strip()
        matched_evidence: Dict[str, Any] = {
            "title": title,
            "matched_keywords": [],
            "detected_entities": [],
        }

        # 1. Detect Assets
        affected_assets: Set[str] = set()
        has_btc = any(p.search(combined_text) for p in self.BTC_PATTERNS)
        has_eth = any(p.search(combined_text) for p in self.ETH_PATTERNS)
        has_bnb_direct = any(p.search(combined_text) for p in self.BNB_DIRECT_PATTERNS)
        has_binance_exchange = any(p.search(combined_text) for p in self.BINANCE_EXCHANGE_PATTERNS)
        has_other = any(p.search(combined_text) for p in self.OTHER_ASSET_PATTERNS)

        if has_btc:
            affected_assets.add("BTC")
            matched_evidence["detected_entities"].append("BTC")
        if has_eth:
            affected_assets.add("ETH")
            matched_evidence["detected_entities"].append("ETH")
        if has_bnb_direct:
            affected_assets.add("BNB")
            matched_evidence["detected_entities"].append("BNB_DIRECT")
        if has_binance_exchange:
            matched_evidence["detected_entities"].append("BINANCE_EXCHANGE")

        # Check pairs parameter
        if pairs:
            for pair in pairs:
                p_upper = pair.upper()
                if "BTC" in p_upper:
                    affected_assets.add("BTC")
                if "ETH" in p_upper:
                    affected_assets.add("ETH")
                if "BNB" in p_upper:
                    affected_assets.add("BNB")

        # 2. Determine Event Category
        category = EventCategory.UNCLASSIFIED
        confidence = 0.5

        for cat, patterns in self.CATEGORY_PATTERNS:
            for p in patterns:
                m = p.search(combined_text)
                if m:
                    category = cat
                    confidence = 0.95
                    matched_evidence["matched_keywords"].append(m.group(0))
                    break
            if category != EventCategory.UNCLASSIFIED:
                break

        if category == EventCategory.UNCLASSIFIED:
            if "crypto" in combined_text.lower() or "market" in combined_text.lower():
                category = EventCategory.OTHER
                confidence = 0.6

        # 3. Determine Relevance Classification
        # Governed by Rule: A Binance exchange incident must not become DIRECT_ASSET for BNB
        relevance = RelevanceClassification.UNCLASSIFIED

        if category in (EventCategory.MONETARY_POLICY, EventCategory.MACROECONOMIC):
            relevance = RelevanceClassification.MACRO
            affected_assets.update(["BTC", "ETH", "BNB"])

        elif category == EventCategory.ETF_INSTITUTIONAL_FLOW:
            if "BTC" in affected_assets and "ETH" not in affected_assets:
                relevance = RelevanceClassification.DIRECT_ASSET
                affected_assets = {"BTC"}
            elif "ETH" in affected_assets and "BTC" not in affected_assets:
                relevance = RelevanceClassification.DIRECT_ASSET
                affected_assets = {"ETH"}
            else:
                relevance = RelevanceClassification.MARKET_WIDE
                affected_assets.update(["BTC", "ETH"])

        elif category in (EventCategory.EXCHANGE_OPERATIONAL, EventCategory.EXCHANGE_SOLVENCY):
            relevance = RelevanceClassification.EXCHANGE_WIDE
            # Do NOT attribute exchange operations as direct BNB token events unless BNB_DIRECT pattern matched
            if not has_bnb_direct and "BNB" in affected_assets:
                affected_assets.remove("BNB")

        elif category == EventCategory.PROTOCOL_UPGRADE:
            if affected_assets.intersection({"BTC", "ETH", "BNB"}):
                relevance = RelevanceClassification.DIRECT_ASSET
            else:
                relevance = RelevanceClassification.OTHER_ASSET

        elif category in (EventCategory.ASSET_LISTING, EventCategory.ASSET_DELISTING):
            target_intersection = affected_assets.intersection({"BTC", "ETH", "BNB"})
            if target_intersection:
                relevance = RelevanceClassification.DIRECT_ASSET
            else:
                relevance = RelevanceClassification.OTHER_ASSET

        elif category == EventCategory.SECURITY_INCIDENT:
            if has_binance_exchange and not has_bnb_direct:
                relevance = RelevanceClassification.EXCHANGE_WIDE
                if "BNB" in affected_assets:
                    affected_assets.remove("BNB")
            elif affected_assets.intersection({"BTC", "ETH", "BNB"}):
                relevance = RelevanceClassification.DIRECT_ASSET
            else:
                relevance = RelevanceClassification.OTHER_ASSET

        elif category == EventCategory.REGULATORY:
            target_intersection = affected_assets.intersection({"BTC", "ETH", "BNB"})
            if target_intersection:
                relevance = RelevanceClassification.DIRECT_ASSET
            elif has_binance_exchange:
                relevance = RelevanceClassification.EXCHANGE_WIDE
            else:
                relevance = RelevanceClassification.MARKET_WIDE
                affected_assets.update(["BTC", "ETH", "BNB"])

        else:
            # General fallback
            target_intersection = affected_assets.intersection({"BTC", "ETH", "BNB"})
            if target_intersection:
                relevance = RelevanceClassification.DIRECT_ASSET
            elif has_binance_exchange:
                relevance = RelevanceClassification.EXCHANGE_WIDE
            elif has_other:
                relevance = RelevanceClassification.OTHER_ASSET
            elif category != EventCategory.UNCLASSIFIED:
                relevance = RelevanceClassification.MARKET_WIDE
            else:
                relevance = RelevanceClassification.UNCLASSIFIED

        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "event_category": category,
            "relevance_classification": relevance,
            "affected_assets": sorted(list(affected_assets)),
            "classification_evidence": matched_evidence,
            "classifier_version": self.VERSION,
            "confidence_score": confidence,
            "classified_at": now_iso,
        }
