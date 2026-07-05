"""范本检索（③RAG）—— 按 facets 检索页型卡库，对应 Novel search_exemplars(题材, 桥段)。

检索签名 = search_deck_cards(page_function, domain, intent, doc_type)：
page_function 是主键(权重最高)，domain/intent/doc_type 过滤加分；无 facet 时按 rating 全返回。
检索本体见 specs/拆deck-检索本体设计.md；卡库 exemplars/页型卡库.json。
"""
