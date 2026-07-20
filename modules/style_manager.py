"""
智造AI创意工坊 - 词库管理器
从 style_library.txt 加载预制 prompt，命中后直接返回
"""
import os

_STYLE_FILE = os.path.join(os.path.dirname(__file__), '..', 'style_library.txt')

# 预加载词库 {关键词: 预制英文prompt}
STYLE_LIBRARY = {}
if os.path.exists(_STYLE_FILE):
    with open(_STYLE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if '|' in line:
                key, val = line.split('|', 1)
                STYLE_LIBRARY[key.strip()] = val.strip()


def match_style(text):
    """命中词库返回预制prompt，否则返回None"""
    # 对中文：逐个关键词做子串匹配（中文分词天然靠子串）
    # 对英文：用空格/标点拆分后精确匹配
    for key, prompt in STYLE_LIBRARY.items():
        if key in text:
            return prompt
    return None
