def test_chat_response_matches_frontend_contract(client) -> None:
    response = client.post("/api/v1/chat", json={"message": "我妈有点冷"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["messages"][0]["role"] == "assistant"
    assert payload["messages"][0]["tools"][0]["status"] == "SUCCESS"
    assert payload["messages"][0]["meta"]["llmCalls"] == 0
    assert payload["vehicle"]["passengerTemperature"] == 25
    assert payload["vehicle"]["passengerSeatHeat"] == 1


def test_unsafe_chat_is_safety_warning(client) -> None:
    response = client.post("/api/v1/chat", json={"message": "120km/h开门"})

    assert response.status_code == 200
    message = response.json()["messages"][0]
    assert message["kind"] == "safety_warning"
    assert message["meta"]["blocked"] is True
    assert message["tools"][0]["status"] == "BLOCKED"


def test_chat_stream_emits_sse_events(client) -> None:
    response = client.get("/api/v1/chat/stream", params={"message": "电量还有多少"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: started" in response.text
    assert "event: message" in response.text
    assert "event: vehicle" in response.text
    assert "event: done" in response.text


def test_vehicle_snapshot_maps_headlight_to_frontend_enum(client) -> None:
    response = client.post("/api/v1/chat", json={"message": "打开近光灯"})

    assert response.status_code == 200
    assert response.json()["vehicle"]["headlight"] == "ON"
