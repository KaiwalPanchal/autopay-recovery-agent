"""Every offline adversarial case must be blocked. See evals/offline_adversarial.py."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))
import offline_adversarial as adv  # noqa: E402  (shares the temp DB via AUTOPAY_DB_PATH set in conftest)


def test_suite_has_at_least_30_cases():
    assert len(adv.CASES) >= 30


@pytest.mark.parametrize("c", adv.CASES, ids=[c["id"] for c in adv.CASES])
def test_attack_is_blocked(c):
    assert c["fn"]() is True, f"{c['id']} {c['name']} was NOT blocked"
