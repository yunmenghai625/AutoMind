import type { Metadata } from "next";
import { PageHeader } from "@/components/common/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "项目声明",
  description: "AutoMind 个人作品集演示项目的归属、数据与使用边界。",
};

const sections = [
  {
    title: "项目归属",
    content:
      "Copyright © 2026 yunmenghai625。AutoMind 是个人独立开发的非商业作品集演示项目，用于技术展示与面试交流。项目中的原创源代码、文档及界面编排保留全部权利。",
  },
  {
    title: "非隶属声明",
    content:
      "本项目与任何同名企业、汽车制造商或第三方品牌不存在隶属、授权或合作关系。页面出现的第三方名称仅用于说明所采用的技术或服务，不代表其对本项目的认可。",
  },
  {
    title: "数据与第三方内容",
    content:
      "演示知识资料不代表任何汽车制造商的正式手册。开源组件、第三方服务、模型及数据分别受其各自许可证和服务条款约束，不属于本项目的独占权利范围。",
  },
  {
    title: "演示与安全边界",
    content:
      "部分功能由 AI 模型辅助。请勿上传人脸、车牌、证件、真实 VIN 或其他个人信息。生成及车辆诊断结果仅供演示参考，不能替代专业维修检查；涉及车辆安全时，应以车辆官方手册和专业人员意见为准。",
  },
];

export default function LegalPage() {
  return (
    <div className="container mx-auto max-w-4xl px-4 py-6">
      <PageHeader
        title="项目声明"
        description="个人作品集演示项目的归属、数据来源与使用边界。"
      />
      <div className="mt-6 grid gap-4">
        {sections.map((section) => (
          <Card key={section.title}>
            <CardHeader className="border-b py-3">
              <CardTitle className="text-base">{section.title}</CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              <p className="text-sm leading-7 text-muted-foreground">{section.content}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
