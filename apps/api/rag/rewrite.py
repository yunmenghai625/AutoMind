class RuleBasedQueryRewriter:
    _EXPANSIONS = {
        "胎压": "TPMS 轮胎气压 报警灯 推荐胎压 安全驾驶",
        "充电": "动力电池 充电状态 充电安全 续航",
        "快充": "直流快充 高电量 降低充电功率",
        "电池": "动力电池 电量 续航 电池保养",
        "电动车": "电动汽车 动力电池 充电 续航",
        "续航": "电池电量 低温续航 行程规划",
        "冬季": "低温 电池预热 续航余量",
        "停放": "长期停放 电量 持续耗电",
        "长期": "长期停放 电池存放 电量",
        "保养": "车辆维护 保养周期 检查项目",
        "刹车": "制动系统 制动警告灯 安全停车",
        "制动": "制动系统 制动警告灯 安全停车",
        "车道": "车道保持 LKA 驾驶辅助",
        "自适应巡航": "ACC 自适应巡航 驾驶辅助",
        "雨刮": "雨刮器 刮水器 更换维护",
    }

    def rewrite(self, original_query: str, attempt: int) -> str:
        additions = [value for key, value in self._EXPANSIONS.items() if key in original_query]
        if not additions:
            return original_query
        rewritten = f"{original_query} {' '.join(additions)}"
        if attempt >= 2:
            rewritten += " 用户手册 故障原因 操作步骤 安全注意事项"
        return " ".join(rewritten.split())
