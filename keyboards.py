"""
智造AI创意工坊 - 键盘布局定义
底部常驻键盘 + 内联按钮
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard(is_admin=False):
    """
    底部常驻键盘
    is_admin=True: 管理员看到额外"管理面板"按钮
    """
    keyboard = [
        [
            KeyboardButton("文生图"),
            KeyboardButton("图片编辑"),
        ],
        [
            KeyboardButton("文生视频"),
            KeyboardButton("图生视频"),
        ],
        [
            KeyboardButton("我的积分"),
            KeyboardButton("使用说明"),
        ],
        [
            KeyboardButton("充值积分"),
        ],
    ]
    if is_admin:
        keyboard.append([KeyboardButton("管理面板")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def get_image_size_keyboard():
    """文生图/图生图 - 尺寸选择"""
    keyboard = [
        [
            InlineKeyboardButton("1K (1024×1024)", callback_data="size_1K"),
            InlineKeyboardButton("2K (2048×2048)", callback_data="size_2K"),
        ],
        [
            InlineKeyboardButton("3K (3072×3072)", callback_data="size_3K"),
            InlineKeyboardButton("4K (4096×4096)", callback_data="size_4K"),
        ],
        [
            InlineKeyboardButton("返回", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_image_ratio_keyboard():
    """文生图/图生图 - 比例选择"""
    keyboard = [
        [
            InlineKeyboardButton("1:1 方形", callback_data="ratio_1:1"),
            InlineKeyboardButton("16:9 横屏", callback_data="ratio_16:9"),
        ],
        [
            InlineKeyboardButton("9:16 竖屏", callback_data="ratio_9:16"),
            InlineKeyboardButton("4:3 横屏", callback_data="ratio_4:3"),
        ],
        [
            InlineKeyboardButton("3:4 竖屏", callback_data="ratio_3:4"),
            InlineKeyboardButton("3:2 横屏", callback_data="ratio_3:2"),
        ],
        [
            InlineKeyboardButton("返回", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_video_ratio_keyboard():
    """视频 - 比例选择"""
    keyboard = [
        [
            InlineKeyboardButton("4:3 标准", callback_data="ratio_4:3"),
            InlineKeyboardButton("16:9 横屏", callback_data="ratio_16:9"),
        ],
        [
            InlineKeyboardButton("9:16 竖屏", callback_data="ratio_9:16"),
            InlineKeyboardButton("1:1 方形", callback_data="ratio_1:1"),
        ],
        [
            InlineKeyboardButton("返回", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_menu_keyboard():
    """返回主菜单"""
    keyboard = [[InlineKeyboardButton("返回主菜单", callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(keyboard)


def get_admin_panel_keyboard():
    """管理面板主菜单"""
    keyboard = [
        [
            InlineKeyboardButton("📊 今日统计", callback_data="admin_today_stats"),
        ],
        [
            InlineKeyboardButton("👥 用户管理", callback_data="admin_user_mgmt_page_1"),
        ],
        [
            InlineKeyboardButton("💰 手动充值", callback_data="admin_recharge_select_user_page_1"),
        ],
        [
            InlineKeyboardButton("↩️ 返回主菜单", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_pagination_keyboard(current_page, total_pages, action_prefix):
    """分页导航按钮"""
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"{action_prefix}_page_{current_page-1}"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"{action_prefix}_page_{current_page+1}"))
    if not buttons:
        buttons.append(InlineKeyboardButton("🏠 返回", callback_data="back_to_menu"))
    else:
        buttons.append(InlineKeyboardButton("🏠 返回", callback_data="back_to_menu"))
    return InlineKeyboardMarkup([buttons])


def get_recharge_keyboard():
    """充值档位内联按钮"""
    keyboard = [
        [
            InlineKeyboardButton("体验档 $1\n100积分", callback_data="recharge_体验档"),
        ],
        [
            InlineKeyboardButton("入门档 $5\n550积分", callback_data="recharge_入门档"),
        ],
        [
            InlineKeyboardButton("标准档 $10\n1200积分", callback_data="recharge_标准档"),
        ],
        [
            InlineKeyboardButton("进阶档 $25\n3200积分", callback_data="recharge_进阶档"),
        ],
        [
            InlineKeyboardButton("超值档 $50\n7000积分", callback_data="recharge_超值档"),
        ],
        [
            InlineKeyboardButton("返回", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_recharge_action_keyboard():
    """充值页面操作按钮"""
    keyboard = [
        [
            InlineKeyboardButton("📋 复制收款地址", callback_data="copy_usdt"),
        ],
        [
            InlineKeyboardButton("💬 联系管理员", url="https://t.me/jinyang0818"),
        ],
        [
            InlineKeyboardButton("返回", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_recharge_tier_keyboard(user_id):
    """管理员充值档位选择"""
    keyboard = [
        [
            InlineKeyboardButton("体验档 $1\n100积分", callback_data=f"admin_tier_{user_id}_体验档"),
        ],
        [
            InlineKeyboardButton("入门档 $5\n550积分", callback_data=f"admin_tier_{user_id}_入门档"),
        ],
        [
            InlineKeyboardButton("标准档 $10\n1200积分", callback_data=f"admin_tier_{user_id}_标准档"),
        ],
        [
            InlineKeyboardButton("进阶档 $25\n3200积分", callback_data=f"admin_tier_{user_id}_进阶档"),
        ],
        [
            InlineKeyboardButton("超值档 $50\n7000积分", callback_data=f"admin_tier_{user_id}_超值档"),
        ],
        [
            InlineKeyboardButton("⬅️ 返回", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_usage_keyboard():
    """使用说明内联按钮"""
    keyboard = [
        [
            InlineKeyboardButton("积分说明", callback_data="usage_credits"),
        ],
        [
            InlineKeyboardButton("使用指南", callback_data="usage_guide"),
        ],
        [
            InlineKeyboardButton("返回", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
