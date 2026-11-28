import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_create_waste_report_not_implemented():
    """Feature 18: a waste report must be created through the locations API."""
    pytest.fail(
        "Feature 18 TODO: implement/create client fixture and assert POST /reports"
    )
