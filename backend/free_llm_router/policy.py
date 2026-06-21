"""
Provider ordering policy — YOUR decision point.

The router calls an ``OrderFn`` before every request to decide which provider to
try first, second, third… Given a live snapshot of each provider's state, return
the providers in the order you want them attempted.

The default policy (``free_llm_router.router.default_order``) sorts by static
``priority`` only. That's fine until reality intrudes:
  * The top-priority provider is rate-limited *this minute* — trying it first just
    wastes a failover hop (it'll be skipped, but it's still first in line).
  * A provider has burned 49/50 of its daily quota — maybe save it for last.
  * One provider has been consistently slow (high ``last_latency_ms``).
  * A provider's circuit is half_open — risky; maybe deprioritize.

`ProviderStats` gives you, per provider:
    .provider.priority      static rank (lower = preferred)
    .circuit_state          "closed" | "open" | "half_open"
    .tokens_available       bool — has an RPM token to spend right now
    .day_count / .day_limit requests spent today / documented daily cap (cap may be None)
    .last_latency_ms        most recent successful round-trip, 0.0 if never called

Tradeoffs to weigh:
  - Latency-first ordering gets fast answers but can stampede one provider until
    it rate-limits, then thrash.
  - Quota-preserving ordering (spread load, save scarce daily quotas for last)
    is gentler on the free tiers — which is the whole point of not getting banned.
  - Health-first ordering avoids dead providers but a pure "closed-circuits-first"
    sort ignores speed and quota entirely.

There is no single right answer — it depends on whether you optimize for speed,
for staying under the free caps, or for resilience. That's why it's yours.
"""

from __future__ import annotations

from typing import List

from .router import ProviderStats, default_order
from .providers import Provider


def smart_order(stats: List[ProviderStats]) -> List[Provider]:
    """Rank providers for the next request.

    Ordering criteria (cheapest-to-violate first):

    1. Circuit health: closed circuits first, then half_open, then open.
    2. Token availability: providers with an RPM token ready now come first.
    3. Daily quota availability: providers with more headroom in their documented
       daily cap come first. Providers with no documented cap are treated as
       having unlimited headroom.
    4. Static priority: lower ``provider.priority`` is preferred as a final
       tie-breaker.
    """

    def _circuit_rank(state: str) -> int:
        return {"closed": 0, "half_open": 1, "open": 2}.get(state, 2)

    def _quota_ratio(s: ProviderStats) -> float:
        if s.day_limit is None or s.day_limit <= 0:
            return 0.0  # unlimited or unknown = best availability
        return s.day_count / s.day_limit

    def rank(s: ProviderStats) -> tuple:
        return (
            _circuit_rank(s.circuit_state),
            0 if s.tokens_available else 1,
            _quota_ratio(s),
            s.provider.priority,
        )

    return [s.provider for s in sorted(stats, key=rank)]
