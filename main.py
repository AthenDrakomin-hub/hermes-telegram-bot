"""
智造AI创意工坊 - 主入口
Bot 启动 + 注册所有处理器
"""
import sys
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import BOT_TOKEN, ADMIN_IDS
from database import init_db
from handlers import start_command, handle_text, user_states
from callback_handler import handle_callback
from photo_handler import handle_photo


# 配置日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    """启动 Bot"""
    init_db()

    # 获取应用实例
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # ==================== 回调处理器 ====================
    application.add_handler(CallbackQueryHandler(handle_callback))

    # ==================== 消息处理器 ====================
    # ⚠️ 图片消息优先于文本消息
    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo,
        )
    )

    # 命令处理器
    application.add_handler(CommandHandler("start", start_command))

    # 文本消息（排除命令）
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    # ==================== 启动 ====================
    logger.info("🚀 智造AI创意工坊 Bot 启动中...")
    logger.info(f"📱 Bot Token: {BOT_TOKEN[:20]}...")
    logger.info("💡 按 Ctrl+C 停止 Bot")

    # 使用 polling 模式
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
