from unittest.mock import patch

import pytest
import requests

from notifications.telegram import TelegramError, send_message


@pytest.fixture(autouse=True)
def bot_token(settings):
    settings.TELEGRAM_BOT_TOKEN = "test-token"


@patch("notifications.telegram.requests.post")
def test_send_message_success(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"ok": True, "result": {"message_id": 1}}

    payload = send_message(123, "hello")

    assert payload["ok"] is True
    assert mock_post.call_args.args[0] == ("https://api.telegram.org/bottest-token/sendMessage")
    assert mock_post.call_args.kwargs["json"] == {"chat_id": 123, "text": "hello"}


@patch("notifications.telegram.requests.post")
def test_send_message_with_http_error(mock_post):
    mock_post.return_value.status_code = 400
    mock_post.return_value.text = "bad request"

    with pytest.raises(TelegramError):
        send_message(123, "hello")


@patch("notifications.telegram.requests.post")
def test_send_message_with_api_error(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "ok": False,
        "description": "chat not found",
    }

    with pytest.raises(TelegramError):
        send_message(123, "hello")


@patch("notifications.telegram.requests.post")
def test_send_message_with_invalid_json(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.side_effect = ValueError("not json")

    with pytest.raises(TelegramError):
        send_message(123, "hello")


@patch("notifications.telegram.requests.post")
def test_send_message_with_connection_error(mock_post):
    mock_post.side_effect = requests.ConnectionError("boom")

    with pytest.raises(TelegramError):
        send_message(123, "hello")


def test_send_message_without_token(settings):
    settings.TELEGRAM_BOT_TOKEN = ""

    with pytest.raises(TelegramError):
        send_message(123, "hello")
