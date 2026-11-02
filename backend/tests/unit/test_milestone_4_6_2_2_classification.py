"""
NEPTUNE Milestone 4.6.2.2 Classification Regression & Remediation Tests
Validates fixes for Failure Modes 1 through 6 identified in Milestone 4.6.2.1 Audit.
"""
import pytest
from app.data.news.classifier import DeterministicNewsClassifier
from app.data.news.models import EventCategory, RelevanceClassification


@pytest.fixture
def classifier():
    return DeterministicNewsClassifier()


def test_failure_mode_1_market_structure_boundary(classifier):
    """
    Failure 1: Margin tiers, leverage updates, and tick size changes must be
    classified as MARKET_STRUCTURE, not general EXCHANGE_OPERATIONAL.
    """
    title = "Updates on the Leverage & Margin Tiers of Multiple USDⓈ-M Perpetual Contracts (2024-09-26)"
    body = "Binance Futures will adjust the leverage and margin tiers of USDⓈ-M perpetual contracts."
    res = classifier.classify_article(title=title, body_text=body, source="binance_announcements")

    assert res["event_category"] == EventCategory.MARKET_STRUCTURE
    assert res["relevance_classification"] == RelevanceClassification.EXCHANGE_WIDE
    assert res["classifier_version"] == "v1.1.0-deterministic"


def test_failure_mode_2_boilerplate_disclaimer_stripping(classifier):
    """
    Failure 2: Compliance and regulatory boilerplate footers must not cause
    promotional or informational announcements to be classified as REGULATORY.
    """
    title = "Earn Wednesday: New Limited-Time Offers Available Now! (2024-09-25)"
    body = (
        "Subscribe to Simple Earn locked products to enjoy higher APR rewards. "
        "Risk Warning: Digital asset prices are subject to high market risk. "
        "Binance reserves the right in its sole discretion to amend or cancel this announcement."
    )
    res = classifier.classify_article(title=title, body_text=body, source="binance_announcements")

    assert res["event_category"] == EventCategory.UNCLASSIFIED
    assert res["relevance_classification"] == RelevanceClassification.UNCLASSIFIED
    assert res["affected_assets"] == []


def test_failure_mode_3_security_regex_false_positive(classifier):
    """
    Failure 3: Fee promotions and protective language must not be classified
    as SECURITY_INCIDENT.
    """
    title = "Binance Will Support Zero Withdrawal Fees for bStocks"
    body = "Binance is pleased to launch zero withdrawal fees for tokenized stocks."
    res = classifier.classify_article(title=title, body_text=body, source="binance_announcements")

    assert res["event_category"] != EventCategory.SECURITY_INCIDENT
    assert res["event_category"] == EventCategory.MARKET_STRUCTURE
    assert res["relevance_classification"] == RelevanceClassification.EXCHANGE_WIDE


def test_failure_mode_4_promotional_asset_deattribution(classifier):
    """
    Failure 4: Retail campaigns mentioning crypto assets (e.g. BTC, ETH, OMNI)
    must not attribute direct asset trading relevance.
    """
    title = "Binance Adds OMNI on Simple Earn Locked Products"
    body = "Binance Simple Earn is pleased to announce the addition of OMNI on Simple Earn Locked Products."
    res = classifier.classify_article(title=title, body_text=body, source="binance_announcements")

    assert res["event_category"] == EventCategory.UNCLASSIFIED
    assert res["relevance_classification"] == RelevanceClassification.UNCLASSIFIED
    assert res["affected_assets"] == []


def test_failure_mode_5_category_precedence_masking(classifier):
    """
    Failure 5: Listing announcements must not be masked by regulatory disclaimers
    in the body text.
    """
    title = "Binance Will List Predict (PREDICT) with Seed Tag Applied"
    body = (
        "Binance will list Predict (PREDICT) and open trading for PREDICT/USDT. "
        "Users should ensure compliance with local regulations before trading."
    )
    res = classifier.classify_article(title=title, body_text=body, source="binance_announcements")

    assert res["event_category"] == EventCategory.ASSET_LISTING
    assert res["relevance_classification"] == RelevanceClassification.OTHER_ASSET


def test_failure_mode_6_punctuation_acronym_normalization(classifier):
    """
    Failure 6: Acronyms with periods (e.g. E.T.F., S.E.C., F.O.M.C.) must be
    detected cleanly without missing due to punctuation.
    """
    # ETF variation
    title_etf = "The Bitcoin E.T.F. Gets Approved — What to Expect Now."
    res_etf = classifier.classify_article(title=title_etf, body_text="", source="gdelt_gkg")
    assert res_etf["event_category"] == EventCategory.ETF_INSTITUTIONAL_FLOW
    assert res_etf["relevance_classification"] == RelevanceClassification.DIRECT_ASSET
    assert "BTC" in res_etf["affected_assets"]

    # SEC variation
    title_sec = "S.E.C. Files Civil Enforcement Action Against Crypto Firm"
    res_sec = classifier.classify_article(title=title_sec, body_text="", source="gdelt_gkg")
    assert res_sec["event_category"] == EventCategory.REGULATORY

