"""
NEPTUNE News Event & Asset Relevance Classifier (`classifier.py`)

Deterministic, rule-based classification engine implementing the 15-Category
Event Taxonomy and 6-Tier Asset Relevance Classification per Milestone 4.6.2 & 4.6.2.2.
Version: v1.1.0-deterministic
Remediates Failure Modes 1-6 from Milestone 4.6.2.1 Audit:
- Title-primary two-stage waterfall precedence
- Disclaimer and risk warning boilerplate footer stripping
- Punctuation-agnostic acronym normalization (E.T.F., S.E.C., F.O.M.C.)
- Strict separation of MARKET_STRUCTURE from EXCHANGE_OPERATIONAL
- Prevention of promotional campaign asset over-attribution
- Elimination of regulatory disclaimer false positives

Governed by: Rule S-05, Rule S-08, ADR-023, ADR-024, ADR-025.
"""
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.data.news.models import EventCategory, RelevanceClassification


class DeterministicNewsClassifier:
    """
    Transparent, deterministic rule-based event and relevance classifier.
    Version: v1.1.0-deterministic
    """

    VERSION = "v1.1.0-deterministic"

    # Standard legal/boilerplate footer markers to strip from body text
    DISCLAIMER_PATTERNS = [
        re.compile(r"(risk warning\s*:|risk disclaimer\s*:|disclaimer\s*:|terms and conditions\s*:|general notice\s*:|binance reserves the right in its sole discretion)", re.IGNORECASE),
        re.compile(r"(this is a general announcement\.|products and services referred to here may not be available in your region\.|digital asset prices are subject to high market risk)", re.IGNORECASE),
    ]

    # Promotional retail campaigns that do not constitute economic market events
    PROMOTIONAL_PATTERNS = [
        re.compile(r"\b(earn wednesday|limited-time offers?|simple earn|locked products?|dual investment|trading tournament|trade to share|learn & earn|learn and earn|voucher|airdrop|yield arena|launchpool|binance pool supports|flexible rate|exclusive reward|join the challenge|competition|zero-fee trading carnival|referral program|vip invitation)\b", re.IGNORECASE),
    ]

    # Asset Recognition Patterns
    BTC_PATTERNS = [
        re.compile(r"(?<!/)(?<!-)\b(BTC|BITCOIN|SATOSHI|LIGHTNING NETWORK)\b", re.IGNORECASE),
        re.compile(r"\b(BTCUSDT|BTCUSDC|BTCFDUSD)\b", re.IGNORECASE),
    ]
    ETH_PATTERNS = [
        re.compile(r"(?<!/)(?<!-)\b(ETH|ETHEREUM|ETHER|VITALIK|EIP|ERC-20|ERC20)\b", re.IGNORECASE),
        re.compile(r"\b(ETHUSDT|ETHUSDC|ETHFDUSD)\b", re.IGNORECASE),
    ]
    BNB_DIRECT_PATTERNS = [
        re.compile(r"(?<!/)(?<!-)\b(BNB BURN|AUTO-BURN|QUARTERLY BURN|BEP-20|BEP20|BEP-2|BNB CHAIN|BUILD AND BUILD|BINANCE COIN|BSC ECOSYSTEM|\bBNB\b)\b", re.IGNORECASE),
        re.compile(r"\b(BNBUSDT|BNBUSDC|BNBFDUSD)\b", re.IGNORECASE),
    ]
    BINANCE_EXCHANGE_PATTERNS = [
        re.compile(r"\b(BINANCE|CHANGPENG ZHAO|CZ|RICHARD TENG|BINANCE\.COM)\b", re.IGNORECASE),
    ]

    # Major Altcoin Patterns (OTHER_ASSET)
    OTHER_ASSET_PATTERNS = [
        re.compile(r"\b(SOL|SOLANA|XRP|RIPPLE|ADA|CARDANO|DOGE|DOGECOIN|AVAX|AVALANCHE|DOT|POLKADOT|MATIC|POLYGON|LINK|CHAINLINK|PEPE|SHIB|SHIBA|SUI|APT|APTOS|TON|TONCOIN|NEAR|RENDER|FET|TAO|WIF|BONK|FLOKI|LTC|LITECOIN|BCH|ATOM|COSMOS|KDA|KADENA|ALGO|ALGORAND|XLM|STELLAR|TRX|TRON|FTM|FANTOM)\b", re.IGNORECASE),
    ]

    # Category Patterns ordered by architectural priority in v1.1.0
    # MARKET_STRUCTURE precedes EXCHANGE_OPERATIONAL
    # ASSET_DELISTING and ASSET_LISTING precede general REGULATORY
    CATEGORY_PATTERNS: List[Tuple[EventCategory, List[re.Pattern]]] = [
        (
            EventCategory.MONETARY_POLICY,
            [
                re.compile(r"\b(FOMC|FEDERAL RESERVE|THE FED|FED INTEREST RATE|POLICY RATE|BENCHMARK RATE|INTEREST RATE (?:HIKE|CUT|DECISION)|RATE HIKE|RATE CUT|JEROME POWELL|POWELL|CENTRAL BANK|ECB|BOJ|QUANTITATIVE EASING|FED FUNDS RATE|MONETARY POLICY)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.MACROECONOMIC,
            [
                re.compile(r"\b(US CPI|CONSUMER PRICE INDEX|INFLATION|NONFARM PAYROLLS?|NFP|UNEMPLOYMENT RATE|GDP|PRODUCER PRICE INDEX|PPI|RECESSION|JOBLESS CLAIMS|TREASURY YIELD|\bCPI\b)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.ETF_INSTITUTIONAL_FLOW,
            [
                re.compile(r"\b(SPOT BITCOIN ETF|SPOT ETHEREUM ETF|SPOT ETF|ETFS?|E\.T\.F\.?S?|BLACKROCK|IBIT|FIDELITY|FBTC|GRAYSCALE|GBTC|ETHA|19B-4|S-1 APPROVAL|INSTITUTIONAL INFLOW|INSTITUTIONAL OUTFLOW|ETF FLOWS?|BITCOIN ETF|ETHEREUM ETF)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.ASSET_DELISTING,
            [
                re.compile(r"\b(DELIST|DELISTING|WILL DELIST|REMOVAL OF (?:SPOT |MARGIN )?TRADING PAIRS?|REMOVAL OF.*?PAIRS?|CEASE TRADING|TERMINATION OF TRADING|MONITORING TAG)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.ASSET_LISTING,
            [
                re.compile(r"\b(WILL LIST|NEW LISTING|ADDS TRADING PAIRS?|NOW AVAILABLE ON|SEED TAG|INNOVATION ZONE|SPOT LISTING|FUTURES LISTING|EXPANDS TRADING CHOICES|LISTS|ADDS.*?BSTOCKS|BSTOCKS LISTING|LISTS.*?BSTOCKS)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.MARKET_STRUCTURE,
            [
                re.compile(r"\b(LEVERAGE|MARGIN REQUIREMENT|MARGIN TIERS?|LEVERAGE TIERS?|CAPPED FUNDING RATE|FUNDING RATE|TICK SIZE|MAKER FEE|TAKER FEE|ZERO-FEE|FEE STRUCTURE|ZERO WITHDRAWAL FEES?|LIQUIDATION ENGINE|ORDER BOOK DEPTH|COLLATERAL RATIO|CONTRACT SIZE|CONTRACT SPECIFICATION|PRE-IPO PERP|CONVERT.*?PERP)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.EXCHANGE_SOLVENCY,
            [
                re.compile(r"\b(PROOF OF RESERVES|POR|SOLVENCY|INSOLVENT|BANK RUN|COLLAPSE|BANKRUPTCY|CHAPTER 11|DEFICIT|RESERVE RATIO|MERKLE TREE AUDIT|LIQUIDITY CRISIS)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.PROTOCOL_UPGRADE,
            [
                re.compile(r"\b(HARD FORK|SOFT FORK|HALVING|HALVEMENT|DENCUN|PECTRA|EIP-4844|TAPROOT|SHANGHAI|THE MERGE|BEACON CHAIN|NETWORK UPGRADE|MAINNET LAUNCH|TESTNET UPGRADE|BITCOIN CORE|TOKEN SWAP|REDENOMINATION)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.SECURITY_INCIDENT,
            [
                re.compile(r"\b(HACK|EXPLOIT|DRAIN|DRAINED|STOLEN|FLASH LOAN ATTACK|SECURITY INCIDENT|PRIVATE KEY LEAK|SECURITY BREACH)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.REGULATORY,
            [
                re.compile(r"\b(SEC|CFTC|DOJ|REGULATION|REGULATORY|LAWSUIT|SUED|ENFORCEMENT|SUBPOENA|BAN|BANNED|SANCTIONS|FINCEN|FCA|ESMA|LEGAL ACTION|SETTLEMENT|GUILTY PLEA|CFTC CHARGES)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.EXCHANGE_OPERATIONAL,
            [
                re.compile(r"\b(WALLET MAINTENANCE|SYSTEM UPGRADE|SCHEDULED UPGRADE|MAINTENANCE|SUSPEND DEPOSITS|RESUME DEPOSITS|TEMPORARILY SUSPEND|SYSTEM DOWNTIME|API UPGRADE|WALLET UPGRADE|TRADING SUSPENSION)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.NETWORK_OUTAGE,
            [
                re.compile(r"\b(OUTAGE|NETWORK OUTAGE|DOWNTIME|NETWORK CONGESTION|BLOCK PRODUCTION HALTED|CHAIN REORG|NODE FAILURE|RPC OUTAGE)\b", re.IGNORECASE),
            ],
        ),
        (
            EventCategory.LARGE_CAPITAL_FLOW,
            [
                re.compile(r"\b(WHALE|TREASURY TRANSFER|LARGE TRANSFER|MINTED|BURNED|TOKEN BURN|AUTO-BURN|QUARTERLY BURN|BURNING|SUPPLY REDUCTION|OTC DESK|TETHER MINTS|USDC MINTS)\b", re.IGNORECASE),
            ],
        ),
    ]

    def _normalize_punctuation(self, text: str) -> str:
        """Normalize acronyms with periods (e.g. E.T.F. -> ETF, S.E.C. -> SEC)."""
        text = re.sub(r'\bE\.T\.F\.?s?\b', 'ETF', text, flags=re.IGNORECASE)
        text = re.sub(r'\bS\.E\.C\.?\b', 'SEC', text, flags=re.IGNORECASE)
        text = re.sub(r'\bF\.O\.M\.C\.?\b', 'FOMC', text, flags=re.IGNORECASE)
        text = re.sub(r'\bC\.P\.I\.?\b', 'CPI', text, flags=re.IGNORECASE)
        return text

    def _strip_boilerplate(self, body_text: Optional[str]) -> str:
        """Strip legal disclaimers, risk warnings, and terms from body text."""
        if not body_text:
            return ""
        text = body_text
        for p in self.DISCLAIMER_PATTERNS:
            m = p.search(text)
            if m:
                text = text[:m.start()]
        return text.strip()

    def classify_article(
        self,
        title: str,
        body_text: Optional[str] = None,
        source: str = "",
        pairs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Deterministically classify an article into (EventCategory, RelevanceClassification, affected_assets).
        Version 1.1.0 implements title-primary precedence and disclaimer stripping.
        """
        title_norm = self._normalize_punctuation(title)
        body_clean = self._strip_boilerplate(body_text)
        body_norm = self._normalize_punctuation(body_clean)

        combined_text = f"{title_norm} {body_norm}".strip()
        matched_evidence: Dict[str, Any] = {
            "title": title,
            "matched_keywords": [],
            "detected_entities": [],
        }

        # Check for promotional campaign in title
        is_promotional = any(p.search(title_norm) for p in self.PROMOTIONAL_PATTERNS)

        # 1. Detect Assets
        affected_assets: Set[str] = set()
        has_btc = any(p.search(title_norm) for p in self.BTC_PATTERNS) or any(p.search(body_norm) for p in self.BTC_PATTERNS)
        has_eth = any(p.search(title_norm) for p in self.ETH_PATTERNS) or any(p.search(body_norm) for p in self.ETH_PATTERNS)
        has_bnb_direct = any(p.search(title_norm) for p in self.BNB_DIRECT_PATTERNS) or any(p.search(body_norm) for p in self.BNB_DIRECT_PATTERNS)
        has_binance_exchange = any(p.search(title_norm) for p in self.BINANCE_EXCHANGE_PATTERNS) or any(p.search(body_norm) for p in self.BINANCE_EXCHANGE_PATTERNS)
        has_other = any(p.search(title_norm) for p in self.OTHER_ASSET_PATTERNS) or any(p.search(body_norm) for p in self.OTHER_ASSET_PATTERNS)

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
        secondary_categories: List[str] = []

        if is_promotional:
            category = EventCategory.UNCLASSIFIED
            confidence = 0.85
            matched_evidence["matched_keywords"].append("PROMOTIONAL_CAMPAIGN")
        else:
            # Stage 1: Evaluate TITLE first (Title-Primary Precedence)
            for cat, patterns in self.CATEGORY_PATTERNS:
                for p in patterns:
                    m = p.search(title_norm)
                    if m:
                        category = cat
                        confidence = 0.98
                        matched_evidence["matched_keywords"].append(f"TITLE:{m.group(0)}")
                        break
                if category != EventCategory.UNCLASSIFIED:
                    break

            # Stage 2: If Title did not match, evaluate cleaned body text
            if category == EventCategory.UNCLASSIFIED:
                for cat, patterns in self.CATEGORY_PATTERNS:
                    for p in patterns:
                        m = p.search(body_norm)
                        if m:
                            category = cat
                            confidence = 0.90
                            matched_evidence["matched_keywords"].append(f"BODY:{m.group(0)}")
                            break
                    if category != EventCategory.UNCLASSIFIED:
                        break

            # Check for secondary category in body text if title was category
            if category != EventCategory.UNCLASSIFIED:
                for cat, patterns in self.CATEGORY_PATTERNS:
                    if cat == category:
                        continue
                    for p in patterns:
                        m = p.search(body_norm)
                        if m:
                            secondary_categories.append(cat.value)
                            break
                    if len(secondary_categories) >= 2:
                        break

            if category == EventCategory.UNCLASSIFIED:
                if "crypto" in combined_text.lower() or "market" in combined_text.lower():
                    category = EventCategory.OTHER
                    confidence = 0.65

        # 3. Determine Relevance Classification
        relevance = RelevanceClassification.UNCLASSIFIED

        if is_promotional:
            relevance = RelevanceClassification.UNCLASSIFIED
            # Strip direct asset attribution from promotional marketing campaigns
            affected_assets = set()

        elif category in (EventCategory.MONETARY_POLICY, EventCategory.MACROECONOMIC):
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

        elif category in (EventCategory.EXCHANGE_OPERATIONAL, EventCategory.EXCHANGE_SOLVENCY, EventCategory.MARKET_STRUCTURE):
            relevance = RelevanceClassification.EXCHANGE_WIDE
            # Do NOT attribute exchange operations as direct BNB token events unless BNB_DIRECT pattern matched
            if not has_bnb_direct and "BNB" in affected_assets:
                affected_assets.remove("BNB")
            # If exchange-wide, general pairs in text are not direct trading events on BTC/ETH
            if not has_bnb_direct:
                affected_assets = set()

        elif category in (EventCategory.ASSET_LISTING, EventCategory.ASSET_DELISTING):
            # Check if BTC, ETH, or BNB is the primary asset listed/delisted
            title_upper = title_norm.upper()
            direct_target = set()
            for sym in ["BTC", "ETH", "BNB"]:
                if re.search(rf"\b{sym}\b", title_upper) and not any(p in title_upper for p in [f"/{sym}", "MARGIN PAIR", "PERPETUAL"]):
                    direct_target.add(sym)
            if direct_target:
                relevance = RelevanceClassification.DIRECT_ASSET
                affected_assets = direct_target
            else:
                relevance = RelevanceClassification.OTHER_ASSET
                affected_assets = set()

        elif category == EventCategory.PROTOCOL_UPGRADE:
            target_intersection = affected_assets.intersection({"BTC", "ETH", "BNB"})
            if target_intersection:
                relevance = RelevanceClassification.DIRECT_ASSET
                affected_assets = target_intersection
            else:
                relevance = RelevanceClassification.OTHER_ASSET

        elif category == EventCategory.SECURITY_INCIDENT:
            if has_binance_exchange and not has_bnb_direct:
                relevance = RelevanceClassification.EXCHANGE_WIDE
                affected_assets = set()
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
                affected_assets = set()
            else:
                relevance = RelevanceClassification.MARKET_WIDE
                affected_assets.update(["BTC", "ETH", "BNB"])

        else:
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
            "secondary_categories": secondary_categories,
            "classification_evidence": matched_evidence,
            "classifier_version": self.VERSION,
            "confidence_score": confidence,
            "classified_at": now_iso,
        }
