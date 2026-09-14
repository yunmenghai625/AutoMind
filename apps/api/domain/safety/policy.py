from dataclasses import dataclass

from apps.api.domain.vehicle.entities import VehicleStateData
from apps.api.domain.vehicle.properties import VehicleProperty
from apps.api.tools.schemas import ToolCommand

_SAFETY_PERMIT = object()


@dataclass(frozen=True, slots=True)
class SafetyDecision:
    approved: bool
    code: str
    reason: str


@dataclass(frozen=True, slots=True)
class AuthorizedToolCall:
    command: ToolCommand
    decision: SafetyDecision
    _permit: object

    def is_valid(self) -> bool:
        return self.decision.approved and self._permit is _SAFETY_PERMIT


class SafetyPolicyEngine:
    """Deterministic safety boundary. It does not call or trust an LLM."""

    def evaluate(
        self,
        command: ToolCommand,
        state: VehicleStateData,
        *,
        observed_speed_kph: float | None = None,
    ) -> SafetyDecision:
        effective_speed = max(state.speed_kph, observed_speed_kph or 0)

        if command.property_name == VehicleProperty.DOOR_STATE and command.value == "OPEN":
            if effective_speed > 0:
                return SafetyDecision(
                    False,
                    "DOOR_OPEN_WHILE_MOVING",
                    f"车辆速度为 {effective_speed:g} km/h，禁止打开车门。",
                )
            if state.gear != "P":
                return SafetyDecision(
                    False,
                    "DOOR_OPEN_GEAR_NOT_P",
                    "车辆未处于 P 挡，禁止打开车门。",
                )

        if (
            command.property_name == VehicleProperty.CHARGE_STATUS
            and command.value == "CHARGING"
            and state.gear != "P"
        ):
            return SafetyDecision(
                False,
                "CHARGE_GEAR_NOT_P",
                "车辆未处于 P 挡，禁止开始充电。",
            )

        if command.property_name == VehicleProperty.GEAR and state.speed_kph > 0:
            return SafetyDecision(
                False,
                "GEAR_CHANGE_WHILE_MOVING",
                "车辆行驶中禁止通过智能助手切换挡位。",
            )

        return SafetyDecision(True, "APPROVED", "安全规则校验通过。")

    def authorize(
        self,
        command: ToolCommand,
        state: VehicleStateData,
        *,
        observed_speed_kph: float | None = None,
    ) -> AuthorizedToolCall | SafetyDecision:
        decision = self.evaluate(command, state, observed_speed_kph=observed_speed_kph)
        if not decision.approved:
            return decision
        return AuthorizedToolCall(command, decision, _SAFETY_PERMIT)
