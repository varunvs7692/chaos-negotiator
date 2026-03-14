"""Configuration for pytest."""

import sys
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def clear_optional_auth_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests independent from developer machine environment secrets."""
    monkeypatch.delenv("API_AUTH_KEY", raising=False)
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
