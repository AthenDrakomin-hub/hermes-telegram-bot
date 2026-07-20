"""
智造AI创意工坊 - Prompt 增强引擎（纯规则，零外部依赖）
不调用LLM，不做NLTK，纯本地规则匹配 + 后缀追加
"""
import re
from .style_manager import match_style


# ========== 质量后缀 ==========
_QUALITY_SUFFIXES = {
    't2i': ', 8k, highly detailed, sharp focus, cinematic lighting',
    'i2i': ', smooth texture, artistic style transfer',
    't2v': ', 24fps, smooth motion, cinematic camera',
    'i2v': ', subtle ambient motion, gentle sway',
}

# ========== 工具函数 ==========

def _sanitize(text):
    """剔除非ASCII字符（中文/emoji 污染），保留英文和数字"""
    cleaned = re.sub(r'[^\x00-\x7F]+', ' ', text).strip()
    # 如果清洗后为空（全是中文），返回原文（让 API 自己处理）
    return cleaned if cleaned else text


def _has_depth_cue(text):
    return any(p in text.lower() for p in [
        'depth of field', '3d', 'layering', 'perspective', 'overlapping'
    ])


def _has_motion_cue(text):
    return bool(re.search(
        r'\b(pan|tilt|zoom|dolly|orbit|track|crane|push|pull|rotate)\b',
        text, re.I
    ))


# ========== 四大增强入口 ==========

def enhance_t2i(user_input):
    """文生图增强：追加质量词 + 深度描述"""
    cached = match_style(user_input)
    if cached:
        return _sanitize(cached)

    base = _sanitize(user_input)
    enhanced = base + _QUALITY_SUFFIXES['t2i']
    if not _has_depth_cue(enhanced):
        enhanced += ", with strong depth-of-field and 3D spatial layering"
    return enhanced


def enhance_i2i(user_input):
    """图生图增强：风格描述 + 质量后缀"""
    cached = match_style(user_input)
    if cached:
        return _sanitize(cached) + _QUALITY_SUFFIXES['i2i']

    base = _sanitize(user_input)
    return base + _QUALITY_SUFFIXES['i2i']


def enhance_t2v(user_input):
    """文生视频增强：追加运动描述"""
    cached = match_style(user_input)
    if cached:
        return _sanitize(cached) + _QUALITY_SUFFIXES['t2v']

    base = _sanitize(user_input)
    enhanced = base + _QUALITY_SUFFIXES['t2v']
    if not _has_motion_cue(enhanced):
        enhanced += ", slow camera dolly-in with subtle parallax"
    return enhanced


def enhance_i2v(user_input):
    """图生视频增强：含名词黑名单熔断"""
    # 图生视频只关注"运动"，不关注"主体"
    # 如果用户输入包含具体名词（中英文），说明他可能误把主体描述当运动描述
    # 此时降级为安全默认值
    BANNED_WORDS = [
        'girl', 'boy', 'man', 'woman', 'person', 'child',
        'dog', 'cat', 'bird', 'fish', 'tree', 'car', 'house',
        'dress', 'shirt', 'hat', 'hair', 'face', 'eye', 'hand',
        'flower', 'mountain', 'building', 'animal',
        # 中文高频名词
        '女孩', '男孩', '男人', '女人', '人', '小孩', '儿童',
        '狗', '猫', '鸟', '鱼', '树', '车', '房子', '房屋',
        '裙子', '衬衫', '帽子', '头发', '脸', '眼睛', '手', '脚',
        '花', '山', '建筑', '动物', '宠物',
    ]
    lower_input = user_input.lower()
    if any(word in lower_input for word in BANNED_WORDS):
        return "gentle ambient motion, smooth lens breathing"

    # 命中词库也走 sanitize（虽然预制词是英文，保持一致性）
    cached = match_style(user_input)
    if cached:
        return _sanitize(cached) + _QUALITY_SUFFIXES['i2v']

    base = _sanitize(user_input)
    return base + _QUALITY_SUFFIXES['i2v']
