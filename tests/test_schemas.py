import pytest
from pydantic import ValidationError

from src.auth import check_password
from src.schemas import TERM_KEYS, Finding


def make(status):
    return Finding(term="notice_period", status=status, wording=None, page=None,
                   explanation="e", reason="r", sources=[], question=None)


def test_invalid_status_rejected():
    with pytest.raises(ValidationError):
        make("Compliant")


@pytest.mark.parametrize("s", ["Consistent", "Needs Attention", "Unable to Assess"])
def test_valid_statuses(s):
    assert make(s).status == s


def test_term_keys():
    assert len(TERM_KEYS) == 11 and TERM_KEYS[0] == "salary_payment"


def test_check_password():
    assert check_password("pw", "pw")
    assert not check_password("bad", "pw")
    assert not check_password("", "")
