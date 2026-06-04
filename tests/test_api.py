import pytest
import httpx
from backend.app import app
from tests.test_parser import generate_dummy
import asyncio
from fastapi.testclient import TestClient

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_upload_pdb_invalid():
    response = client.post("/api/upload_pdb", files={"file": ("test.pdb", b"invalid data")})
    assert response.status_code == 422

def test_upload_and_status():
    pdb_content = generate_dummy(15)
    response = client.post("/api/upload_pdb", files={"file": ("test.pdb", pdb_content)})
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    
    status_resp = client.get(f"/api/jobs/{job_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "pending"
