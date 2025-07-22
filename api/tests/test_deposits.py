"""Tests for deposit endpoints"""

import pytest
from fastapi.testclient import TestClient


class TestDepositEndpoints:
    def test_get_deposits_empty(self, test_app: TestClient, token):
        """Test getting deposits when there are none"""
        response = test_app.get("/deposits", headers={"x-token": token})
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_deposits_with_filters(self, test_app: TestClient, token):
        """Test getting deposits with filters"""
        response = test_app.get(
            "/deposits",
            params={"status": "pending", "limit": 10},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_get_nonexistent_deposit(self, test_app: TestClient, token):
        """Test getting a deposit that doesn't exist"""
        response = test_app.get("/deposits/999999", headers={"x-token": token})
        assert response.status_code == 418  # NotFoundError
