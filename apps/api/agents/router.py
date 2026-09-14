import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RouteResult:
    route: str
    intent: str
    calls: list[dict[str, Any]] = field(default_factory=list)
    reply_hint: str = ""
    observed_speed_kph: float | None = None


class CheapRouter:
    """High-precision rules first; uncertain requests are delegated once to the model."""

    def route(self, text: str) -> RouteResult:
        normalized = re.sub(r"\s+", "", text).lower()
        speed = _extract_speed(normalized)

        if any(word in normalized for word in ("电量", "续航", "还能开", "剩余里程")):
            return RouteResult("vehicle_info", "vehicle_info")

        if "冷" in normalized:
            passenger = any(word in normalized for word in ("我妈", "妈妈", "副驾", "乘客"))
            zone = "passenger" if passenger else "driver"
            target = 25 if passenger else 24
            return RouteResult(
                "rule",
                "cockpit_control",
                [
                    {"name": "set_temperature", "arguments": {"zone": zone, "temp_c": target}},
                    {"name": "set_seat_heating", "arguments": {"zone": zone, "level": 1}},
                ],
                "passenger_warm" if passenger else "driver_warm",
                speed,
            )

        temperature = re.search(r"(?:温度|空调).*?(1[6-9]|2\d|30)(?:度|℃)?", normalized)
        if temperature:
            zone = "passenger" if any(w in normalized for w in ("副驾", "乘客")) else "driver"
            return RouteResult(
                "rule",
                "cockpit_control",
                [
                    {
                        "name": "set_temperature",
                        "arguments": {"zone": zone, "temp_c": float(temperature.group(1))},
                    }
                ],
                "temperature",
                speed,
            )

        if any(word in normalized for word in ("开门", "打开车门", "车门打开")):
            zone = (
                "passenger" if any(w in normalized for w in ("副驾", "右边", "乘客")) else "driver"
            )
            return RouteResult(
                "rule",
                "cockpit_control",
                [{"name": "set_door_state", "arguments": {"zone": zone, "state": "OPEN"}}],
                "door_open",
                speed,
            )

        if any(word in normalized for word in ("关门", "关闭车门")):
            zone = (
                "passenger" if any(w in normalized for w in ("副驾", "右边", "乘客")) else "driver"
            )
            return RouteResult(
                "rule",
                "cockpit_control",
                [{"name": "set_door_state", "arguments": {"zone": zone, "state": "CLOSED"}}],
                "door_close",
                speed,
            )

        if "车窗" in normalized:
            zone = (
                "passenger" if any(w in normalized for w in ("副驾", "右边", "乘客")) else "driver"
            )
            if any(w in normalized for w in ("关闭", "关上", "升起", "关窗")):
                position = 0.0
            elif any(w in normalized for w in ("打开", "降下", "开窗")):
                position = 100.0
            else:
                return RouteResult("model", "ambiguous")
            return RouteResult(
                "rule",
                "cockpit_control",
                [{"name": "set_window", "arguments": {"zone": zone, "position": position}}],
                "window",
                speed,
            )

        if any(word in normalized for word in ("打开近光灯", "开近光灯", "近光灯")):
            return RouteResult(
                "rule",
                "cockpit_control",
                [{"name": "set_light", "arguments": {"state": "LOW_BEAM"}}],
                "light",
                speed,
            )
        if any(word in normalized for word in ("关灯", "关闭车灯")):
            return RouteResult(
                "rule",
                "cockpit_control",
                [{"name": "set_light", "arguments": {"state": "OFF"}}],
                "light",
                speed,
            )

        if any(word in normalized for word in ("开始充电", "充电开始")):
            return RouteResult(
                "rule",
                "cockpit_control",
                [{"name": "set_charge", "arguments": {"status": "CHARGING"}}],
                "charge",
                speed,
            )
        if any(word in normalized for word in ("停止充电", "结束充电")):
            return RouteResult(
                "rule",
                "cockpit_control",
                [{"name": "set_charge", "arguments": {"status": "IDLE"}}],
                "charge",
                speed,
            )

        return RouteResult("model", "ambiguous")


def _extract_speed(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:km/?h|公里(?:每小时)?|迈)", text)
    return float(match.group(1)) if match else None
