from time import perf_counter

from apps.api.diagnosis.providers.base import VlmAnalysisResult
from apps.api.diagnosis.schemas import VlmStructuredOutput, WarningDetection


class LocalHeuristicVlmProvider:
    name = "local"
    model = "automind-vision-local-v1"
    is_external = False

    async def analyze(
        self, *, image: bytes, mime_type: str, filename: str, context: str | None
    ) -> VlmAnalysisResult:
        del image, mime_type
        started = perf_counter()
        hint = f"{filename} {context or ''}".lower()
        if any(token in hint for token in ("tpms", "tire", "胎压")):
            detection = WarningDetection(
                warning_type="tire_pressure",
                warning_code="TPMS",
                label="胎压监测警告灯",
                confidence=0.92,
                visible_evidence=["文件上下文指向胎压警告灯", "图像已通过仪表盘图片校验"],
                uncertainty="本地离线识别仅用于开发验收，仍需检查四轮胎压确认。",
            )
        elif any(token in hint for token in ("brake", "制动", "刹车")):
            detection = WarningDetection(
                warning_type="brake_system",
                warning_code="BRAKE",
                label="制动系统警告灯",
                confidence=0.9,
                visible_evidence=["文件上下文指向制动系统警告", "图像已通过仪表盘图片校验"],
                uncertainty="无法从单张图片判断制动液、传感器或机械部件的具体故障。",
            )
        elif any(token in hint for token in ("engine", "p0420", "发动机")):
            detection = WarningDetection(
                warning_type="check_engine",
                warning_code="CHECK_ENGINE",
                label="发动机故障指示灯",
                confidence=0.88,
                visible_evidence=["文件上下文指向发动机故障灯", "图像已通过仪表盘图片校验"],
                uncertainty="图片不能给出具体 OBD 故障码或确定损坏部件。",
            )
        else:
            detection = WarningDetection(
                warning_type="unknown",
                warning_code=None,
                label="未能可靠识别的仪表指示",
                confidence=0.35,
                visible_evidence=["图片有效，但缺少可确认的警告灯特征"],
                uncertainty="请重新拍摄清晰近照，或同时提供仪表文字与 OBD 故障码。",
            )
        return VlmAnalysisResult(
            output=VlmStructuredOutput(detections=[detection]),
            provider=self.name,
            model=self.model,
            input_tokens=0,
            output_tokens=0,
            latency_ms=round((perf_counter() - started) * 1000),
            cost_est_cny=0,
        )
