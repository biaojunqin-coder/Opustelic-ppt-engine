"""生成 provider 抽象——SVG / 讲解词这些「要 LLM」的步骤，运行时由谁生成。

三种来源（默认免费·不强制付费 key）：
1. **运行时 Claude（默认·免费）**：skill 被 Claude Code 调用时，Claude 自己按 prompt / 规范现场生成。
   你正用的 Claude 就是那个 LLM——demo 里的预写函数只是兜底示范，无需本模块。
2. **外部 API（可选·省 token·要 key）**：接 OpenAI 兼容端点当苦力。
   ⚠️ DeepSeek/OpenAI 要云 key；但**本地 Ollama 也兼容此接口（免费·无云 key）**，照样省主模型 token。
3. **模板兜底**：narration 有 speaker_notes.narration_for_line（结构对·非亮眼）。

契约（svg_provider / narration_provider 都是 callable）：
- svg_provider(ctx) -> str        # ctx = build_deck_prompt 输出·返回该页 SVG
- narration_provider(line) -> str # 返回该页讲解词
"""

from __future__ import annotations

import json
import urllib.request
from typing import Callable


def openai_compatible_provider(build_messages: Callable, *, base_url: str, api_key: str,
                               model: str, timeout: int = 60) -> Callable:
    """走 OpenAI 兼容端点（DeepSeek / OpenAI / 本地 Ollama）的生成 provider（可选·省 token）。

    build_messages(input) -> [{role, content}]；返回 callable(input) -> 生成文本。
    ⚠️ 云端点要 api_key——可选优化（默认走运行时 Claude·免费）。本地 Ollama（base_url=localhost:11434/v1）
    免费·无云 key·照样省主模型 token。
    """
    def _provider(x):
        body = json.dumps({"model": model, "messages": build_messages(x)}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/chat/completions", data=body,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"]
    return _provider
