"""
HUNTER.OS - Product API Tests
"""
import pytest


class TestProducts:
    def test_create_product(self, client, auth_headers):
        """Test product creation."""
        res = client.post("/api/v1/products", json={
            "name": "TestProduct",
            "description_prompt": "A test product for agencies",
        }, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "TestProduct"
        assert data["status"] == "draft"

    def test_list_products(self, client, auth_headers):
        """Test listing products."""
        # Create a product first
        client.post("/api/v1/products", json={
            "name": "Product1",
            "description_prompt": "desc1",
        }, headers=auth_headers)

        res = client.get("/api/v1/products", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1

    def test_get_product(self, client, auth_headers):
        """Test getting a specific product."""
        create_res = client.post("/api/v1/products", json={
            "name": "GetMe",
            "description_prompt": "desc",
        }, headers=auth_headers)
        pid = create_res.json()["id"]

        res = client.get(f"/api/v1/products/{pid}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "GetMe"

    def test_update_product(self, client, auth_headers):
        """Test updating a product."""
        create_res = client.post("/api/v1/products", json={
            "name": "Original",
            "description_prompt": "orig desc",
        }, headers=auth_headers)
        pid = create_res.json()["id"]

        res = client.patch(f"/api/v1/products/{pid}", json={
            "name": "Updated",
        }, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Updated"

    def test_get_nonexistent_product(self, client, auth_headers):
        """Test 404 for nonexistent product."""
        res = client.get("/api/v1/products/99999", headers=auth_headers)
        assert res.status_code == 404

    def test_unauthorized_access(self, client):
        """Test product access without auth."""
        res = client.get("/api/v1/products")
        assert res.status_code == 401
