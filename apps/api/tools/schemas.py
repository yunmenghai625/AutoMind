from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.api.domain.vehicle.properties import VehicleProperty, VehicleZone


class StrictToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SetTemperatureArgs(StrictToolArguments):
    zone: Literal["driver", "passenger"]
    temp_c: float = Field(ge=16, le=30)


class SetSeatHeatingArgs(StrictToolArguments):
    zone: Literal["driver", "passenger"]
    level: int = Field(ge=0, le=3)


class SetWindowArgs(StrictToolArguments):
    zone: Literal["driver", "passenger"]
    position: Literal[0, 25, 50, 75, 100]


class SetDoorStateArgs(StrictToolArguments):
    zone: Literal["driver", "passenger"]
    state: Literal["OPEN", "CLOSED"]


class SetLightArgs(StrictToolArguments):
    state: Literal["OFF", "PARKING", "LOW_BEAM", "HIGH_BEAM"]


class SetChargeArgs(StrictToolArguments):
    status: Literal["IDLE", "CHARGING"]


class ToolCallPlan(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any]


class ToolCommand(BaseModel):
    name: str
    arguments: dict[str, Any]
    property_name: VehicleProperty
    zone: VehicleZone | None
    value: bool | int | float | str


class ModelPlan(BaseModel):
    intent: Literal["cockpit_control", "vehicle_info", "unsupported"]
    reply: str = Field(max_length=500)
    tool_calls: list[ToolCallPlan] = Field(default_factory=list, max_length=4)
