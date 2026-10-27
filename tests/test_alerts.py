from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.alerts import build_weather_alerts, send_telegram_message


def _day(rain=0.0, t_min=10.0, t_max=20.0, city="Cordoba") -> dict:
    return {
        "city_name": city,
        "date_local": date(2026, 10, 28),
        "temp_min_c": t_min,
        "temp_max_c": t_max,
        "precipitation_total_mm": rain,
    }


def test_normal_day_has_no_alerts():
    assert build_weather_alerts([_day()]) == []


@pytest.mark.parametrize(
    ("day", "keyword"),
    [
        (_day(rain=20.0), "Lluvia intensa"),
        (_day(t_max=35.0), "Calor extremo"),
        (_day(t_min=0.0), "Helada"),
    ],
)
def test_thresholds_are_inclusive(day, keyword):
    alerts = build_weather_alerts([day])

    assert len(alerts) == 1
    assert keyword in alerts[0]
    assert "Cordoba (28/10)" in alerts[0]


def test_one_day_can_trigger_several_alerts():
    assert len(build_weather_alerts([_day(rain=45.0, t_max=38.0)])) == 2


def test_missing_values_are_ignored():
    assert build_weather_alerts([_day(rain=None, t_min=None, t_max=None)]) == []


def test_send_without_credentials_does_not_call_api(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with patch("src.alerts.requests.post") as post:
        assert send_telegram_message("hola") is False
    post.assert_not_called()


def test_send_posts_to_telegram(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")

    with patch("src.alerts.requests.post", return_value=MagicMock()) as post:
        assert send_telegram_message("hola") is True

    args, kwargs = post.call_args
    assert args[0] == "https://api.telegram.org/bot123:abc/sendMessage"
    assert kwargs["json"] == {"chat_id": "42", "text": "hola"}
