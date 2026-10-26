def test_health_and_interactive_api_docs_are_available(client):
    health = client.get("/health")
    docs = client.get("/docs")
    schema = client.get("/api/openapi.json")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert docs.status_code == 200
    assert "Swagger UI" in docs.text
    assert schema.status_code == 200
    assert schema.json()["info"]["title"] == "BrandLens API"
