from apps.api.agents.router import CheapRouter


def test_driver_cold_is_deterministic() -> None:
    result = CheapRouter().route("我有点冷")

    assert result.route == "rule"
    assert [call["name"] for call in result.calls] == [
        "set_temperature",
        "set_seat_heating",
    ]
    assert result.calls[0]["arguments"]["zone"] == "driver"


def test_mother_cold_maps_to_front_passenger() -> None:
    result = CheapRouter().route("我妈有点冷")

    assert result.route == "rule"
    assert all(call["arguments"]["zone"] == "passenger" for call in result.calls)
    assert result.calls[0]["arguments"]["temp_c"] == 25


def test_speed_is_preserved_for_safety_context() -> None:
    result = CheapRouter().route("120km/h开门")

    assert result.route == "rule"
    assert result.observed_speed_kph == 120
    assert result.calls[0]["name"] == "set_door_state"
