import type { DiagnosisResult } from "@/types/diagnosis";

export function mockDiagnosis(imageName: string): DiagnosisResult {
  void imageName;
  return {
    detected: [
      {
        code: "P0420",
        label: "Check Engine Warning (Catalyst System)",
        confidence: 93,
        risk: "Medium",
      },
    ],
    causes: [
      {
        title: "Oxygen sensor degradation",
        detail:
          "Aging O2 sensor can report inefficient catalyst operation and trigger P0420.",
      },
      {
        title: "Catalytic converter efficiency below threshold",
        detail:
          "Exhaust flow restriction or contamination reduces converter efficiency.",
      },
      {
        title: "Exhaust system leak",
        detail:
          "A small leak upstream of the sensor can skew the readings and set the code.",
      },
    ],
    recommendations: [
      {
        title: "Check engine codes at service center",
        detail:
          "Have a full OBD-II scan performed to confirm P0420 and check freeze frame data.",
      },
      {
        title: "Inspect O2 sensors",
        detail:
          "Verify sensor response with live data; replace components only after diagnosis.",
      },
      {
        title: "Inspect exhaust for leaks",
        detail:
          "Inspect the exhaust manifold and gasket for visible damage or soot marks.",
      },
    ],
    references: [
      {
        source: "Maintenance Guide",
        chapter: "Emission System",
        page: 88,
        snippet:
          "Catalyst efficiency codes should be confirmed with a full scan before any part replacement.",
      },
      {
        source: "Warning Light Guide",
        chapter: "Check Engine",
        page: 21,
        snippet:
          "A steady check engine light indicates a non-immediate fault; the car can usually be driven to a service point.",
      },
    ],
    pipeline: [
      "Image",
      "Vision Model",
      "Warning Detection",
      "Knowledge Retrieval",
      "Diagnosis",
    ],
    processedAt: new Date().toISOString(),
  };
}
