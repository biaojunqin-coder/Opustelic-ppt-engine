"""Prompt 引擎（①）—— 按当前任务动态拼装 prompt（范本卡 + 页型规范 + 大纲 + 状态），非写死模板。

对应 Novel beat_sheet_generator + 写正文时拼「手法卡+语感范本+细纲+回读」。
整合：retrieval(RAG 取范本卡) + deck_state(大纲状态) + deck_rules(硬门提醒)。
"""
