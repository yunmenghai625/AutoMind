# AutoMind Phase 4 Multimodal Diagnosis 架构

## 目标与边界

Phase 4 接收仪表盘或警告灯图片，输出可审计的结构化识别、风险级别、知识库解释、引用和
下一步建议。VLM 只识别可见证据，不给出确定维修结论，也不能修改 VehicleState 或调用车控工具。

## 工作流

```text
JPEG / PNG / WebP + 可选文字
  -> MIME、文件大小、像素上限 Guard
  -> EXIF 方向归一、RGB 转换、尺寸压缩、JPEG 重编码净化
  -> Local 或 R2/S3-compatible Object Storage
  -> VLM strict structured detection
       warning_type / confidence / visible_evidence / uncertainty
  -> Confidence Gate
       低于 0.70：无法可靠识别，提示重拍或提供 OBD 码
       达标：按警告类型进入 Knowledge Agent 检索
  -> Information / Warning / Critical 确定性风险分级
  -> 保守措辞 + 引用 + 下一步建议
  -> Agent trace + diagnosis_records + usage_daily
```

## 图片安全与存储

- 声明 MIME 必须与 Pillow 解析出的实际格式一致，仅允许 JPEG、PNG、WebP。
- 上传默认不超过 5 MiB、1200 万像素；压缩后最长边不超过 1600 px。
- 服务仅把重新编码后的 JPEG 衍生图送入存储，不保存原始上传字节，避免长期保留原图及附加元数据。
- `LocalStorageProvider` 用于开发；`S3CompatibleStorageProvider` 支持 Cloudflare R2 和 S3。
- `image_expires_at` 默认 14 天，可在任务书要求的 7–30 天内配置；生产 R2 应配置对应生命周期。

## VLM、置信度与降级

- `VlmStructuredOutput` 禁止额外字段，检测项必须包含警告类型、0–1 置信度、可见证据和不确定性。
- 外部 OpenAI-compatible VLM 设超时，非法 JSON 最多修复一次；失败后降级到本地 Provider。
- 默认本地 Provider 用于无外部费用的开发验收；无法取得可靠特征时固定输出低置信度 unknown。
- 达到月 AI 预算后不再调用外部 VLM，自动切换本地降级，并在记录中保存请求/实际 Provider。

## 数据与配额

- `diagnosis_records` 保存用户主体、车辆、图片 URL/哈希/到期时间、结构化识别、风险、答复、
  引用、请求/实际 provider/model、状态、延迟、成本和错误码。
- `usage_daily.diagnosis_requests` 与 AIGC 主题额度分开原子计数；Guest 默认 1 次/日，
  Registered 默认 5 次/日。
- 无效图片在配额预占之前被拒绝；每个有效调用均生成 Agent run、六个节点步骤和成本/延迟记录。

## API 与前端

- `POST /api/v1/diagnosis` 使用 multipart form：`file` 必填、`description` 可选。
- `GET /api/v1/diagnosis/assets/{filename}` 只服务本地开发目录中的安全文件名。
- Mavis 现有 `/diagnosis` 页面只替换 API 服务层和 File 状态，未更改页面布局或设计系统。
