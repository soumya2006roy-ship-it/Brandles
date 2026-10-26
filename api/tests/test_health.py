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


def test_openapi_marks_cookie_auth_and_leaves_public_endpoints_public(client):
    schema = client.get("/api/openapi.json").json()
    assert schema["components"]["securitySchemes"]["BrandLensSession"] == {
        "type": "apiKey",
        "in": "cookie",
        "name": "brandlens_session",
        "description": "Session cookie set by the BrandLens login endpoint.",
    }
    assert schema["paths"]["/api/v1/orgs/{org_id}/campaigns"]["get"]["security"] == [
        {"BrandLensSession": []}
    ]
    assert "security" not in schema["paths"]["/api/v1/auth/login"]["post"]
