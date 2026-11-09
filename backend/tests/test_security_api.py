import app.api.routes.datasets as dataset_routes
import pytest

from tests.helpers import FULL_MAPPING, sales_csv, upload_and_wait

FRONTEND = "http://localhost:3000"


async def test_cors_preflight_for_the_frontend_origin(anon):
    response = await anon.options(
        "/api/datasets",
        headers={
            "Origin": FRONTEND,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND
    assert response.headers["access-control-allow-credentials"] == "true"  # needed for `credentials: "include"`
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


async def test_cors_refuses_other_origins(anon):
    response = await anon.options(
        "/api/datasets", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


async def test_credentialed_requests_from_the_frontend_get_cors_headers(client):
    response = await client.get("/api/datasets", headers={"Origin": FRONTEND})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "x-request-id" in response.headers["access-control-expose-headers"].lower()


async def test_browser_style_multipart_upload_with_origin_header_works(client):
    response = await client.post(
        "/api/datasets",
        files={"file": ("a.csv", sales_csv(days=20), "text/csv")},
        data={"mapping": "{}"},
        headers={"Origin": FRONTEND},
    )
    assert response.status_code == 202
    assert response.headers["access-control-allow-origin"] == FRONTEND


@pytest.mark.parametrize(
    ("origin", "allowed"),
    [
        ("https://evil.example", False),
        ("null", False),  # sandboxed iframes / file:// pages
        ("http://localhost:3001", False),  # same host, other port is another origin
        (FRONTEND, True),  # the configured frontend
        ("http://localhost:8000", True),  # the API's own origin (Swagger UI "Try it out")
        (None, True),  # no Origin header: curl, server-to-server
    ],
)
async def test_state_changing_requests_from_untrusted_origins_are_blocked(anon, origin, allowed):
    headers = {"Origin": origin} if origin else {}
    response = await anon.post("/api/auth/login", json={"email": "a@example.com", "password": "x"}, headers=headers)
    if allowed:
        assert response.status_code == 401  # reached the handler (wrong credentials)
    else:
        assert response.status_code == 403
        assert response.json()["code"] == "csrf_origin_mismatch"


async def test_safe_methods_are_not_origin_checked(client):
    assert (await client.get("/api/auth/me", headers={"Origin": "https://evil.example"})).status_code == 200


async def test_request_id_is_generated_and_echoed(anon):
    generated = (await anon.get("/api/health")).headers["x-request-id"]
    assert len(generated) == 32
    echoed = await anon.get("/api/health", headers={"X-Request-ID": "trace-1234-abcd"})
    assert echoed.headers["x-request-id"] == "trace-1234-abcd"
    hostile = await anon.get("/api/health", headers={"X-Request-ID": "x y\tz"})
    assert hostile.headers["x-request-id"] != "x y\tz" and len(hostile.headers["x-request-id"]) == 32


async def test_security_headers_on_every_response(client):
    for path in ("/api/health", "/api/datasets", "/api/nothing-here"):
        headers = (await client.get(path)).headers
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["referrer-policy"] == "no-referrer"
        assert headers["cache-control"] == "no-store"


async def test_oversized_json_bodies_are_refused_without_being_read(anon):
    response = await anon.post(
        "/api/auth/login",
        content=b'{"email": "' + b"a" * (1024 * 1024 + 10) + b'"}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"


async def test_errors_share_one_json_shape(client, anon):
    not_found = await anon.get("/api/does-not-exist")
    assert not_found.status_code == 404
    assert not_found.json() == {"code": "not_found", "message": "The requested resource was not found."}

    wrong_method = await client.post("/api/datasets/abc/analytics/overview")
    assert wrong_method.status_code == 405 and wrong_method.json()["code"] == "method_not_allowed"

    bad_json = await anon.post("/api/auth/login", content=b"{nope", headers={"Content-Type": "application/json"})
    assert bad_json.status_code == 422
    assert bad_json.json()["code"] == "validation_error"
    assert set(bad_json.json()) == {"code", "message", "details"}


async def test_unexpected_errors_become_a_clean_500_that_still_carries_cors_headers(client, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("secret internal detail: password=hunter2")

    monkeypatch.setattr(dataset_routes.dataset_service, "list_for_owner", boom)
    response = await client.get("/api/datasets", headers={"Origin": FRONTEND})
    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "message": "Something went wrong on our side. Please try again.",
    }
    assert "hunter2" not in response.text  # no internals leak
    assert response.headers["access-control-allow-origin"] == FRONTEND  # the browser can read the error
    assert response.headers["x-request-id"]


async def test_health_endpoints(anon):
    for path in ("/api/health", "/health"):
        assert (await anon.get(path)).json() == {"status": "ok"}
    assert (await anon.get("/api/health/ready")).json() == {"status": "ok", "database": "up"}


async def test_readiness_reports_database_outage_as_503(anon, monkeypatch):
    import app.api.routes.health as health

    class Broken:
        async def __aenter__(self):
            raise ConnectionError("database is down")

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(health, "get_sessionmaker", lambda: lambda: Broken())
    response = await anon.get("/api/health/ready")
    assert response.status_code == 503 and response.json() == {"status": "degraded", "database": "down"}


async def test_openapi_documents_every_frontend_endpoint(anon):
    spec = (await anon.get("/api/openapi.json")).json()
    expected = {
        ("post", "/api/auth/login"),
        ("post", "/api/auth/register"),
        ("post", "/api/auth/logout"),
        ("get", "/api/auth/me"),
        ("get", "/api/datasets"),
        ("post", "/api/datasets"),
        ("get", "/api/datasets/{dataset_id}"),
        ("delete", "/api/datasets/{dataset_id}"),
        ("get", "/api/datasets/{dataset_id}/processing"),
        ("get", "/api/datasets/{dataset_id}/analytics/overview"),
        ("get", "/api/datasets/{dataset_id}/analytics/sales"),
        ("get", "/api/datasets/{dataset_id}/analytics/products"),
        ("get", "/api/datasets/{dataset_id}/analytics/customers"),
        ("get", "/api/datasets/{dataset_id}/analytics/finance"),
        ("get", "/api/datasets/{dataset_id}/analytics/insights"),
        ("get", "/api/datasets/{dataset_id}/records"),
        ("post", "/api/datasets/{dataset_id}/reports/preview"),
        ("get", "/api/datasets/{dataset_id}/reports"),
        ("post", "/api/datasets/{dataset_id}/reports"),
    }
    documented = {(m, p) for p, ops in spec["paths"].items() for m in ops}
    assert expected <= documented
    assert (await anon.get("/api/docs")).status_code == 200


async def test_large_responses_are_gzip_compressed(client):
    ds = await upload_and_wait(client, sales_csv(days=120), "big.csv", mapping=FULL_MAPPING)
    response = await client.get(f"/api/datasets/{ds['id']}/records", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200 and response.headers["content-encoding"] == "gzip"
    assert response.headers["vary"].lower().count("accept-encoding") >= 1
