"""生成 provider 抽象测试（只测构造·不实调外部端点）。"""

from __future__ import annotations

from engine.providers import openai_compatible_provider


def test_provider_constructs_callable():
    # 构造返回 callable（不实际调用·无端点/key）；默认生成走运行时 Claude·此为可选 API 适配
    p = openai_compatible_provider(
        lambda x: [{"role": "user", "content": str(x)}],
        base_url="http://localhost:11434/v1", api_key="x", model="qwen2.5")
    assert callable(p)
