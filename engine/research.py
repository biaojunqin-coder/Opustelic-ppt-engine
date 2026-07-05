"""调研接口（策略阶段 3 · 数字溯源）——深度研究的接入点。

推荐路径 `provider="claude-websearch"`：Claude 运行时自己用 WebSearch/WebFetch 挖数据+溯源，
免费、无 key、已验证可用（D6 拍板 · D13 复核确认）。`provider="gpt-researcher"`（第三方包+独立
LLM/搜索 key）是 🧭能力边界，待用户愿意为调研深度多花钱再启，非当前默认路径。
数字溯源铁律（Perplexica / 01 雷区7）：基准 / 数字**原值照抄·绝不概括**，每个关键论断带来源。
⚠️ 调研工具的 fact-check 是 LLM 自评——**不能当 🟢 硬信号**，数字溯源走机检（check_evidence_source）/ 人审（L2）。

⚠️ **时间锚定铁律（真实踩过的坑）**：联网搜索前必须先确认"今天是哪天"，搜索词/筛选结果都要按当前时间过滤——
**"某年预计"这种表述一旦那年已经过去，必须换成该年的实际数（actual），不能让"预计"挂过期**。
没锚定时间直接搜，搜出来的"最新数据"可能是训练知识里残留的旧预测，会在 pitch 现场被当场戳穿成"调研没做新鲜"。
"""

from __future__ import annotations


def research(query: str, *, provider: str = "stub", today: str | None = None) -> dict:
    """深度调研一个论点 → 可溯源数据。现 stub：返回待人工 / 待接入。

    provider='stub'（占位） | 'gpt-researcher'（待接·联网 / key）。
    today：调用方传入"今天是哪天"（如"2026-06-30"）——写进返回的 note，提醒下游别把过期"预计"当未来时态用
    （真实踩过的坑：搜出"2025年预计破万亿"，2026年了还当成未来时态写进 deck）。引擎本身不读系统时钟，靠调用方显式传入。
    返回 {query, findings:[{data, source}], status, today}。
    """
    anchor = f"（已知今天 {today}·搜索结果里凡'某年预计'若该年已过，须换成实际数）" if today else "（⚠️ 未传 today·搜索前务必先确认当前日期）"
    if provider == "stub":
        return {"query": query, "findings": [], "status": "stub·待接 gpt-researcher 或人工填", "today": today,
                "note": f"数字须原值照抄 + 带 source·不概括（01 雷区7）{anchor}"}
    if provider == "claude-websearch":
        # 运行时由 Claude 用 WebSearch/WebFetch 挖数据 + 溯源（免费·无 key·替代 gpt-researcher）
        return {"query": query, "findings": [], "today": today,
                "status": "claude-websearch·运行时 Claude 用 WebSearch 挖+溯源",
                "note": f"skill 运行时 Claude 调 WebSearch/WebFetch·数字原值照抄+带 source·不接付费 API{anchor}"}
    raise NotImplementedError(f"调研 provider {provider!r} 待接入（联网 / key）")


def attach_source(evidence: dict, source: str) -> dict:
    """给一条 evidence 补 source（数字溯源·防编造）。配 check_evidence_source 使用。"""
    return {**evidence, "source": source}


def attach_citation(evidence: dict, *, title: str, outlet: str, date: str, quote: str, url: str,
                    source_type: str = "external") -> dict:
    """给一条 evidence 补完整引用信息（source_title/outlet/date/quote/url + source_type）。

    声明式：填了这些字段，engine/svg_layout.py::source_card_from_evidence 会自动识别渲染引用卡——
    不需要按页码另开一张硬编码表（早期 Descente demo 的反模式：SOURCE_CARDS={7:..., 11:...}）。
    引用内容必须是亲自核验过的真实网页摘录，不可编造（和 attach_source 同一条铁律）。

    source_type（D18 FR5.1·用户拍板的对客呈现分类）：
      "external"        外部公开数据（联网调研所得）——页面标注来源+尾页 references 带 URL 供验证；
      "client_provided" 客户内部资料（brief 内容/客户给的数据）——**页面不标**（客户本来就有，
                        刻意强调反而怪），内部台账溯源照记。本函数默认 external（用它的场景
                        就是联网调研）；brief 类证据在写 storyline 时手标 client_provided。
    """
    return {**evidence, "source": outlet, "source_title": title, "source_outlet": outlet,
            "source_date": date, "source_quote": quote, "source_url": url,
            "source_type": source_type}
