from apps.api.diagnosis.schemas import RiskLevel, WarningDetection

_CRITICAL_TYPES = {"brake_system", "oil_pressure", "battery", "temperature"}
_WARNING_TYPES = {"tire_pressure", "check_engine", "airbag", "abs"}


def classify_risk(detection: WarningDetection, *, low_confidence: bool) -> RiskLevel:
    if low_confidence or detection.warning_type == "unknown":
        return "Information"
    if detection.warning_type in _CRITICAL_TYPES:
        return "Critical"
    if detection.warning_type in _WARNING_TYPES:
        return "Warning"
    return "Information"


def recommended_action(risk: RiskLevel) -> tuple[str, str]:
    if risk == "Critical":
        return (
            "尽快安全停车并寻求专业检查",
            "在确保交通安全的前提下靠边停车；如伴随制动、异味、过热或动力异常，请联系救援。",
        )
    if risk == "Warning":
        return (
            "降低驾驶负荷并安排检查",
            "留意车辆是否出现异常，并尽快检查车辆手册、胎压或读取 OBD 故障码。",
        )
    return (
        "补充清晰图片或故障码",
        "当前证据不足，请拍摄警告灯近照并提供仪表文字或 OBD 码，不要仅凭本结果更换零件。",
    )
