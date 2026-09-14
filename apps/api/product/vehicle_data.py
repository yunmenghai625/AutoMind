import asyncio
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx

from apps.api.core.resilience import CircuitBreaker, CircuitOpenError


class VehicleDataProviderError(RuntimeError):
    pass


class VehicleDataProvider(Protocol):
    name: str

    async def decode_vin(self, vin: str, model_year: int | None) -> dict[str, Any]: ...

    async def recalls(self, *, make: str, model: str, year: int) -> list[dict[str, Any]]: ...


class DisabledVehicleDataProvider:
    name = "disabled"

    async def decode_vin(self, vin: str, model_year: int | None) -> dict[str, Any]:
        del vin, model_year
        raise VehicleDataProviderError("Vehicle data provider is disabled")

    async def recalls(self, *, make: str, model: str, year: int) -> list[dict[str, Any]]:
        del make, model, year
        raise VehicleDataProviderError("Vehicle data provider is disabled")


class NhtsaVehicleDataProvider:
    name = "NHTSA"

    def __init__(
        self, *, vehicle_base_url: str, recall_base_url: str, timeout_seconds: float
    ) -> None:
        self._vehicle_base_url = vehicle_base_url.rstrip("/")
        self._recall_base_url = recall_base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 5))
        self._circuit = CircuitBreaker(failure_threshold=3, recovery_seconds=30)

    async def decode_vin(self, vin: str, model_year: int | None) -> dict[str, Any]:
        body = await self._get(
            f"{self._vehicle_base_url}/vehicles/DecodeVinValues/{vin}",
            params={"format": "json", "modelyear": model_year or ""},
        )
        rows = body.get("Results")
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            raise VehicleDataProviderError("VIN provider returned no normalized result")
        row = rows[0]
        error_code = str(row.get("ErrorCode") or "")
        if error_code and error_code != "0":
            raise VehicleDataProviderError("VIN could not be decoded")
        return {
            "make": _text(row.get("Make")),
            "model": _text(row.get("Model")),
            "model_year": _integer(row.get("ModelYear")),
            "vehicle_type": _text(row.get("VehicleType")),
            "fuel_type": _text(row.get("FuelTypePrimary")),
        }

    async def recalls(self, *, make: str, model: str, year: int) -> list[dict[str, Any]]:
        body = await self._get(
            f"{self._recall_base_url}/recalls/recallsByVehicle",
            params={"make": make, "model": model, "modelYear": year},
        )
        rows = body.get("results") or body.get("Results") or []
        if not isinstance(rows, list):
            raise VehicleDataProviderError("Recall provider returned invalid data")
        normalized: list[dict[str, Any]] = []
        for row in rows[:100]:
            if not isinstance(row, dict):
                continue
            component = _text(row.get("Component")) or "Unspecified component"
            summary = _text(row.get("Summary")) or "Recall summary unavailable"
            consequence = _text(row.get("Consequence"))
            remedy = _text(row.get("Remedy")) or "Contact an authorized service center."
            external_id = _text(row.get("NHTSACampaignNumber"))
            if not external_id:
                continue
            normalized.append(
                {
                    "external_id": external_id,
                    "component": component,
                    "summary": summary,
                    "consequence": consequence,
                    "recommended_action": remedy,
                    "risk": _recall_risk(component, consequence or summary),
                    "source": self.name,
                    "issued_at": _date(row.get("ReportReceivedDate")),
                    "metadata_json": {
                        "manufacturer": _text(row.get("Manufacturer")),
                        "park_outside": _text(row.get("parkItOutside")),
                        "do_not_drive": _text(row.get("doNotDrive")),
                    },
                }
            )
        return normalized

    async def _get(self, url: str, *, params: dict[str, Any]) -> dict[str, Any]:
        try:
            return await self._circuit.call(lambda: self._get_with_retry(url, params=params))
        except CircuitOpenError as exc:
            raise VehicleDataProviderError("External vehicle data circuit is open") from exc

    async def _get_with_retry(self, url: str, *, params: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(url, params=params)
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict):
                    raise ValueError("response root must be an object")
                return body
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt == 0:
                    await asyncio.sleep(0.15)
        raise VehicleDataProviderError("External vehicle data is unavailable") from last_error


def _text(value: Any) -> str | None:
    normalized = str(value).strip() if value is not None else ""
    return normalized[:2000] or None


def _integer(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _date(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    for pattern in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:10], pattern).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _recall_risk(component: str, detail: str) -> str:
    text = f"{component} {detail}".lower()
    critical = ("fire", "crash", "injury", "brake", "steering", "燃烧", "制动", "转向")
    return "High" if any(term in text for term in critical) else "Medium"
