# AutoMind Phase 3.5 AIGC Cockpit Theme 架构

## 目标与边界

Phase 3.5 在不重构 Phase 0–3 的前提下，增加低成本座舱主题生成。生成是 Proposal，不能修改
VehicleState；只有用户显式确认的 Apply 才进入确定性的 Safety Gate 和 Vehicle Tools。图片
失败或预算不足只影响壁纸，不影响主题参数、Cockpit、RAG 或 Vehicle API。

## 工作流

```text
用户描述
  -> Guest/Registered 日配额原子预占
  -> prompt_hash 缓存
  -> 可选 Automotive RAG Grounding
  -> ThemeGenerator -> 严格 ThemeSpec
  -> Image Budget Guard
  -> ImageGenerationProvider -> Asset Store
  -> Preview（无 VehicleState/Tool 写入）

用户确认 Apply
  -> ThemeSpec 再校验
  -> ToolRegistry -> SafetyPolicyEngine
  -> ToolExecutor -> VehicleService/HAL
  -> Vehicle audit + Agent run/step/tool audit
```

## 领域与 Provider

- `ThemeSpec` 禁止额外字段，并约束十六进制环境色、0–100 亮度、显示模式、16–30°C 温度和
  壁纸提示词长度。
- `LocalThemeGenerator` 是确定性离线默认；`OpenAICompatibleThemeGenerator` 支持 JSON
  structured output。模型 JSON 校验失败只允许修复一次，仍失败返回 `INVALID_THEME_SPEC`。
- `ImageGenerationProvider` 与文本模型解耦；实现 OpenAI-compatible 真实图片 API 和 Mock。
- 本地存储用于开发，`S3ThemeAssetStore` 支持 R2/S3-compatible 对象存储。

## 数据、缓存与成本

- `aigc_generations` 记录 prompt、provider/model、图片 provider/model、状态、总成本、独立
  图片成本、延迟、缓存/重生成和降级原因。
- `cockpit_themes` 只保存已通过校验的 ThemeSpec、壁纸 URL、prompt hash 和应用次数。
- `usage_daily` 通过 `(date, subject_key)` 原子计数；Guest 默认 1 次/日，Registered 默认
  3 次/日，Phase 5 可把认证用户注入 `UsageSubject`。
- 月图片预算默认 5 元；达到 80% 使用 Mock 默认背景，达到 100% 停止外部图片调用。
- prompt hash 绑定规范化 prompt、车辆和两个 provider/model；缓存仍计入日请求，但不新增成本。

## API 与前端

- `POST /api/v1/aigc/themes`：输出 ThemeSpec、wallpaper URL 和生成 metadata。
- `POST /api/v1/aigc/themes/{id}/apply`：必须提交 `confirmed: true` 与 `expected_version`。
- `GET /api/v1/aigc/metrics`：输出成功率、平均延迟、成本、应用率和重生成率。
- `/cockpit` 只增加 AI Theme Dialog。Preview 展示壁纸、环境色、亮度、模式、音乐和温度；
  Apply 成功后才改变背景并刷新共享 Vehicle Store。

