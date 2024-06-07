"""Tests for token authentication"""

from fastapi.testclient import TestClient


class TestTokenAuth:
    """Test security of protected API endpoints"""

    def test_access_protected_route_with_valid_token(self, test_app: TestClient):
        test_app.headers = {}
        response = test_app.get("/entities/", headers={"x-token": "valid-token-000"})
        assert response.status_code == 200

    def test_access_protected_route_with_invalid_token(self, test_app: TestClient):
        test_app.headers = {}
        response = test_app.get("/entities/", headers={"x-token": "invalid-token-123"})
        assert response.status_code == 403

    def test_access_protected_route_without_token(self, test_app: TestClient):
        test_app.headers = {}
        response = test_app.get("/entities/")
        assert response.status_code == 403
