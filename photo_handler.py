"""
智造AI创意工坊 - 图片消息处理器
处理用户发送的图片（用于图生图/图生视频）
"""
import os
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers import user_states

logger = logging.getLogger(__name__)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理用户发送的图片"""
    user_id = update.effective_user.id
    
    # 先获取 state
    state = user_states.get(user_id, {"mode": "idle"})
    mode = state.get("mode", "idle")
    func = state.get("func", "")

    logger.info(f"[PHOTO_HANDLER] user_id={user_id}, mode={mode}, func={func}")

    from database import get_or_create_user
    get_or_create_user(user_id)

    if mode == "waiting_image":
        # 获取图片（选最大的那张）
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        # 构建 Telegram 文件公开 URL
        # file.file_path 可能是相对路径如 "photos/file_1.jpg" 或完整 URL
        if file.file_path.startswith("http"):
            file_url = file.file_path
        else:
            file_url = f"https://api.telegram.org/file/bot{context.bot.token}/{file.file_path}"

        logger.info(f"[PHOTO_HANDLER] file_url={file_url}")

        state["image_url"] = file_url
        user_states[user_id] = state

        if func == "img2img":
            # 图片编辑：下一步要编辑描述
            state["mode"] = "waiting_edit_description"
            user_states[user_id] = state
            await update.message.reply_text(
                "✅ 图片已收到！\n\n请描述你要如何编辑这张图片\n例如：把背景换成星空，人物换成赛博朋克风格"
            )

        elif func == "img2vid":
            # 图生视频：下一步要动态描述
            state["mode"] = "waiting_video_prompt"
            user_states[user_id] = state
            await update.message.reply_text(
                "✅ 图片已收到！\n\n请描述你想要的动态效果\n例如：人物慢慢转头看向镜头，头发随风飘动，背景灯光闪烁"
            )

    else:
        await update.message.reply_text(
            "⚠️ 请先点击功能按钮选择要使用的功能，然后我再接收你的图片哦~"
        )
