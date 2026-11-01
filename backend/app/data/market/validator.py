"""
NEPTUNE Market Data — Candle Validator

Enforces absolute data integrity on incoming market data:
- Rejects incomplete candles for strategy evaluations (Rule A-09).
- Normalizes all timestamps to UTC ISO 8601 strings (Rule A-02, ADR-012).
- Validates OHLC mathematical invariants:
    high >= low
    high >= max(open, close)
    low <= min(open, close)
    all prices > 0
    volume >= 0
- Detects duplicate candles and sequence gaps.
"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import re

from pydantic import BaseModel, Field, field_validator


class ValidatedCandle(BaseModel):
    """Normalized, validated candle model."""
    symbol: str
    timeframe: str
    timestamp: str            # ISO 8601 UTC string e.g. '2026-11-01T20:00:00.000Z'
    open: float = Field(gt=0.0)
    high: float = Field(gt=0.0)
    low: float = Field(gt=0.0)
    close: float = Field(gt=0.0)
    volume: float = Field(ge=0.0)
    is_closed: bool = True
    quote_volume: Optional[float] = Field(default=None, ge=0.0)
    trades_count: Optional[int] = Field(default=None, ge=0)

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_utc_iso(cls, v: Any) -> str:
        """Ensure canonical ISO 8601 UTC format ending in Z."""
        if isinstance(v, (int, float)):
            # Handle epoch milliseconds or seconds
            epoch_sec = v / 1000.0 if v > 1e11 else float(v)
            dt = datetime.fromtimestamp(epoch_sec, tz=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        elif isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            else:
                v = v.astimezone(timezone.utc)
            return v.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        elif isinstance(v, str):
            # Parse string and ensure UTC
            cleaned = v.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(cleaned)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            except Exception as e:
                raise ValueError(f"Invalid timestamp format: {v} ({e})")
        raise ValueError(f"Unsupported timestamp type: {type(v)}")

    @property
    def dt_utc(self) -> datetime:
        """Return parsed datetime object in UTC."""
        return datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))


@dataclass
class ValidationIssue:
    severity: str        # 'ERROR' | 'WARNING'
    field: str
    message: str
    candle_index: Optional[int] = None
    timestamp: Optional[str] = None


class CandleValidator:
    """
    Validation engine for individual candles and sequences of candles.
    """

    TIMEFRAME_MINUTES = {
        "1m": 1,
        "3m": 3,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "2h": 120,
        "4h": 240,
        "6h": 360,
        "8h": 480,
        "12h": 720,
        "1d": 1440,
    }

    @classmethod
    def validate_candle(
        cls,
        data: Dict[str, Any],
        require_closed: bool = True
    ) -> Tuple[Optional[ValidatedCandle], List[ValidationIssue]]:
        """
        Validate and normalize a single candle dictionary.
        
        Args:
            data: Raw candle dictionary.
            require_closed: If True, rejects incomplete candles.
        
        Returns:
            (ValidatedCandle or None, list of ValidationIssues)
        """
        issues: List[ValidationIssue] = []

        # 1. Incomplete candle check
        is_closed = data.get("is_closed", True)
        if require_closed and not is_closed:
            issues.append(ValidationIssue(
                severity="ERROR",
                field="is_closed",
                message="Incomplete candle rejected for closed-candle evaluation (Rule A-09)."
            ))
            return None, issues

        # 2. Pydantic validation & type coercion
        try:
            candle = ValidatedCandle(**data)
        except Exception as e:
            issues.append(ValidationIssue(
                severity="ERROR",
                field="schema",
                message=f"Candle failed schema validation: {str(e)}"
            ))
            return None, issues

        # 3. OHLC mathematical invariants
        if candle.high < candle.low:
            issues.append(ValidationIssue(
                severity="ERROR",
                field="high_low",
                message=f"High ({candle.high}) is lower than Low ({candle.low}).",
                timestamp=candle.timestamp
            ))

        if candle.high < max(candle.open, candle.close):
            issues.append(ValidationIssue(
                severity="ERROR",
                field="high_bound",
                message=f"High ({candle.high}) is lower than Open ({candle.open}) or Close ({candle.close}).",
                timestamp=candle.timestamp
            ))

        if candle.low > min(candle.open, candle.close):
            issues.append(ValidationIssue(
                severity="ERROR",
                field="low_bound",
                message=f"Low ({candle.low}) is greater than Open ({candle.open}) or Close ({candle.close}).",
                timestamp=candle.timestamp
            ))

        # If any ERROR issues exist, reject the candle
        if any(i.severity == "ERROR" for i in issues):
            return None, issues

        return candle, issues

    @classmethod
    def validate_sequence(
        cls,
        candles: List[ValidatedCandle],
        timeframe: str,
        allow_duplicates: bool = False
    ) -> Tuple[List[ValidatedCandle], List[ValidationIssue]]:
        """
        Validate a chronological sequence of candles:
        - Checks timestamp strictly increasing order.
        - Detects and drops duplicate timestamps.
        - Identifies gaps larger than 1 timeframe interval.
        """
        issues: List[ValidationIssue] = []
        if not candles:
            return [], issues

        interval_mins = cls.TIMEFRAME_MINUTES.get(timeframe)
        expected_step = timedelta(minutes=interval_mins) if interval_mins else None

        valid_sequence: List[ValidatedCandle] = []
        seen_timestamps = set()

        for idx, candle in enumerate(candles):
            ts = candle.timestamp

            # Check duplicate
            if ts in seen_timestamps:
                issues.append(ValidationIssue(
                    severity="WARNING" if not allow_duplicates else "INFO",
                    field="duplicate_timestamp",
                    message=f"Duplicate candle timestamp {ts} detected at index {idx}.",
                    candle_index=idx,
                    timestamp=ts
                ))
                if not allow_duplicates:
                    continue  # drop duplicate

            seen_timestamps.add(ts)

            # Check ordering and gaps against previous valid candle
            if valid_sequence:
                prev_candle = valid_sequence[-1]
                prev_dt = prev_candle.dt_utc
                curr_dt = candle.dt_utc

                if curr_dt <= prev_dt:
                    issues.append(ValidationIssue(
                        severity="ERROR",
                        field="timestamp_order",
                        message=f"Timestamp out of order: {curr_dt} <= {prev_dt} at index {idx}.",
                        candle_index=idx,
                        timestamp=ts
                    ))
                    continue

                if expected_step:
                    delta = curr_dt - prev_dt
                    if delta > expected_step:
                        missing_count = int(delta / expected_step) - 1
                        issues.append(ValidationIssue(
                            severity="WARNING",
                            field="missing_candles_gap",
                            message=f"Sequence gap detected between {prev_candle.timestamp} and {ts}. Approx {missing_count} missing candles.",
                            candle_index=idx,
                            timestamp=ts
                        ))

            valid_sequence.append(candle)

        return valid_sequence, issues
