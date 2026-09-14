import type { DiagnosisResult } from "@/types/diagnosis";

export function mockDiagnosis(imageName: string): DiagnosisResult {
  void imageName;
  return {
    detected: [
      {
        code: "P0420",
        label: "发动机故障警告（催化系统）",
        confidence: 93,
        risk: "Medium",
      },
    ],
    causes: [
      {
        title: "氧传感器性能衰减",
        detail:
          "氧传感器老化可能误报催化器效率不足，并触发 P0420 故障码。",
      },
      {
        title: "三元催化器效率低于阈值",
        detail:
          "排气流动受阻或催化器污染会降低转化效率。",
      },
      {
        title: "排气系统泄漏",
        detail:
          "传感器上游的轻微泄漏可能导致读数偏差并触发故障码。",
      },
    ],
    recommendations: [
      {
        title: "前往服务中心读取故障码",
        detail:
          "建议进行完整 OBD-II 扫描，以确认 P0420 并检查冻结帧数据。",
      },
      {
        title: "检查氧传感器",
        detail:
          "通过实时数据确认传感器响应，完成诊断后再决定是否更换部件。",
      },
      {
        title: "检查排气系统是否泄漏",
        detail:
          "检查排气歧管和密封垫是否存在明显损伤或烟灰痕迹。",
      },
    ],
    references: [
      {
        source: "车辆保养指南",
        chapter: "排放系统",
        page: 88,
        snippet:
          "更换任何部件前，应通过完整扫描确认催化器效率相关故障码。",
      },
      {
        source: "仪表警告灯指南",
        chapter: "发动机故障灯",
        page: 21,
        snippet:
          "发动机故障灯常亮通常表示非紧急故障，车辆一般可谨慎行驶至服务点。",
      },
    ],
    pipeline: [
      "图像输入",
      "视觉模型",
      "警告识别",
      "知识检索",
      "诊断输出",
    ],
    processedAt: new Date().toISOString(),
  };
}
