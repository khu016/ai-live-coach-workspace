import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

_tmp = tempfile.mkdtemp(prefix="aac_test_")
os.environ["DATA_DIR"] = _tmp
os.environ["MODEL_API_KEY"] = ""
os.environ["ASR_PROVIDER"] = "mock"
os.environ["INVITE_CODES"] = "nivi-test-one,nivi-test-two"
os.environ["SESSION_COOKIE_SECURE"] = "false"
os.environ["ADMIN_ACCESS_CODE"] = "nivi-admin-test-code"

import pytest
from fastapi.testclient import TestClient

from app.db import engine
from app.main import app
from app.models import Base


@pytest.fixture()
def raw_client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def client(raw_client):
    response = raw_client.post(
        "/api/v1/auth/invite",
        json={"nickname": "测试主播", "invite_code": "nivi-test-one"},
    )
    assert response.status_code == 200
    return raw_client
