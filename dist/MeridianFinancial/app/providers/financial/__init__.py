"""Active provider selection. MockProvider is a process singleton so injected
dev transactions and served cursors survive across requests."""
from __future__ import annotations

from app.core.config import get_settings
from app.providers.financial.base import (  # noqa: F401
    AccountDTO,
    BalanceDTO,
    FinancialDataProvider,
    ProviderRateLimited,
    ProviderTransientError,
    TransactionDTO,
    TransactionPage,
)
from app.providers.financial.mock import MockProvider
from app.providers.financial.plaid import PlaidProvider  # noqa: F401

_provider: MockProvider | None = None


def get_provider() -> MockProvider:
    global _provider
    if _provider is None:
        settings = get_settings()
        _provider = MockProvider(
            settings.sample_data_dir / "provider_fixtures",
            min_latency=settings.mock_min_latency,
            max_latency=settings.mock_max_latency,
            failure_rate=settings.mock_failure_rate,
        )
    return _provider


def reset_provider_state() -> None:
    """Testing hook."""
    global _provider
    _provider = None
