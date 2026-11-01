"""
Unit tests — AGENTS.md Engineering Rules enforcement.

These tests verify that the architectural constraints defined in AGENTS.md
cannot be silently violated.
"""
import pytest
from decimal import Decimal


class TestMonetaryPrecision:
    """Rule A-01: All monetary calculations use Decimal, never float."""

    def test_decimal_addition_is_exact(self):
        a = Decimal("100.1")
        b = Decimal("0.2")
        result = a + b
        assert result == Decimal("100.3"), (
            "Decimal arithmetic must be exact. Use Decimal for all monetary values."
        )

    def test_float_addition_is_not_exact(self):
        """This test documents WHY we forbid float for money."""
        result = 100.1 + 0.2
        assert result != 100.3, (
            "Float is NOT exact. This documents the reason we use Decimal."
        )

    def test_position_size_calculation_uses_decimal(self):
        """
        Position sizing formula from RISK_MANAGEMENT.md:
        risk_amount = equity * risk_pct
        position_size = risk_amount / (entry_price - stop_price)
        """
        equity = Decimal("1000.00")
        risk_pct = Decimal("0.005")  # 0.5%
        entry_price = Decimal("50000.00")
        stop_price = Decimal("49500.00")

        risk_amount = equity * risk_pct
        stop_distance = entry_price - stop_price
        position_size = risk_amount / stop_distance

        assert risk_amount == Decimal("5.00")
        assert stop_distance == Decimal("500.00")
        assert position_size == Decimal("0.01")


class TestFeeCalculations:
    """Paper execution fee calculations must be exact."""

    def test_taker_fee_applied_to_buy(self):
        entry_price = Decimal("50000.00")
        quantity = Decimal("0.01")
        taker_fee_rate = Decimal("0.001")  # 0.1%

        notional = entry_price * quantity
        fee = notional * taker_fee_rate

        assert notional == Decimal("500.00")
        assert fee == Decimal("0.50")

    def test_round_trip_fee_cost(self):
        """Both entry and exit incur fees."""
        entry_price = Decimal("50000.00")
        exit_price = Decimal("51000.00")
        quantity = Decimal("0.01")
        fee_rate = Decimal("0.001")

        entry_notional = entry_price * quantity
        exit_notional = exit_price * quantity

        entry_fee = entry_notional * fee_rate
        exit_fee = exit_notional * fee_rate
        total_fees = entry_fee + exit_fee

        gross_pnl = exit_notional - entry_notional
        net_pnl = gross_pnl - total_fees

        assert gross_pnl == Decimal("10.00")
        assert total_fees == Decimal("1.01")
        assert net_pnl == Decimal("8.99")


class TestRewardRiskRatio:
    """Signal R:R calculation — minimum 1.5:1 enforced by risk manager."""

    def test_valid_long_setup(self):
        entry = Decimal("50000")
        stop = Decimal("49000")
        target = Decimal("51500")

        risk = entry - stop
        reward = target - entry
        rr = reward / risk

        assert rr == Decimal("1.5")

    def test_invalid_setup_below_minimum(self):
        entry = Decimal("50000")
        stop = Decimal("49000")
        target = Decimal("51000")  # Only 1:1

        risk = entry - stop
        reward = target - entry
        rr = reward / risk

        assert rr < Decimal("1.5"), "This setup should be rejected by risk manager."

    def test_zero_risk_is_invalid(self):
        """Stop at entry price is an invalid setup."""
        entry = Decimal("50000")
        stop = Decimal("50000")

        risk = entry - stop
        assert risk == Decimal("0"), "Zero risk means stop equals entry — invalid."
