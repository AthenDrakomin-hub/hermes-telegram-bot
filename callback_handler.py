"""
智造AI创意工坊 - 内联按钮回调处理器
处理 InlineKeyboardButton 点击事件，调用实际功能模块
"""
import os
import httpx
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from keyboards import (
    get_main_keyboard,
    get_image_ratio_keyboard,
    get_image_size_keyboard,
    get_video_ratio_keyboard,
    get_recharge_keyboard,
    get_recharge_action_keyboard,
    get_back_to_menu_keyboard,
    get_admin_panel_keyboard,
    get_pagination_keyboard,
    get_admin_recharge_tier_keyboard,
)
from config import RECHARGE_TIERS, USDT_ADDRESS, ADMIN_IDS
from handlers import user_states, is_admin
from modules.prompt_enhancer import enhance_t2i, enhance_i2i, enhance_t2v, enhance_i2v


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """统一回调处理器"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data
    message = query.message
    
    import logging
    logging.getLogger().info(f"[CALLBACK] user_id={user_id}, data={data}")

    # 重置状态为空闲（只在返回主菜单时重置）
    # 其他回调需要保持原有状态（func, prompt 等）
    if data == "back_to_menu":
        user_states[user_id] = {"mode": "idle"}
        kb = get_main_keyboard(is_admin=is_admin(user_id))
        try:
            await message.edit_text(
                "🏠 主菜单",
                reply_markup=kb,
            )
        except Exception:
            # 如果 edit_text 失败（键盘类型不匹配），用 reply_text
            await message.reply_text(
                "🏠 主菜单",
                reply_markup=kb,
            )

    elif data.startswith("size_"):
        size = data.replace("size_", "")
        state = user_states.get(user_id, {})
        state["selected_size"] = size
        user_states[user_id] = state

        func = state.get("func", "text2img")
        if func in ["text2img", "img2img"]:
            await message.edit_text(
                "✅ 已选择尺寸: " + size + "\n请选择比例：",
                reply_markup=get_image_ratio_keyboard(),
            )
        else:
            await message.edit_reply_markup(reply_markup=None)

    elif data.startswith("ratio_"):
        ratio = data.replace("ratio_", "")
        state = user_states.get(user_id, {})
        state["selected_ratio"] = ratio
        user_states[user_id] = state

        func = state.get("func", "UNKNOWN_MISSING_FUNC")
        prompt = state.get("prompt", "")
        edit_prompt = state.get("edit_prompt", "")
        size = state.get("selected_size", "1K")

        if func == "text2img":
            await message.edit_text(
                f"✅ 参数已确认\n"
                f"尺寸: {size} | 比例: {ratio}\n"
                f"\n⏳ 正在生成图片，请稍候...",
                reply_markup=None,
            )
            await execute_text2img(message, user_id, prompt, size, ratio, context)

        elif func == "img2img":
            image_url = state.get("image_url", "")
            if not image_url:
                await message.edit_text("❌ 未找到图片，请重新发送", reply_markup=get_main_keyboard())
                return

            await message.edit_text(
                f"✅ 参数已确认\n"
                f"尺寸: {size} | 比例: {ratio}\n"
                f"\n⏳ 正在编辑图片，请稍候...",
                reply_markup=None,
            )
            await execute_img2img(message, user_id, image_url, edit_prompt, size, ratio, context)

        elif func == "text2vid":
            await message.edit_text(
                f"✅ 比例已确认: {ratio}\n"
                f"⏳ 正在创建视频任务...",
                reply_markup=None,
            )
            await execute_text2vid(message, user_id, prompt, ratio, context)

        elif func == "img2vid":
            image_url = state.get("image_url", "")
            if not image_url:
                await message.edit_text("❌ 未找到图片，请重新发送", reply_markup=get_main_keyboard())
                return

            await message.edit_text(
                f"✅ 比例已确认: {ratio}\n"
                f"⏳ 正在创建视频任务...",
                reply_markup=None,
            )
            await execute_img2vid(message, user_id, image_url, prompt, ratio, context)

    elif data.startswith("recharge_"):
        tier_name = data.replace("recharge_", "")
        tier = RECHARGE_TIERS.get(tier_name, {})

        if not USDT_ADDRESS:
            await message.edit_text("⚠️ 充值功能暂未配置收款地址")
            return

        total_credits = tier.get("credits", 0) + tier.get("bonus", 0)

        msg = (
            f"💳 {tier_name}充值\n\n"
            f"💰 金额: ${tier.get('usdt', 0)}\n"
            f"🎁 积分: {total_credits}（含赠送 {tier.get('bonus', 0)} 积分）\n\n"
            f"📍 USDT(TRC20)收款地址:\n"
            f"`{USDT_ADDRESS}`"
        )
        await message.edit_text(
            msg,
            parse_mode="Markdown",
            reply_markup=get_recharge_action_keyboard(),
        )

    elif data == "copy_usdt":
        # 点击复制 USDT 地址
        from telegram import ReplyKeyboardMarkup, KeyboardButton, CopyTextButton
        kb = KeyboardButton(
            text="📋 复制地址",
            copy_text=CopyTextButton(text=USDT_ADDRESS),
        )
        contact_kb = KeyboardButton(
            text="💬 联系管理员",
            url="https://t.me/jinyang0818",
        )
        reply_kb = KeyboardButton(text="返回主菜单")
        await message.reply_text(
            f"📍 USDT(TRC20)收款地址:\n\n"
            f"`{USDT_ADDRESS}`",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [[kb], [contact_kb], [reply_kb]],
                resize_keyboard=True,
                one_time_keyboard=False,
            ),
        )

    elif data == "usage_credits":
        await message.edit_text(
            "💰 积分说明\n\n"
            "• 文生图: 1积分/次\n"
            "• 图片编辑: 1.5积分/次\n"
            "• 文生视频: 5积分/次\n"
            "• 图生视频: 4积分/次\n"
            "• 新用户注册赠送50积分\n"
            "• 充值: $1 = 100积分起\n"
            "• 积分永久有效，不过期",
            reply_markup=get_back_to_menu_keyboard(),
        )

    elif data == "usage_guide":
        await message.edit_text(
            "📖 使用指南\n\n"
            "1. 点击底部功能按钮选择你要的功能\n"
            "2. 按提示输入描述或上传图片\n"
            "3. 选择参数（尺寸/比例）\n"
            "4. 确认后立即开始生成\n"
            "5. 生成完成后自动发送结果\n\n"
            "💡 小贴士：\n"
            "• 描述越详细，生成效果越好\n"
            "• 视频生成需要1-3分钟，请耐心等待\n"
            "• 生成失败会自动退款",
            reply_markup=get_back_to_menu_keyboard(),
        )

    # ==================== 管理员面板 ====================
    # 管理员白名单过滤：非管理员点击管理面板相关按钮时拦截
    admin_callback_prefixes = [
        "admin_panel", "admin_today_stats", "admin_user_mgmt_page_",
        "admin_recharge_select_user_page_", "admin_view_user_",
        "admin_recharge_user_", "admin_tier_",
        "admin_toggle_ratelimit", "admin_set_global_rpm",
        "admin_set_per_user_rpm", "admin_toggle_half_price",
        "admin_confirm_recharge_", "admin_reject_recharge_",
        "管理面板",  # 兼容中文 callback_data
    ]
    is_admin_callback = any(data == p or data.startswith(p) for p in admin_callback_prefixes)
    if is_admin_callback and not is_admin(user_id):
        await message.edit_text(
            "🔒 此功能仅限管理员使用",
            reply_markup=get_back_to_menu_keyboard(),
        )
        return

    elif data == "admin_panel":
        await message.edit_text(
            "🛠️ 管理面板\n\n选择你要执行的操作：",
            reply_markup=get_admin_panel_keyboard(),
        )

    elif data == "管理面板":
        # 兼容中文 callback_data
        await message.edit_text(
            "🛠️ 管理面板\n\n选择你要执行的操作：",
            reply_markup=get_admin_panel_keyboard(),
        )

    elif data == "admin_today_stats":
        from database import get_today_stats
        stats = get_today_stats()
        msg = (
            f"📊 今日统计\n\n"
            f"👥 新增用户: {stats['new_users']}\n"
            f"💰 充值总额: {stats['income']} 积分\n"
            f"📈 活跃用户: {stats['active_users']}"
        )
        await message.edit_text(msg, reply_markup=get_back_to_menu_keyboard())

    elif data.startswith("admin_user_mgmt_page_"):
        """用户管理分页"""
        page = int(data.split("_")[-1])
        from database import get_all_users
        all_users = get_all_users(100)
        per_page = 10
        total_pages = max(1, (len(all_users) + per_page - 1) // per_page)
        page = min(page, total_pages)
        
        start = (page - 1) * per_page
        end = start + per_page
        page_users = all_users[start:end]
        
        if not page_users:
            await message.edit_text("👥 暂无用户")
            return
        
        msg = f"👥 用户管理 ({page}/{total_pages})\n{'━' * 20}\n"
        for i, u in enumerate(page_users, start=start + 1):
            name = u.get('first_name', '') or u.get('username', '') or f"用户{u['user_id']}"
            msg += f"\n{i}. {name}\n"
            msg += f"   💰 余额: {u['credits']} | 🎨 生成: {u['total_generated']}"
        msg += f"\n{'━' * 20}"
        
        # 每行用户后面加操作按钮
        kb_rows = []
        for u in page_users:
            name = u.get('first_name', '') or u.get('username', '') or f"用户{u['user_id']}"
            kb_rows.append([
                InlineKeyboardButton(f"👁️ {name}", callback_data=f"admin_view_user_{u['user_id']}"),
                InlineKeyboardButton(f"💰 充值", callback_data=f"admin_recharge_user_{u['user_id']}"),
            ])
        
        # 分页按钮
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"admin_user_mgmt_page_{page-1}"))
        if page < total_pages:
            pagination_buttons.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"admin_user_mgmt_page_{page+1}"))
        if not pagination_buttons:
            pagination_buttons.append(InlineKeyboardButton("🏠 返回", callback_data="back_to_menu"))
        else:
            pagination_buttons.append(InlineKeyboardButton("🏠 返回", callback_data="back_to_menu"))
        kb_rows.append(pagination_buttons)
        
        await message.edit_text(msg, reply_markup=InlineKeyboardMarkup(kb_rows))

    elif data.startswith("admin_recharge_select_user_page_"):
        """充值选用户分页"""
        page = int(data.split("_")[-1])
        from database import get_all_users
        all_users = get_all_users(100)
        per_page = 10
        total_pages = max(1, (len(all_users) + per_page - 1) // per_page)
        page = min(page, total_pages)
        
        start = (page - 1) * per_page
        end = start + per_page
        page_users = all_users[start:end]
        
        if not page_users:
            await message.edit_text("💰 暂无用户")
            return
        
        msg = f"💰 手动充值 ({page}/{total_pages})\n{'━' * 20}\n"
        for i, u in enumerate(page_users, start=start + 1):
            name = u.get('first_name', '') or u.get('username', '') or f"用户{u['user_id']}"
            msg += f"\n{i}. {name}\n"
            msg += f"   ID: {u['user_id']} | 💰 余额: {u['credits']}"
        msg += f"\n{'━' * 20}"
        
        kb_rows = []
        for u in page_users:
            name = u.get('first_name', '') or u.get('username', '') or f"用户{u['user_id']}"
            kb_rows.append([InlineKeyboardButton(f"💰 给 {name} 充值", callback_data=f"admin_recharge_user_{u['user_id']}")])
        
        # 分页按钮
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"admin_recharge_select_user_page_{page-1}"))
        if page < total_pages:
            pagination_buttons.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"admin_recharge_select_user_page_{page+1}"))
        if not pagination_buttons:
            pagination_buttons.append(InlineKeyboardButton("🏠 返回", callback_data="back_to_menu"))
        else:
            pagination_buttons.append(InlineKeyboardButton("🏠 返回", callback_data="back_to_menu"))
        kb_rows.append(pagination_buttons)
        
        await message.edit_text(msg, reply_markup=InlineKeyboardMarkup(kb_rows))

    elif data.startswith("admin_view_user_"):
        """查看用户详情"""
        user_id_str = data.replace("admin_view_user_", "")
        from database import get_or_create_user
        user = get_or_create_user(int(user_id_str))
        if not user:
            await message.edit_text("❌ 用户不存在")
            return
        await message.edit_text(
            f"👤 用户详情\n\n"
            f"昵称: {user.get('first_name', '-') or user.get('username', '-')}\n"
            f"ID: {user['user_id']}\n"
            f"💰 余额: {user['credits']}\n"
            f"🎨 累计生成: {user['total_generated']}\n"
            f"📅 注册: {user.get('created_at', '-')}\n"
            f"{'👑 管理员' if user.get('is_admin') else '👤 普通用户'}",
            reply_markup=get_back_to_menu_keyboard(),
        )

    elif data.startswith("admin_recharge_user_"):
        """选择充值档位"""
        user_id_str = data.replace("admin_recharge_user_", "")
        from database import get_or_create_user
        user = get_or_create_user(int(user_id_str))
        if not user:
            await message.edit_text("❌ 用户不存在")
            return
        
        name = user.get('first_name', '') or user.get('username', '') or f"用户{user['user_id']}"
        msg = (
            f"💰 给 {name} 充值\n\n"
            f"用户ID: {user['user_id']}\n"
            f"当前余额: {user['credits']}\n\n"
            f"请选择充值档位："
        )
        await message.edit_text(
            msg,
            reply_markup=get_admin_recharge_tier_keyboard(user['user_id']),
        )

    elif data.startswith("admin_tier_"):
        """管理员选择充值档位"""
        parts = data.split("_")
        user_id_str = parts[2]
        tier_name = "_".join(parts[3:])
        
        from database import confirm_admin_recharge, get_or_create_user
        tier = RECHARGE_TIERS.get(tier_name, {})
        if not tier:
            await message.edit_text("❌ 档位不存在")
            return
        
        total_credits = tier.get("credits", 0) + tier.get("bonus", 0)
        success = confirm_admin_recharge(int(user_id_str), tier_name, tier.get("usdt", 0), total_credits)
        
        if success:
            user = get_or_create_user(int(user_id_str))
            await message.edit_text(
                f"✅ 充值成功！\n\n"
                f"用户: {user.get('first_name', '-') or user.get('username', '-')}\n"
                f"档位: {tier_name}\n"
                f"金额: ${tier.get('usdt', 0)}\n"
                f"充值: {total_credits} 积分\n"
                f"当前余额: {user['credits']}",
                reply_markup=get_back_to_menu_keyboard(),
            )
        else:
            await message.edit_text("❌ 充值失败，请重试")

    # ==================== 流控管理回调 ====================
    elif data == "admin_toggle_ratelimit":
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT enabled FROM rate_limits WHERE id=1")
        row = cursor.fetchone()
        if row:
            new_enabled = 0 if row["enabled"] else 1
            cursor.execute("UPDATE rate_limits SET enabled = ? WHERE id=1", (new_enabled,))
            conn.commit()
            status = "🔴 已暂停" if new_enabled == 0 else "🟢 已开启"
            await message.edit_text(
                f"⚡ 流控状态已更改: {status}",
                reply_markup=get_back_to_menu_keyboard(),
            )
        conn.close()

    elif data.startswith("admin_set_global_rpm"):
        await message.edit_text(
            f"📝 请输入新的全局 RPM 值（每分钟最大请求数）\n\n"
            f"当前值: 60\n"
            f"建议范围: 10-300",
            reply_markup=get_back_to_menu_keyboard(),
        )
        # 将用户状态切换到等待输入全局RPM
        user_states[query.from_user.id] = {"mode": "waiting_admin_rpm", "rpm_type": "global"}

    elif data.startswith("admin_set_per_user_rpm"):
        await message.edit_text(
            f"📝 请输入新的单用户 RPM 值（每个用户每分钟最大请求数）\n\n"
            f"当前值: 5\n"
            f"建议范围: 1-30",
            reply_markup=get_back_to_menu_keyboard(),
        )
        user_states[query.from_user.id] = {"mode": "waiting_admin_rpm", "rpm_type": "per_user"}

    elif data == "admin_toggle_half_price":
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT group_half_price FROM rate_limits WHERE id=1")
        row = cursor.fetchone()
        if row:
            new_val = 0 if row["group_half_price"] else 1
            cursor.execute("UPDATE rate_limits SET group_half_price = ? WHERE id=1", (new_val,))
            conn.commit()
            status = "🟢 已启用" if new_val else "🔴 已禁用"
            await message.edit_text(
                f"💰 群聊半价功能: {status}",
                reply_markup=get_back_to_menu_keyboard(),
            )
        conn.close()

    # ==================== 充值确认/拒绝回调 ====================
    elif data.startswith("admin_confirm_recharge_"):
        parts = data.split("_")
        # admin_confirm_recharge_REQUESTID_ADMINID → parts[3]
        request_id = int(parts[3])
        from database import confirm_recharge
        success = confirm_recharge(request_id)
        if success:
            await message.edit_text(
                f"✅ 充值请求 #{request_id} 已确认处理",
                reply_markup=get_back_to_menu_keyboard(),
            )
        else:
            await message.edit_text(
                f"❌ 充值请求 #{request_id} 处理失败，请重试",
                reply_markup=get_back_to_menu_keyboard(),
            )

    elif data.startswith("admin_reject_recharge_"):
        parts = data.split("_")
        # admin_reject_recharge_REQUESTID_ADMINID → parts[3]
        request_id = int(parts[3])
        from database import reject_recharge
        success = reject_recharge(request_id)
        if success:
            await message.edit_text(
                f"❌ 充值请求 #{request_id} 已拒绝",
                reply_markup=get_back_to_menu_keyboard(),
            )
        else:
            await message.edit_text(
                f"❌ 充值请求 #{request_id} 拒绝失败，请重试",
                reply_markup=get_back_to_menu_keyboard(),
            )

    else:
        await message.edit_text(
            "🤔 未知操作，请重新选择",
            reply_markup=get_back_to_menu_keyboard(),
        )


async def notify_admin_recharge(user_id, request_id, tier_name, req, context):
    """通知管理员有新的充值请求"""
    from config import ADMIN_IDS
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    
    for admin_id in ADMIN_IDS:
        try:
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ 确认充值", callback_data=f"admin_confirm_recharge_{request_id}_{admin_id}"),
                    InlineKeyboardButton("❌ 拒绝", callback_data=f"admin_reject_recharge_{request_id}_{admin_id}"),
                ],
                [InlineKeyboardButton("🏠 返回管理面板", callback_data="admin_panel")],
            ])
            msg = (
                f"💰 新的充值请求\n\n"
                f"用户ID: {user_id}\n"
                f"充值档位: {tier_name}\n"
                f"金额: ${req['usdt_amount']}\n"
                f"积分: {req['total_credits']}\n\n"
                f"请核实转账后点击确认"
            )
            await context.bot.send_message(
                chat_id=admin_id,
                text=msg,
                parse_mode="Markdown",
                reply_markup=kb,
            )
        except Exception as e:
            import logging
            logging.getLogger().error(f"通知管理员失败: {e}")


# ==================== 图片发送工具函数 ====================

async def download_and_send_photo(message, img_url, caption=None):
    """
    下载图片到本地，然后通过文件上传发送到 Telegram
    解决 Telegram 无法直接访问 Agnes AI 图片 URL 的问题
    """
    temp_dir = "temp_images"
    os.makedirs(temp_dir, exist_ok=True)
    
    import uuid
    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(temp_dir, filename)
    
    try:
        # 下载图片
        async with httpx.AsyncClient(timeout=120, verify=False) as client:
            r = await client.get(img_url)
            r.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(r.content)
        
        # 通过文件上传发送（Telegram 会接受本地文件）
        with open(filepath, 'rb') as photo:
            await message.reply_photo(
                photo=photo,
                caption=caption,
            )
        
        # 发送成功后删除临时文件
        os.remove(filepath)
        return True
        
    except Exception as e:
        # 出错也尝试删除临时文件
        try:
            os.remove(filepath)
        except:
            pass
        await message.reply_text(f"❌ 图片发送失败: {str(e)}")
        return False


# ==================== 文生图 ====================

async def execute_text2img(message, user_id, prompt, size, ratio, context):
    """用 message 对象执行文生图"""
    from database import spend_credits, get_user_credits, increment_generated_count, update_credits
    from agnes_client import agnes_client
    from config import CREDIT_COSTS

    cost = CREDIT_COSTS["text2img"]

    credits = get_user_credits(user_id)
    if credits is None or credits < cost:
        await message.reply_text(
            f"❌ 积分不足！\n"
            f"当前积分: {credits}\n"
            f"文生图需要: {cost} 积分\n"
            f"请点击「充值积分」充值后再试"
        )
        return

    if not spend_credits(user_id, cost):
        await message.reply_text("❌ 积分扣费失败，请重试")
        return

    size_label = {"1K": "1024×1024", "2K": "2048×2048", "3K": "3072×3072", "4K": "4096×4096"}
    await message.reply_text(
        f"🎨 开始生成图片...\n"
        f"尺寸: {size_label.get(size, size)}\n"
        f"比例: {ratio}\n"
        f"消耗: {cost} 积分\n"
        f"预计需要 10-30 秒"
    )

    # 调用 API（先增强 prompt）
    enhanced_prompt = enhance_t2i(prompt)
    result = await agnes_client.text_to_image(enhanced_prompt, size=size, ratio=ratio)

    if result.get("url"):
        increment_generated_count(user_id)
        # 下载图片并通过文件发送
        success = await download_and_send_photo(
            message,
            result["url"],
            caption=f"✅ 生成完成！\n"
                    f"尺寸: {size_label.get(size, size)}\n"
                    f"比例: {ratio}\n"
                    f"消耗: {cost} 积分"
        )
        if not success:
            update_credits(user_id, cost, "refund", "图片发送失败退款")
            await message.reply_text("❌ 图片发送失败，积分已退还")
    else:
        update_credits(user_id, cost, "refund", f"文生图失败退款: {result.get('error')}")
        await message.reply_text(f"❌ 生成失败: {result.get('error')}\n积分已退还")


# ==================== 图片编辑 ====================

async def execute_img2img(message, user_id, image_url, edit_prompt, size, ratio, context):
    """用 message 对象执行图片编辑"""
    from database import spend_credits, get_user_credits, increment_generated_count, update_credits
    from agnes_client import agnes_client
    from config import CREDIT_COSTS

    cost = CREDIT_COSTS["img2img"]

    credits = get_user_credits(user_id)
    if credits is None or credits < cost:
        await message.reply_text(
            f"❌ 积分不足！\n"
            f"当前积分: {credits}\n"
            f"图片编辑需要: {cost} 积分\n"
            f"请点击「充值积分」充值后再试"
        )
        return

    if not spend_credits(user_id, cost):
        await message.reply_text("❌ 积分扣费失败，请重试")
        return

    size_label = {"1K": "1024×1024", "2K": "2048×2048", "3K": "3072×3072", "4K": "4096×4096"}
    await message.reply_text(
        f"🖼️ 开始编辑图片...\n"
        f"尺寸: {size_label.get(size, size)}\n"
        f"比例: {ratio}\n"
        f"消耗: {cost} 积分\n"
        f"预计需要 10-30 秒"
    )

    # 增强 prompt 后调用 API
    enhanced_prompt = enhance_i2i(edit_prompt)
    result = await agnes_client.image_to_image(enhanced_prompt, image_url, size=size, ratio=ratio)

    if result.get("url"):
        increment_generated_count(user_id)
        success = await download_and_send_photo(
            message,
            result["url"],
            caption=f"✅ 编辑完成！\n"
                    f"尺寸: {size_label.get(size, size)}\n"
                    f"比例: {ratio}\n"
                    f"消耗: {cost} 积分"
        )
        if not success:
            update_credits(user_id, cost, "refund", "图片发送失败退款")
            await message.reply_text("❌ 图片发送失败，积分已退还")
    else:
        update_credits(user_id, cost, "refund", f"图片编辑失败退款: {result.get('error')}")
        await message.reply_text(f"❌ 编辑失败: {result.get('error')}\n积分已退还")


# ==================== 文生视频 ====================

async def execute_text2vid(message, user_id, prompt, ratio, context):
    """用 message 对象执行文生视频"""
    from database import spend_credits, get_user_credits, increment_generated_count, save_video_task, update_credits
    from agnes_client import agnes_client
    from config import CREDIT_COSTS, VIDEO_POLL_INTERVAL, VIDEO_POLL_TIMEOUT
    import asyncio

    cost = CREDIT_COSTS["text2vid"]

    credits = get_user_credits(user_id)
    if credits is None or credits < cost:
        await message.reply_text(f"❌ 积分不足！当前: {credits}，需要: {cost}")
        return

    if not spend_credits(user_id, cost):
        await message.reply_text("❌ 积分扣费失败，请重试")
        return

    # 增强 prompt 后创建视频任务
    enhanced_prompt = enhance_t2v(prompt)
    result = await agnes_client.create_video_task(enhanced_prompt, ratio=ratio, duration=5)

    if result.get("error"):
        update_credits(user_id, cost, "refund", f"文生视频创建失败: {result['error']}")
        await message.reply_text(f"❌ 创建失败: {result['error']}\n积分已退还")
        return

    task_id = result.get("task_id")
    video_id = result.get("video_id")

    if not task_id:
        update_credits(user_id, cost, "refund", "创建视频任务无返回值")
        await message.reply_text("❌ 创建任务失败，积分已退还")
        return

    save_video_task(task_id, user_id, "text2vid", video_id, prompt)

    await message.reply_text(
        f"🎬 视频任务已创建！\n"
        f"任务ID: {task_id}\n"
        f"预计 1-3 分钟"
    )

    asyncio.create_task(poll_video_for_message(message, user_id, task_id, video_id, cost))


# ==================== 图生视频 ====================

async def execute_img2vid(message, user_id, image_url, prompt, ratio, context):
    """用 message 对象执行图生视频"""
    from database import spend_credits, get_user_credits, increment_generated_count, save_video_task, update_credits
    from agnes_client import agnes_client
    from config import CREDIT_COSTS, VIDEO_POLL_INTERVAL, VIDEO_POLL_TIMEOUT
    import asyncio

    cost = CREDIT_COSTS["img2vid"]

    credits = get_user_credits(user_id)
    if credits is None or credits < cost:
        await message.reply_text(f"❌ 积分不足！当前: {credits}，需要: {cost}")
        return

    if not spend_credits(user_id, cost):
        await message.reply_text("❌ 积分扣费失败，请重试")
        return

    # 增强 prompt 后创建图生视频任务
    enhanced_prompt = enhance_i2v(prompt)
    result = await agnes_client.create_video_task(enhanced_prompt, image_url=image_url, ratio=ratio, duration=5)

    if result.get("error"):
        update_credits(user_id, cost, "refund", f"图生视频创建失败: {result['error']}")
        await message.reply_text(f"❌ 创建失败: {result['error']}\n积分已退还")
        return

    task_id = result.get("task_id")
    video_id = result.get("video_id")

    if not task_id:
        update_credits(user_id, cost, "refund", "创建视频任务无返回值")
        await message.reply_text("❌ 创建任务失败，积分已退还")
        return

    save_video_task(task_id, user_id, "img2vid", video_id, prompt)

    await message.reply_text(
        f"🎥 视频任务已创建！\n"
        f"任务ID: {task_id}\n"
        f"预计 1-3 分钟"
    )

    asyncio.create_task(poll_video_for_message(message, user_id, task_id, video_id, cost))


# ==================== 视频轮询 ====================

async def poll_video_for_message(message, user_id, task_id, video_id, cost):
    """轮询视频结果（使用 message 对象）"""
    import asyncio
    from agnes_client import agnes_client
    from database import get_pending_video_tasks, update_video_task, increment_generated_count, update_credits
    from config import VIDEO_POLL_INTERVAL, VIDEO_POLL_TIMEOUT

    try:
        await asyncio.sleep(10)

        for i in range(VIDEO_POLL_TIMEOUT // VIDEO_POLL_INTERVAL):
            pending = get_pending_video_tasks()
            task = next((t for t in pending if t["task_id"] == task_id), None)
            if not task:
                break

            result = await agnes_client.poll_video_result(video_id)
            status = result.get("status")
            progress = result.get("progress", 0)

            if status == "completed" and result.get("url"):
                update_video_task(task_id, "completed", result["url"])
                increment_generated_count(user_id)
                
                # 视频也下载到本地发送
                temp_dir = "temp_videos"
                os.makedirs(temp_dir, exist_ok=True)
                import uuid
                vid_filename = f"{uuid.uuid4().hex}.mp4"
                vid_filepath = os.path.join(temp_dir, vid_filename)
                
                try:
                    async with httpx.AsyncClient(timeout=120, verify=False) as client:
                        r = await client.get(result["url"])
                        r.raise_for_status()
                        with open(vid_filepath, 'wb') as f:
                            f.write(r.content)
                    
                    with open(vid_filepath, 'rb') as video:
                        await message.reply_video(
                            video=video,
                            caption=f"✅ 视频生成完成！\n"
                                    f"时长: {result.get('seconds', '5')}秒\n"
                                    f"分辨率: {result.get('size', '720p')}\n"
                                    f"消耗: {cost} 积分"
                        )
                    
                    os.remove(vid_filepath)
                except Exception as e:
                    try:
                        os.remove(vid_filepath)
                    except:
                        pass
                    await message.reply_text(f"❌ 视频发送失败: {str(e)}\n积分已退还")
                    update_credits(user_id, cost, "refund", "视频发送失败退款")
                return

            elif status == "failed":
                update_video_task(task_id, "refunded")
                update_credits(user_id, cost, "refund", f"视频生成失败: {result.get('error')}")
                await message.reply_text(f"❌ 视频生成失败: {result.get('error')}\n积分已退还")
                return

            await asyncio.sleep(VIDEO_POLL_INTERVAL)

        # 超时
        update_video_task(task_id, "refunded")
        update_credits(user_id, cost, "refund", "视频生成超时")
        await message.reply_text("⏰ 视频生成超时，积分已退还")

    except Exception as e:
        update_credits(user_id, cost, "refund", f"视频轮询异常: {str(e)}")
        await message.reply_text(f"❌ 视频生成出错: {str(e)}\n积分已退还")
