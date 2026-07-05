"""议题树 / 假设树（策略阶段 2 · 结构化思维）——把问题空间 MECE 拆解。对应方法论 03 + Novel goal_tree。

- **议题树**：还不知道什么重要时，把总问题拆成 MECE 子问题（瞄准 3 主分支）。
- **假设树**：Day-1 先押答案，拆成能快速证伪的子假设（砍 ⅔ 工作量的利器）。

fail-closed：非法 mode / 缺总问题 / 假设树缺 Day-1 答案 / 分支无可证伪检验 → error。
降解 to_sub_hypotheses()：喂 storyline_state.set_hypothesis_tree，打通策略层内部（树 → storyline）。
"""

from __future__ import annotations

TREE_MODES = {"议题树", "假设树"}
CONFIDENCE = {"高", "中", "低"}


def new_tree(question: str, mode: str = "假设树", hypothesis: str = "") -> dict:
    """建树骨架。议题树：question=L0 总问题；假设树：再给 hypothesis=Day-1 押的答案。"""
    return {"mode": mode, "question": question, "hypothesis": hypothesis, "branches": []}


def add_branch(tree: dict, key: str, claim: str, test: str, confidence: str = "中") -> dict:
    """加一分支（L1 根本面 / 子假设）。

    test = 能**杀死**该分支的检验（可证伪·『多做点研究』不是检验，『拉 4 家竞品定价比』才是）；
    confidence = 信心（高/中/低·先打低信心分支，方法论 03 假设树）。
    """
    tree["branches"].append({"key": key, "claim": claim, "test": test, "confidence": confidence})
    return tree


def validate_tree(tree: dict) -> dict:
    """校验 → {issues, valid}。fail-closed：mode/总问题/Day-1 答案/可证伪检验。"""
    issues = []
    if tree.get("mode") not in TREE_MODES:
        issues.append({"sev": "error", "msg": "mode 非 议题树/假设树"})
    if not tree.get("question"):
        issues.append({"sev": "error", "msg": "缺 L0 总问题"})
    if tree.get("mode") == "假设树" and not tree.get("hypothesis"):
        issues.append({"sev": "error", "msg": "假设树缺 Day-1 押的答案（『我不知道』不是假设·猜一个）"})
    # branches 显式为 None 也是合法 JSON 形态（or 兜底防崩·2026-07-02 saopan：校验器自己不能被崩溃击穿）
    br = tree.get("branches") or []
    if not br:
        issues.append({"sev": "error", "msg": "无分支"})
    seen = set()
    for b in br:
        k = b.get("key")
        if k in seen:
            issues.append({"sev": "error", "msg": f"分支 key 重复 {k}"})
        seen.add(k)
        if not b.get("test"):
            issues.append({"sev": "error", "msg": f"分支 {k or '?'} 无可证伪检验（『多做研究』不算·要能杀死它的检验）"})
        if b.get("confidence") not in CONFIDENCE:
            issues.append({"sev": "warn", "msg": f"分支 {k or '?'} 信心未标（高/中/低）"})
    # 3 的法则（方法论 03：3 主分支·2-5 可接受；>5 = 顶层没成形）
    if br and not (2 <= len(br) <= 5):
        issues.append({"sev": "warn", "msg": f"{len(br)} 分支（3 的法则建议 3·2-5 可接受·>5 顶层没成形）"})
    return {"issues": issues, "valid": not any(i["sev"] == "error" for i in issues)}


def to_sub_hypotheses(tree: dict) -> list:
    """议题树/假设树 → storyline 的 sub_hypotheses（降解·喂 storyline_state.set_hypothesis_tree）。"""
    r = validate_tree(tree)
    if not r["valid"]:
        raise ValueError(f"树非法·拒降解：{r['issues']}")
    return [{"id": b["key"], "claim": b["claim"], "test": b["test"],
             "confidence": b.get("confidence", "中")} for b in tree["branches"]]
