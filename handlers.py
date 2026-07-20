"""
智造AI创意工坊 - 统一消息处理器
PTB v22: 所有文本处理合并到一个 Handler，避免 handler overlap race condition
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from keyboards import get_main_keyboard, get_back_to_menu_keyboard, get_admin_panel_keyboard
from config import WELCOME_MESSAGE, ADMIN_IDS
from database import get_or_create_user, get_user_credits, get_user_stats, update_credits


# ==================== 用户当前状态 ====================
# 格式: user_id -> {"mode": "idle/text2img/text2vid/etc", "temp_data": {...}}
user_states = {}


def is_admin(user_id):
    """检查是否为管理员"""
    return int(user_id) in [int(aid) for aid in ADMIN_IDS if aid]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    user = update.effective_user
    user_id = user.id

    # 获取或创建用户
    user_data = get_or_create_user(
        user_id=user_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        is_admin=1 if is_admin(user_id) else 0,
    )

    # 重置用户状态
    user_states[user_id] = {"mode": "idle"}

    # 发送欢迎语 + 底部常驻键盘（管理员额外显示管理面板）
    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_keyboard(is_admin=is_admin(user_id)),
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    统一文本消息处理器
    所有底部键盘按钮点击都作为普通文本消息到达这里
    """
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # 确保用户已注册
    get_or_create_user(user_id)

    # 获取当前状态
    state = user_states.get(user_id, {"mode": "idle"})
    mode = state.get("mode", "idle")

    # ==================== 全局白名单过滤 ====================
    # 非管理员用户尝试访问管理功能时，拦截并提示无权
    admin_text_commands = ["管理面板", "用户管理", "手动充值", "今日统计", "用户列表"]
    if text in admin_text_commands and not is_admin(user_id):
        await update.message.reply_text(
            "🔒 此功能仅限管理员使用", reply_markup=get_back_to_menu_keyboard()
        )
        return

    # ==================== 管理员指令 ====================
    if is_admin(user_id):
        if text == "管理面板":
            await update.message.reply_text(
                "🛠️ 管理面板\n\n选择你要执行的操作：",
                reply_markup=get_admin_panel_keyboard(),
            )
            return
        if text.startswith("充值 "):
            await handle_admin_recharge(update, context, text)
            return
        elif text.startswith("查用户 "):
            await handle_admin_check_user(update, context, text)
            return
        elif text == "用户列表":
            await handle_admin_user_list(update, context)
            return
        elif text == "今日统计":
            await handle_admin_today_stats(update, context)
            return
        elif text == "用户管理":
            await handle_admin_user_mgmt(update, context)
            return
        elif text == "手动充值":
            await handle_admin_manual_recharge_list(update, context)
            return
        elif text == "流控管理":
            await handle_admin_rate_limit(update, context)
            return

    # ==================== 功能路由 ====================
    if mode == "idle":
        # 管理员额外按钮的文本匹配
        if text == "管理面板" and is_admin(user_id):
            await update.message.reply_text(
                "🛠️ 管理面板\n\n选择你要执行的操作：",
                reply_markup=get_admin_panel_keyboard(),
            )
            return

        # 空闲状态，匹配底部键盘按钮
        await handle_idle_mode(update, context, text)
        return

    # 非 idle 状态下，如果用户点了底部按钮，也应该路由到对应功能
    bottom_buttons = ["文生图", "图片编辑", "文生视频", "图生视频", "我的积分", "使用说明", "充值积分"]
    if text in bottom_buttons:
        await handle_idle_mode(update, context, text)
        return

    elif mode == "waiting_prompt":
        # 等待用户输入提示词
        await handle_waiting_prompt(update, context, text, state)

    elif mode == "waiting_image":
        # 等待用户发送图片（文字消息拦截）
        await update.message.reply_text(
            "⚠️ 请先发送图片！发送图片后我会引导你输入编辑描述或动态效果。\n\n"
            "如果你不想继续使用当前功能，请点击底部菜单选择其他功能。",
        )

    elif mode == "waiting_edit_description":
        # 等待用户输入编辑描述
        await handle_waiting_edit_description(update, context, text, state)

    elif mode == "waiting_video_prompt":
        # 等待用户输入视频描述
        await handle_waiting_video_prompt(update, context, text, state)

    elif mode == "waiting_admin_rpm":
        # 管理员输入RPM值
        rpm_type = state.get("rpm_type", "")
        try:
            rpm_value = int(text)
            from database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            if rpm_type == "global":
                cursor.execute("UPDATE rate_limits SET global_rpm = ? WHERE id=1", (rpm_value,))
                await update.message.reply_text(f"✅ 全局RPM已设置为: {rpm_value}")
            elif rpm_type == "per_user":
                cursor.execute("UPDATE rate_limits SET per_user_rpm = ? WHERE id=1", (rpm_value,))
                await update.message.reply_text(f"✅ 单用户RPM已设置为: {rpm_value}")
            conn.commit()
            conn.close()
            user_states[user_id] = {"mode": "idle"}
        except ValueError:
            await update.message.reply_text("❌ 请输入有效的数字")


async def handle_idle_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """空闲状态下的按钮处理"""
    user_id = update.effective_user.id

    if text == "文生图":
        user_states[user_id] = {"mode": "waiting_prompt", "func": "text2img"}
        await update.message.reply_text(
            "🎨 请输入你想生成的图片描述\n\n"
            "💡 提示：描述越详细，生成效果越好\n"
            "例如：一只穿着粉色牛仔裙的白色小猫坐在咖啡店露台上"
        )

    elif text == "图片编辑":
        user_states[user_id] = {"mode": "waiting_image", "func": "img2img"}
        await update.message.reply_text(
            "🖼️ 请发送你想要编辑的图片\n\n"
            "支持：jpg/png/webp 格式"
        )

    elif text == "文生视频":
        user_states[user_id] = {"mode": "waiting_video_prompt", "func": "text2vid"}
        await update.message.reply_text(
            "🎬 请输入你想生成的视频描述\n\n"
            "例如：一只可爱的小猫在阳光下的咖啡店里悠闲地喝着咖啡"
        )

    elif text == "图生视频":
        user_states[user_id] = {"mode": "waiting_image", "func": "img2vid"}
        await update.message.reply_text(
            "🎥 请发送你想要制作视频的图片\n\n"
            "💡 发送图片后，我会引导你输入动态描述"
        )

    elif text == "我的积分":
        credits = get_user_credits(user_id)
        stats = get_user_stats(user_id)
        if stats:
            msg = f"""
📊 你的积分信息

💰 剩余积分: {credits}
🎨 累计生成: {stats['total_generated']} 次
📅 注册时间: {stats['created_at'][:10]}
🔄 充值次数: {stats['recharge_count']}
📤 消耗次数: {stats['spend_count']}
            """
        else:
            msg = f"💰 剩余积分: {credits}"
        await update.message.reply_text(msg.strip())

    elif text == "使用说明":
        await update.message.reply_text(
            "📖 使用说明\n\n"
            "1️⃣ 文生图：输入描述生成图片，消耗1积分\n"
            "2️⃣ 图片编辑：上传图片+编辑描述，消耗1.5积分\n"
            "3️⃣ 文生视频：输入描述生成5秒视频，消耗5积分\n"
            "4️⃣ 图生视频：上传图片+动态描述，消耗4积分\n"
            "5️⃣ 充值积分：点击底部按钮选择充值档位\n"
            "6️⃣ 查看积分：点击'我的积分'查看余额\n\n"
            "💡 新用户注册赠送50积分",
            reply_markup=get_back_to_menu_keyboard(),
        )

    elif text == "充值积分":
        from keyboards import get_recharge_keyboard
        await update.message.reply_text(
            "💳 选择充值档位\n\n"
            "📌 体验档: $1 → 100积分\n"
            "📌 入门档: $5 → 550积分(赠50)\n"
            "📌 标准档: $10 → 1200积分(赠200)\n"
            "📌 进阶档: $25 → 3200积分(赠700)\n"
            "📌 超值档: $50 → 7000积分(赠2000)\n\n"
            "选择档位后，会显示USDT收款地址，"
            "转账后联系管理员确认即可。",
            reply_markup=get_recharge_keyboard(),
        )

    else:
        # 未知输入，显示帮助
        await update.message.reply_text(
            "🤔 请选择一个功能：",
            reply_markup=get_main_keyboard(),
        )


async def handle_waiting_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, state: dict):
    """等待用户输入文生图描述"""
    user_id = update.effective_user.id
    func = state.get("func")

    # 存储提示词
    state["prompt"] = text
    user_states[user_id] = state

    # 发送尺寸选择
    from keyboards import get_image_size_keyboard
    await update.message.reply_text(
        "✅ 收到描述！请选择图片尺寸：",
        reply_markup=get_image_size_keyboard(),
    )


async def handle_waiting_edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, state: dict):
    """等待用户输入图片编辑描述"""
    user_id = update.effective_user.id
    state["edit_prompt"] = text
    user_states[user_id] = state

    from keyboards import get_image_size_keyboard
    await update.message.reply_text(
        "✅ 收到编辑描述！请选择输出尺寸：",
        reply_markup=get_image_size_keyboard(),
    )


async def handle_waiting_video_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, state: dict):
    """等待用户输入视频描述"""
    user_id = update.effective_user.id
    func = state.get("func")

    state["prompt"] = text
    user_states[user_id] = state

    from keyboards import get_video_ratio_keyboard
    await update.message.reply_text(
        "✅ 收到视频描述！请选择视频比例：",
        reply_markup=get_video_ratio_keyboard(),
    )


# ==================== 管理员功能 ====================

async def handle_admin_recharge(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """管理员充值指令：充值 [用户ID] [档位]"""
    parts = text.split()
    if len(parts) != 3:
        await update.message.reply_text("❌ 格式错误\n用法：充值 [用户ID] [档位]\n例：充值 123456789 标准档")
        return

    target_user_id = int(parts[1])
    tier_name = parts[2]

    from config import RECHARGE_TIERS
    tier = RECHARGE_TIERS.get(tier_name)
    if not tier:
        await update.message.reply_text(f"❌ 未知的档位: {tier_name}\n可用档位: {', '.join(RECHARGE_TIERS.keys())}")
        return

    total_credits = tier["credits"] + tier["bonus"]
    new_credits = update_credits(
        user_id=target_user_id,
        amount=total_credits,
        transaction_type="admin_add",
        description=f"管理员充值: {tier_name}",
        usdt_amount=tier["usdt"],
        tier_name=tier_name,
    )

    if new_credits is not None:
        await update.message.reply_text(
            f"✅ 充值成功！\n"
            f"用户ID: {target_user_id}\n"
            f"档位: {tier_name}\n"
            f"充值: {tier['credits']} + 赠送: {tier['bonus']} = {total_credits} 积分\n"
            f"当前余额: {new_credits}"
        )
    else:
        await update.message.reply_text(f"❌ 用户 {target_user_id} 不存在")


async def handle_admin_check_user(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """管理员查询用户：查用户 [用户ID]"""
    parts = text.split()
    if len(parts) != 2:
        await update.message.reply_text("❌ 格式错误\n用法：查用户 [用户ID]")
        return

    user_id = int(parts[1])
    stats = get_user_stats(user_id)

    if stats:
        await update.message.reply_text(
            f"👤 用户信息\n"
            f"ID: {user_id}\n"
            f"积分: {stats['credits']}\n"
            f"累计生成: {stats['total_generated']}\n"
            f"注册时间: {stats['created_at']}\n"
            f"充值次数: {stats['recharge_count']}\n"
            f"消耗次数: {stats['spend_count']}"
        )
    else:
        await update.message.reply_text(f"❌ 用户 {user_id} 不存在")


async def handle_admin_user_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员查看所有用户"""
    from database import get_all_users
    users = get_all_users(limit=50)
    msg = f"📋 最近注册用户 (共 {len(users)} 人):\n\n"
    for u in users:
        msg += f"ID: {u['user_id']} | {u['first_name'] or u['username'] or 'Unknown'} | 积分: {u['credits']}\n"
    await update.message.reply_text(msg[:4000])  # Telegram消息限制4096字符


async def handle_admin_today_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员查看今日统计"""
    from database import get_today_stats
    stats = get_today_stats()
    await update.message.reply_text(
        f"📊 今日统计\n\n"
        f"新增用户: {stats['new_users']}\n"
        f"活跃用户: {stats['active_users']}\n"
        f"充值总额: {stats['income']} 积分\n"
        f"消耗总额: {stats['expense']} 积分\n"
        f"交易笔数: {stats['total_transactions']}"
    )


async def handle_admin_user_mgmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员用户管理（带内联按钮）"""
    from database import get_all_users
    all_users = get_all_users(100)
    if not all_users:
        await update.message.reply_text("👥 暂无用户")
        return

    per_page = 10
    total_pages = max(1, (len(all_users) + per_page - 1) // per_page)

    msg = f"👥 用户管理 (1/{total_pages})\n{'━' * 20}\n"
    for i, u in enumerate(all_users[:per_page]):
        name = u.get('first_name', '') or u.get('username', '') or f"用户{u['user_id']}"
        msg += f"\n{i+1}. {name}\n"
        msg += f"   💰 余额: {u['credits']} | 🎨 生成: {u['total_generated']}"
    msg += f"\n{'━' * 20}"

    kb_rows = []
    for u in all_users[:per_page]:
        name = u.get('first_name', '') or u.get('username', '') or f"用户{u['user_id']}"
        kb_rows.append([
            InlineKeyboardButton(f"👁️ {name}", callback_data=f"admin_view_user_{u['user_id']}"),
            InlineKeyboardButton(f"💰 充值", callback_data=f"admin_recharge_user_{u['user_id']}"),
        ])
    kb_rows.append([InlineKeyboardButton("🏠 返回", callback_data="back_to_menu")])

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb_rows))


async def handle_admin_manual_recharge_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员手动充值用户列表（带内联按钮）"""
    from database import get_all_users
    all_users = get_all_users(100)
    if not all_users:
        await update.message.reply_text("💰 暂无用户")
        return

    per_page = 10
    total_pages = max(1, (len(all_users) + per_page - 1) // per_page)

    msg = f"💰 手动充值 (1/{total_pages})\n{'━' * 20}\n"
    for i, u in enumerate(all_users[:per_page]):
        name = u.get('first_name', '') or u.get('username', '') or f"用户{u['user_id']}"
        msg += f"\n{i+1}. {name}\n"
        msg += f"   ID: {u['user_id']} | 💰 余额: {u['credits']}"
    msg += f"\n{'━' * 20}"

    kb_rows = []
    for u in all_users[:per_page]:
        name = u.get('first_name', '') or u.get('username', '') or f"用户{u['user_id']}"
        kb_rows.append([InlineKeyboardButton(f"💰 给 {name} 充值", callback_data=f"admin_recharge_user_{u['user_id']}")])
    kb_rows.append([InlineKeyboardButton("🏠 返回", callback_data="back_to_menu")])

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb_rows))


async def handle_admin_rate_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员流控管理"""
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()

    # 检查 rate_limit 表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rate_limits'")
    if not cursor.fetchone():
        # 创建表
        cursor.execute("""
            CREATE TABLE rate_limits (
                id INTEGER PRIMARY KEY CHECK(id=1),
                enabled INTEGER DEFAULT 1,
                global_rpm INTEGER DEFAULT 60,
                per_user_rpm INTEGER DEFAULT 5,
                group_half_price INTEGER DEFAULT 1
            )
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO rate_limits (id, enabled, global_rpm, per_user_rpm, group_half_price)
            VALUES (1, 1, 60, 5, 1)
        """)
        conn.commit()

    cursor.execute("SELECT * FROM rate_limits WHERE id=1")
    row = cursor.fetchone()
    rl = dict(row) if row else {"enabled": 1, "global_rpm": 60, "per_user_rpm": 5, "group_half_price": 1}
    conn.close()

    status = "🟢 已开启" if rl["enabled"] else "🔴 已关闭"
    half_status = "🟢 启用" if rl["group_half_price"] else "🔴 禁用"

    msg = (
        f"⚡ 全局流控管理\n\n"
        f"总开关: {status}\n"
        f"全局 RPM: {rl['global_rpm']}\n"
        f"单用户 RPM: {rl['per_user_rpm']}\n"
        f"群聊半价: {half_status}\n\n"
        f"点击下方按钮进行管理："
    )

    kb = [
        [
            InlineKeyboardButton("⏸️ 暂停流控" if rl["enabled"] else "▶️ 开启流控", callback_data="admin_toggle_ratelimit"),
        ],
        [
            InlineKeyboardButton(f"全局RPM: {rl['global_rpm']}", callback_data="admin_set_global_rpm"),
            InlineKeyboardButton(f"单用户RPM: {rl['per_user_rpm']}", callback_data="admin_set_per_user_rpm"),
        ],
        [
            InlineKeyboardButton("群聊半价" if rl["group_half_price"] else "取消群聊半价", callback_data="admin_toggle_half_price"),
        ],
        [
            InlineKeyboardButton("🏠 返回", callback_data="back_to_menu"),
        ],
    ]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))


# 流控状态存储（内存中，重启后从数据库读）
rate_limit_state = {}
