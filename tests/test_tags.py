"""Tests for Tag API"""

from fastapi import status
from fastapi.testclient import TestClient

from refinance.errors.common import NotFoundError


class TestTagEndpoints:
    """Test API endpoints for tags"""

    def test_create_tag(self, test_app: TestClient):
        # Create a new tag
        response = test_app.post("/tags/", json={"name": "Finance"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Finance"

    def test_get_tag(self, test_app: TestClient):
        # First create a tag, then retrieve it
        create_response = test_app.post("/tags/", json={"name": "Budget"})
        tag_id = create_response.json()["id"]
        response = test_app.get(f"/tags/{tag_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == tag_id
        assert data["name"] == "Budget"

    def test_update_tag(self, test_app: TestClient):
        # Create a tag, then update it
        create_response = test_app.post("/tags/", json={"name": "Budget"})
        tag_id = create_response.json()["id"]
        update_response = test_app.patch(
            f"/tags/{tag_id}", json={"name": "Updated Budget"}
        )
        assert update_response.status_code == status.HTTP_200_OK
        updated_data = update_response.json()
        assert updated_data["name"] == "Updated Budget"

    def test_delete_tag(self, test_app: TestClient):
        # Create a tag, then delete it
        create_response = test_app.post("/tags/", json={"name": "Temporary"})
        tag_id = create_response.json()["id"]
        delete_response = test_app.delete(f"/tags/{tag_id}")
        assert delete_response.status_code == status.HTTP_200_OK
        # Verify the tag is deleted
        get_response = test_app.get(f"/tags/{tag_id}")
        assert get_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert get_response.json()["error_code"] == NotFoundError.error_code

    def test_read_tags_with_filters(self, test_app: TestClient):
        # Create multiple tags
        test_app.post("/tags/", json={"name": "Personal"})
        test_app.post("/tags/", json={"name": "Professional"})
        # Filter tags by name
        filter_response = test_app.get("/tags/", params={"name": "Personal"})
        assert filter_response.status_code == status.HTTP_200_OK
        data = filter_response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Personal"
