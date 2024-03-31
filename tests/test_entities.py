"""Tests for Entity API endpoints"""

from fastapi import status


def test_create_entity(test_app):
    # create a new entity, resident
    response = test_app.post(
        "/entities/",
        json={"name": "Vasya Pupkin", "comment": "resident"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Vasya Pupkin"
    assert data["comment"] == "resident"
    assert data["active"] is True


def test_get_entity(test_app):
    # get entity, check all create details match
    response = test_app.get("/entities/1")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Vasya Pupkin"
    assert data["comment"] == "resident"
    assert data["active"] is True


def test_patch_entity(test_app):
    # modify data
    new_attrs = {"name": "Vasya Pupkin 2", "comment": "resident 2", "active": False}
    response_1 = test_app.patch("/entities/1", json=new_attrs)
    assert response_1.status_code == 200
    # check that modified data is returned now
    response_2 = test_app.get("/entities/1")
    data = response_2.json()
    for k, new_value in new_attrs.items():
        assert data[k] == new_value


def test_delete_entity_error(test_app):
    # try to delete, receive an error
    response = test_app.delete("/entities/1")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_get_non_existent_entity_error(test_app):
    # try to get, receive an error
    response = test_app.get("/entities/1111")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert data["error_code"] == 4040
    assert "not found" in data["error"].lower()
