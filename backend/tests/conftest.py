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

import pytest
from fastapi.testclient import TestClient

from app.db import engine
from app.main import app
from app.models import Base


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
