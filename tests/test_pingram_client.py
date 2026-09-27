"""Tests for the Pingram email client wrapper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from solis_energy_manager.clients.pingram_client import send_email

MODULE = "solis_energy_manager.clients.pingram_client"  # adjust to the real path


@pytest.fixture
def anyio_backend():
    """Run async tests against asyncio only, not every anyio backend."""
    return "asyncio"


@pytest.fixture
def settings():
    """A settings stub exposing only what send_email actually reads."""
    stub = MagicMock()
    stub.pingram_api_key.get_secret_value.return_value = "test-api-key"
    stub.pingram_api_url = "https://api.pingram.io"
    stub.destination_email.get_secret_value.return_value = "me@example.com"
    stub.from_name = "Solis Energy Manager"
    return stub


@pytest.fixture
def mock_pingram_client():
    """The object yielded by `async with Pingram(...) as client`."""
    client = MagicMock()
    client.email.email_send = AsyncMock()
    return client


@pytest.fixture
def mock_pingram_cls(mock_pingram_client):
    """Patch Pingram so entering the `async with` block yields mock_pingram_client."""
    with patch(f"{MODULE}.Pingram") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_pingram_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock_cls


@pytest.mark.anyio
async def test_send_email_constructs_client_with_settings_credentials(
    settings, mock_pingram_cls
):
    """Test that the Pingram client is built from the settings' API key and URL."""
    await send_email(settings, subject="Charge tonight?", html_content="<p>Yes</p>")

    mock_pingram_cls.assert_called_once_with(
        api_key="test-api-key",
        base_url="https://api.pingram.io",
    )


@pytest.mark.anyio
async def test_send_email_sends_expected_request(
    settings, mock_pingram_cls, mock_pingram_client
):
    """Test that email_send is called with the expected request fields."""
    await send_email(settings, subject="Charge tonight?", html_content="<p>Yes</p>")

    mock_pingram_client.email.email_send.assert_awaited_once()
    request = mock_pingram_client.email.email_send.await_args.args[0]

    assert request.type == "email_compose_preview"
    assert request.to == "me@example.com"
    assert request.subject == "Charge tonight?"
    assert request.html == "<p>Yes</p>"
    assert request.from_name == "Solis Energy Manager"
    assert request.from_address == "noreply@pingram.io"


@pytest.mark.anyio
async def test_send_email_closes_client_on_success(settings, mock_pingram_cls):
    """Test that the Pingram client's async context manager is entered and exited."""
    await send_email(settings, subject="s", html_content="h")

    mock_pingram_cls.return_value.__aenter__.assert_awaited_once()
    mock_pingram_cls.return_value.__aexit__.assert_awaited_once()


@pytest.mark.anyio
async def test_send_email_propagates_failure_and_still_closes_client(
    settings, mock_pingram_cls, mock_pingram_client
):
    """Test that a failed send is not swallowed, and the client is still exited."""
    mock_pingram_client.email.email_send.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await send_email(settings, subject="s", html_content="h")

    mock_pingram_cls.return_value.__aexit__.assert_awaited_once()
