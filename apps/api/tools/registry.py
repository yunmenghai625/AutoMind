from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from apps.api.domain.safety.policy import AuthorizedToolCall
from apps.api.domain.vehicle.properties import VehicleProperty, VehicleZone
from apps.api.domain.vehicle.service import VehicleService
from apps.api.tools.schemas import (
    SetChargeArgs,
    SetDoorStateArgs,
    SetLightArgs,
    SetSeatHeatingArgs,
    SetTemperatureArgs,
    SetWindowArgs,
    ToolCallPlan,
    ToolCommand,
)

_TOOL_SCHEMAS: Mapping[str, type[BaseModel]] = {
    "set_temperature": SetTemperatureArgs,
    "set_seat_heating": SetSeatHeatingArgs,
    "set_window": SetWindowArgs,
    "set_door_state": SetDoorStateArgs,
    "set_light": SetLightArgs,
    "set_charge": SetChargeArgs,
}


class ToolRegistry:
    @property
    def schemas(self) -> Mapping[str, type[BaseModel]]:
        return _TOOL_SCHEMAS

    def validate(self, plan: ToolCallPlan) -> ToolCommand:
        schema = _TOOL_SCHEMAS.get(plan.name)
        if schema is None:
            raise ValueError(f"Tool is not allowlisted: {plan.name}")
        arguments = schema.model_validate(plan.arguments).model_dump()
        property_name, zone, value = _to_vehicle_property(plan.name, arguments)
        return ToolCommand(
            name=plan.name,
            arguments=arguments,
            property_name=property_name,
            zone=zone,
            value=value,
        )

    def model_tool_catalog(self) -> list[dict[str, Any]]:
        return [
            {"name": name, "arguments_schema": schema.model_json_schema()}
            for name, schema in _TOOL_SCHEMAS.items()
        ]


class ToolExecutor:
    def __init__(self, vehicle_service: VehicleService) -> None:
        self._vehicle_service = vehicle_service

    async def execute(
        self,
        authorized: AuthorizedToolCall,
        *,
        vehicle_id: Any,
        expected_version: int,
        request_id: str,
    ) -> Any:
        if not authorized.is_valid():
            raise PermissionError("Tool execution requires an approved SafetyPolicyEngine permit")
        command = authorized.command
        return await self._vehicle_service.set_property(
            vehicle_id,
            command.property_name,
            command.zone,
            command.value,
            expected_version=expected_version,
            request_id=request_id,
        )


def _to_vehicle_property(
    name: str, arguments: dict[str, Any]
) -> tuple[VehicleProperty, VehicleZone | None, bool | int | float | str]:
    if name == "set_temperature":
        zone = VehicleZone(arguments["zone"])
        prop = (
            VehicleProperty.DRIVER_TEMP
            if zone == VehicleZone.DRIVER
            else VehicleProperty.PASSENGER_TEMP
        )
        return prop, zone, arguments["temp_c"]
    if name == "set_seat_heating":
        return VehicleProperty.SEAT_HEAT, VehicleZone(arguments["zone"]), arguments["level"]
    if name == "set_window":
        return (
            VehicleProperty.WINDOW_POSITION,
            VehicleZone(arguments["zone"]),
            arguments["position"],
        )
    if name == "set_door_state":
        return VehicleProperty.DOOR_STATE, VehicleZone(arguments["zone"]), arguments["state"]
    if name == "set_light":
        return VehicleProperty.LIGHT_STATE, VehicleZone.GLOBAL, arguments["state"]
    if name == "set_charge":
        return VehicleProperty.CHARGE_STATUS, VehicleZone.GLOBAL, arguments["status"]
    raise ValueError(f"Unsupported tool: {name}")
