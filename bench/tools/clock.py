from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from dataclasses import dataclass, field
from typing import Optional

ISO_DURATION_RE = re.compile(
    r'P(?:(?P<years>\d+)Y)?(?:(?P<months>\d+)M)?(?:(?P<weeks>\d+)W)?(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?'
)


@dataclass
class VirtualClock:
    """Lightweight clock used to simulate temporal triggers during benchmarks."""

    start: Optional[datetime] = None
    tz: timezone = timezone.utc
    _now: datetime = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.start is None:
            self._now = datetime.now(tz=self.tz)
        else:
            self._now = self.start.replace(tzinfo=self.tz)

    def isoformat(self) -> str:
        """Return the current virtual time as an ISO 8601 string."""
        return self._now.isoformat()

    def advance(self, duration: str) -> None:
        """Advance the clock by a duration specified as an ISO 8601 duration string.
        
        Args:
            duration: ISO 8601 duration string (e.g., 'PT1H' for 1 hour, 'P1D' for 1 day)
        """
        delta = parse_iso_duration(duration)
        self._now += delta

    def set_time(self, new_time: datetime) -> None:
        """Set the clock to a specific datetime.
        
        Args:
            new_time: The new datetime to set the clock to
        """
        self._now = new_time.replace(tzinfo=self.tz).astimezone(self.tz)


def parse_iso_duration(duration: str) -> timedelta:
    match = ISO_DURATION_RE.fullmatch(duration)
    if not match:
        raise ValueError(f'Invalid ISO 8601 duration: {duration}')
    
    parts = {k: int(v) if v is not None else 0 for k, v in match.groupdict().items()}
    days = parts['days'] + parts['weeks'] * 7 + parts['months'] * 30 + parts['years'] * 365
    delta = timedelta(days=days, hours=parts['hours'], minutes=parts['minutes'], seconds=parts['seconds'])
    return delta


__all__ = ['VirtualClock', 'parse_iso_duration']
