from app.schemas.health import HealthResponse


def test_health_response_shape() -> None:
    response = HealthResponse(status="ok", service="fintax-ai")

    assert response.model_dump() == {"status": "ok", "service": "fintax-ai"}
