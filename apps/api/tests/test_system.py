"""System routes, request ids, problem details, security headers, CORS and OpenAPI."""

import json
import logging
from uuid import UUID

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from weta_api.config import Settings
from weta_api.log import JsonFormatter, request_id_var
from weta_api.main import create_app

API = "/api/v1"


class TestHealth:
    def test_liveness(self, client: TestClient) -> None:
        response = client.get(f"{API}/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_readiness_without_database_is_not_ready(self, client: TestClient) -> None:
        response = client.get(f"{API}/health/ready")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "not_configured"
        assert body["checks"] == [
            {
                "name": "database",
                "status": "not_configured",
                "detail": "WETA_DATABASE_URL is not set",
                "version": None,
            }
        ]

    def test_readiness_with_unreachable_database_hides_credentials(self) -> None:
        secret = "s3cr3t-password"
        unreachable = Settings(
            _env_file=None,  # type: ignore[call-arg]
            environment="test",
            # Port 1 on loopback: nothing listens there, so the connection is refused.
            database_url=f"postgresql+asyncpg://weta:{secret}@127.0.0.1:1/weta_dev",
            db_check_timeout_s=5.0,
        )
        with TestClient(create_app(unreachable)) as client:
            response = client.get(f"{API}/health/ready")
        assert response.status_code == 503
        check = response.json()["checks"][0]
        assert check["status"] == "unavailable"
        assert secret not in response.text
        assert "127.0.0.1" not in response.text

    def test_version(self, client: TestClient) -> None:
        body = client.get(f"{API}/version").json()
        assert body["api_version"] == "v1"
        assert body["environment"] == "test"
        assert body["components"]["weta-core"] == "0.1.0"
        assert {"fastapi", "pydantic", "pint", "sqlalchemy"} <= body["components"].keys()


class TestRequestId:
    def test_assigned_when_absent(self, client: TestClient) -> None:
        rid = client.get(f"{API}/health").headers["x-request-id"]
        assert UUID(rid).version == 7

    def test_safe_incoming_id_is_kept(self, client: TestClient) -> None:
        response = client.get(f"{API}/health", headers={"X-Request-ID": "trace-1234abcd"})
        assert response.headers["x-request-id"] == "trace-1234abcd"

    @pytest.mark.parametrize("bad", ["short", "has spaces in it", "x" * 200, "injectéxyzab"])
    def test_unsafe_incoming_id_is_replaced(self, client: TestClient, bad: str) -> None:
        headers = {"X-Request-ID": bad.encode("utf-8")}
        rid = client.get(f"{API}/health", headers=headers).headers["x-request-id"]
        assert UUID(rid).version == 7


class TestProblemDetails:
    def test_unknown_route_is_a_problem(self, client: TestClient) -> None:
        response = client.get(f"{API}/does-not-exist")
        assert response.status_code == 404
        assert response.headers["content-type"] == "application/problem+json"
        body = response.json()
        assert body["title"] == "Not Found"
        assert body["status"] == 404
        assert body["instance"] == f"{API}/does-not-exist"
        assert body["request_id"] == response.headers["x-request-id"]

    def test_method_not_allowed_is_a_problem(self, client: TestClient) -> None:
        response = client.post(f"{API}/health")
        assert response.status_code == 405
        assert response.json()["title"] == "Method Not Allowed"

    def test_validation_errors_list_fields_without_echoing_input(self, settings: Settings) -> None:
        app = create_app(settings)
        probe = APIRouter()

        @probe.get("/probe")
        async def probe_route(limit: int) -> dict[str, int]:
            return {"limit": limit}

        app.include_router(probe, prefix=API)
        with TestClient(app) as client:
            response = client.get(f"{API}/probe", params={"limit": "secret-not-a-number"})
        assert response.status_code == 422
        body = response.json()
        assert body["title"] == "Request validation failed"
        assert body["errors"][0]["loc"] == ["query", "limit"]
        assert "secret-not-a-number" not in response.text

    def test_unhandled_error_is_generic_and_logged(
        self, settings: Settings, caplog: pytest.LogCaptureFixture
    ) -> None:
        app = create_app(settings)
        boom = APIRouter()

        @boom.get("/boom")
        async def boom_route() -> None:
            msg = "internal detail that must not leak"
            raise RuntimeError(msg)

        app.include_router(boom, prefix=API)
        logging.getLogger("weta").propagate = True
        try:
            with (
                caplog.at_level(logging.ERROR, logger="weta.api.errors"),
                TestClient(app, raise_server_exceptions=False) as client,
            ):
                response = client.get(f"{API}/boom")
        finally:
            logging.getLogger("weta").propagate = False
        assert response.status_code == 500
        assert response.headers["content-type"] == "application/problem+json"
        assert "must not leak" not in response.text
        rid = response.json()["request_id"]
        assert response.headers["x-request-id"] == rid
        assert any(r.exc_info for r in caplog.records)


class TestHeaders:
    def test_security_headers(self, client: TestClient) -> None:
        headers = client.get(f"{API}/health").headers
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
        assert headers["referrer-policy"] == "no-referrer"
        assert "default-src 'none'" in headers["content-security-policy"]

    def test_docs_page_is_exempt_from_api_csp(self, client: TestClient) -> None:
        response = client.get(f"{API}/docs")
        assert response.status_code == 200
        assert "content-security-policy" not in response.headers

    def test_docs_disabled_in_production(self, settings: Settings) -> None:
        prod = settings.model_copy(update={"environment": "production"})
        with TestClient(create_app(prod)) as client:
            assert client.get(f"{API}/docs").status_code == 404

    def test_cors_allows_configured_origin_only(self, client: TestClient) -> None:
        preflight = {"Access-Control-Request-Method": "GET"}
        ok = client.options(
            f"{API}/health", headers={"Origin": "http://localhost:5173", **preflight}
        )
        assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
        denied = client.options(
            f"{API}/health", headers={"Origin": "https://evil.example", **preflight}
        )
        assert "access-control-allow-origin" not in denied.headers


class TestOpenApi:
    def test_document_lists_routes_and_shared_schemas(self, client: TestClient) -> None:
        doc = client.get(f"{API}/openapi.json").json()
        assert {f"{API}/health", f"{API}/health/ready", f"{API}/version"} <= doc["paths"].keys()
        schemas = doc["components"]["schemas"]
        assert {"QuantityOut", "ProblemDetail", "Taint", "ProvenanceClass"} <= schemas.keys()
        assert set(schemas["ProvenanceClass"]["enum"]) == {
            "OBSERVED",
            "USER_PROVIDED",
            "IMPORTED",
            "DERIVED",
            "MODELLED",
            "PREDICTED",
            "SCENARIO_ASSUMPTION",
            "SYNTHETIC_DEMO",
        }


class TestSettings:
    def test_empty_database_url_means_not_configured(self) -> None:
        settings = Settings(_env_file=None, database_url="  ")  # type: ignore[call-arg]
        assert settings.database_url is None

    def test_production_rejects_wildcard_cors(self) -> None:
        with pytest.raises(ValueError, match="wildcard"):
            Settings(_env_file=None, environment="production", allowed_origins=["*"])  # type: ignore[call-arg]

    def test_secrets_do_not_appear_in_repr(self) -> None:
        settings = Settings(_env_file=None, secret_key="do-not-print-me")  # type: ignore[call-arg]
        assert "do-not-print-me" not in repr(settings)


def test_json_log_lines_carry_request_id() -> None:
    token = request_id_var.set("rid-12345678")
    try:
        record = logging.makeLogRecord({"name": "weta.test", "msg": "hello", "levelname": "INFO"})
        record.path = "/x"
        line = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)
    assert line["msg"] == "hello"
    assert line["request_id"] == "rid-12345678"
    assert line["path"] == "/x"
