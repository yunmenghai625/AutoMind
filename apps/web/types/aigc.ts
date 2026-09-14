export interface ThemeSpec {
  name: string;
  ambient_color: string;
  ambient_brightness: number;
  display_mode: "comfort" | "night" | "minimal" | "focus";
  music_style: string;
  temperature: number;
  wallpaper_prompt: string;
}

export interface ThemeMetadata {
  generation_id: string;
  provider: string;
  model: string;
  image_provider: string | null;
  image_model: string | null;
  latency_ms: number;
  cost_est_cny: number;
  image_cost_est_cny: number;
  status: string;
  cached: boolean;
  degraded_reason: string | null;
  quota_used: number;
  quota_limit: number;
  budget_state: "normal" | "economy" | "exhausted";
}

export interface CockpitTheme {
  request_id: string;
  theme_id: string;
  theme_spec: ThemeSpec;
  wallpaper_url: string | null;
  metadata: ThemeMetadata;
}

export interface AppliedCockpitTheme {
  request_id: string;
  theme_id: string;
  applied: boolean;
  theme_spec: ThemeSpec;
  wallpaper_url: string | null;
  vehicle_state_version: number;
  agent_run_id: string;
}
