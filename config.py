"""
智造AI创意工坊 - 配置文件
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ==================== Telegram Bot 配置 ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8995500422:AAHBCvdqcs5522Fd-nFn2-BokkbpoKd0fFM")

# 管理员列表 (Telegram user_id)
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# ==================== Agnes AI API 配置 ====================
# API Key 池（多个 Key 轮流使用，突破 RPM 限制）
AGNES_API_KEYS = [
    "sk-CxDUncSqWfaDMuUeC4ta03cqhsTQkyLa3CKZYGmNnslmJSTt",
    "sk-u0qfwaRoaKBdhNzxpINz40c5WTcTJHIfB1wNl3KixmdgFwZ5",
    "sk-bLRZaEL38DCD8PcxkeDsHtzgSjCIz5K5wXtbEAUtCmLXKekx",
    "sk-YZfwF1hwhh7KtAJWFHRx5tP5Y5APIDEwZgoLhdxSyeNFb7Bv",
]

AGNES_BASE_URL = "https://apihub.agnes-ai.com/v1"

# 模型名称
IMAGE_MODEL = "agnes-image-2.1-flash"
VIDEO_MODEL = "agnes-video-v2.0"

# API 超时设置 (秒)
IMAGE_TIMEOUT = 360
VIDEO_TIMEOUT = 360

# ==================== 积分配置 ====================
NEW_USER_CREDITS = 50

CREDIT_COSTS = {
    "text2img": 1,
    "img2img": 1.5,
    "text2vid": 5,
    "img2vid": 4,
}

RECHARGE_TIERS = {
    "体验档": {"usdt": 1, "credits": 100, "bonus": 0},
    "入门档": {"usdt": 5, "credits": 500, "bonus": 50},
    "标准档": {"usdt": 10, "credits": 1000, "bonus": 200},
    "进阶档": {"usdt": 25, "credits": 2500, "bonus": 700},
    "超值档": {"usdt": 50, "credits": 5000, "bonus": 2000},
}

USDT_ADDRESS = os.getenv("USDT_ADDRESS", "")

# ==================== 视频生成配置 ====================
VIDEO_DEFAULT_DURATION = 5
VIDEO_MAX_DURATION = 18
VIDEO_NUM_FRAMES_MAP = {
    3: 81,
    5: 121,
    10: 241,
    18: 441,
}
VIDEO_FRAME_RATE = 24

VIDEO_POLL_INTERVAL = 8
VIDEO_POLL_TIMEOUT = 360

# ==================== 数据库配置 ====================
DATABASE_PATH = "database.db"

# ==================== 交互配置 ====================
WELCOME_MESSAGE = """✨智造AI创意工坊 / 你的专属AI视觉创作工作室 / 文生图｜扩图修复｜AI短视频批量生成"""
