/** Diagnosis (multimodal fault diagnosis) domain types.
 * Mirror of future POST /api/v1/diagnosis contract.
 */

export type DiagnosisStatus = "idle" | "loading" | "success" | "error";

export type RiskLevel = "Low" | "Medium" | "High";

export interface DetectedWarning {
  code: string;
  label: string;
  confidence: number; // 0-100
  risk: RiskLevel;
}

export interface DiagnosisCause {
  title: string;
  detail: string;
}

export interface DiagnosisRecommendation {
  title: string;
  detail: string;
}

export interface KnowledgeReference {
  source: string;
  chapter?: string;
  page?: number;
  snippet: string;
}

export interface DiagnosisResult {
  request_id?: string;
  detected: DetectedWarning[];
  causes: DiagnosisCause[];
  recommendations: DiagnosisRecommendation[];
  references: KnowledgeReference[];
  pipeline: string[];
  processedAt: string;
  message?: string;
  metadata?: {
    diagnosis_id: string;
    run_id: string;
    provider: string;
    model: string;
    latency_ms: number;
    cost_est_cny: number;
    status: string;
    low_confidence: boolean;
    quota_used: number;
    quota_limit: number;
    image_expires_at: string;
  };
}

export interface DiagnosisState {
  status: DiagnosisStatus;
  imagePreview?: string;
  result?: DiagnosisResult;
  error?: string;
}
