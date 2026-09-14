from apps.api.aigc.schemas import ThemeSpec


def build_theme_prompt(user_prompt: str, grounding: list[str] | None = None) -> str:
    schema = ThemeSpec.model_json_schema()
    context = grounding or []
    return (
        "请把用户的座舱氛围需求转换为严格的 ThemeSpec JSON。"
        "壁纸适合车载横屏，不包含文字、品牌标志、人物正脸或驾驶干扰元素。"
        f"\n用户需求：{user_prompt.strip()}"
        f"\n可选车辆知识上下文：{context[:3]}"
        f"\nJSON Schema：{schema}"
    )
