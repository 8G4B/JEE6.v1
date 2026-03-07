from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def mock_db_session():
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.first.return_value = None
    session.all.return_value = []
    return session


@pytest.fixture(autouse=True)
def patch_session_local(mock_db_session):
    with patch(
        "src.infrastructure.database.Session.SessionLocal",
        return_value=mock_db_session,
    ):
        yield mock_db_session
