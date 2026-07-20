"""
智造AI创意工坊 - 数据库模块
SQLite轻量数据库，用户数据+积分+视频任务台账
"""
import sqlite3
import os
from datetime import datetime
from config import DATABASE_PATH


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_connection()
    cursor = conn.cursor()

    # 用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            credits REAL DEFAULT 50,
            total_generated INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_admin INTEGER DEFAULT 0
        )
    """)

    # 视频任务表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_tasks (
            task_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('text2vid', 'img2vid')),
            status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued', 'in_progress', 'completed', 'failed', 'refunded')),
            video_id TEXT,
            prompt TEXT,
            result_url TEXT,
            refunded INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # 充值记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credit_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            usdt_amount REAL,
            tier_name TEXT,
            type TEXT NOT NULL CHECK(type IN ('recharge', 'admin_add', 'spend', 'refund')),
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # 充值请求表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recharge_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tier_name TEXT NOT NULL,
            usdt_amount REAL NOT NULL,
            total_credits REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'confirmed', 'rejected')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_tasks_user ON video_tasks(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_tasks_status ON video_tasks(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON credit_transactions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_type ON credit_transactions(type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recharge_requests_user ON recharge_requests(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recharge_requests_status ON recharge_requests(status)")

    # 流控设置表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
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
    conn.close()
    print("✅ 数据库初始化完成")


def get_or_create_user(user_id, username=None, first_name=None, last_name=None, is_admin=0):
    """获取或创建用户"""
    conn = get_connection()
    cursor = conn.cursor()

    # 检查用户是否存在
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if user:
        conn.close()
        return dict(user)

    # 新用户，赠送初始积分
    cursor.execute("""
        INSERT INTO users (user_id, username, first_name, last_name, credits, is_admin)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, username, first_name, last_name, 50, is_admin))

    conn.commit()
    conn.close()
    print(f"🆕 新用户注册: {first_name or username} (ID: {user_id}), 赠送50积分")
    return {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "credits": 50.0,
        "total_generated": 0,
        "created_at": datetime.now().isoformat(),
        "is_admin": is_admin
    }


def update_credits(user_id, amount, transaction_type="spend", description="", usdt_amount=0, tier_name=""):
    """
    更新用户积分
    :param user_id: 用户ID
    :param amount: 积分变动（正数增加，负数减少）
    :param transaction_type: 交易类型 (recharge/admin_add/spend/refund)
    :param description: 描述
    :param usdt_amount: USDT金额
    :param tier_name: 充值档位名称
    :return: 更新后的积分
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 检查当前积分
    cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return None

    new_credits = user["credits"] + amount
    cursor.execute("UPDATE users SET credits = ? WHERE user_id = ?", (new_credits, user_id))

    # 记录交易
    cursor.execute("""
        INSERT INTO credit_transactions (user_id, amount, usdt_amount, tier_name, type, description)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, amount, usdt_amount, tier_name, transaction_type, description))

    conn.commit()
    conn.close()
    return new_credits


def spend_credits(user_id, amount):
    """扣除积分，余额不足返回False"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user or user["credits"] < amount:
        conn.close()
        return False

    cursor.execute("UPDATE users SET credits = credits - ? WHERE user_id = ?", (amount, user_id))
    cursor.execute("""
        INSERT INTO credit_transactions (user_id, amount, type, description)
        VALUES (?, ?, 'spend', ?)
    """, (user_id, -amount, f"使用积分: {amount}"))

    conn.commit()
    conn.close()
    return True


def get_user_credits(user_id):
    """获取用户积分"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user["credits"] if user else None


def increment_generated_count(user_id):
    """累计生成次数+1"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET total_generated = total_generated + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def save_video_task(task_id, user_id, vid_type, video_id, prompt):
    """保存视频任务"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO video_tasks (task_id, user_id, type, video_id, prompt, status)
        VALUES (?, ?, ?, ?, ?, 'queued')
    """, (task_id, user_id, vid_type, video_id, prompt))
    conn.commit()
    conn.close()


def update_video_task(task_id, status, result_url=None, video_id=None):
    """更新视频任务状态"""
    conn = get_connection()
    cursor = conn.cursor()
    if status == "completed":
        cursor.execute("""
            UPDATE video_tasks SET status = ?, result_url = ?, completed_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """, (status, result_url, task_id))
    else:
        cursor.execute("""
            UPDATE video_tasks SET status = ? WHERE task_id = ?
        """, (status, task_id))
    conn.commit()
    conn.close()


def get_pending_video_tasks():
    """获取所有待处理/处理中的视频任务（服务重启后恢复轮询用）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM video_tasks WHERE status IN ('queued', 'in_progress')
    """)
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks


def get_user_stats(user_id):
    """获取用户统计信息"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT credits, total_generated, created_at
        FROM users WHERE user_id = ?
    """, (user_id,))
    user = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN type='recharge' OR type='admin_add' THEN 1 ELSE 0 END) as recharge_count,
               SUM(CASE WHEN type='spend' THEN 1 ELSE 0 END) as spend_count
        FROM credit_transactions WHERE user_id = ?
    """, (user_id,))
    stats = cursor.fetchone()
    conn.close()

    if not user:
        return None

    return {
        "credits": user["credits"],
        "total_generated": user["total_generated"],
        "created_at": user["created_at"],
        "recharge_count": stats["recharge_count"] or 0,
        "spend_count": stats["spend_count"] or 0,
    }


def get_today_stats():
    """获取今日统计数据"""
    conn = get_connection()
    cursor = conn.cursor()

    # 今日新增用户
    cursor.execute("""
        SELECT COUNT(*) FROM users
        WHERE DATE(created_at) = DATE('now')
    """)
    new_users = cursor.fetchone()[0]

    # 今日总收入/支出（积分金额，非美元）
    cursor.execute("""
        SELECT
            SUM(CASE WHEN type IN ('recharge', 'admin_add') THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN type = 'spend' THEN ABS(amount) ELSE 0 END) as expense,
            COUNT(*) as total_transactions
        FROM credit_transactions
        WHERE DATE(created_at) = DATE('now', '+8 hours')
    """)
    finance = cursor.fetchone()

    # 今日活跃用户
    cursor.execute("""
        SELECT COUNT(DISTINCT user_id) FROM credit_transactions
        WHERE DATE(created_at) = DATE('now')
    """)
    active_users = cursor.fetchone()[0]

    conn.close()
    return {
        "new_users": new_users,
        "income": finance[0] or 0,
        "expense": finance[1] or 0,
        "total_transactions": finance[2] or 0,
        "active_users": active_users,
    }


def get_all_users(limit=100):
    """获取用户列表"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, username, first_name, last_name, credits, total_generated, created_at, is_admin
        FROM users ORDER BY created_at DESC LIMIT ?
    """, (limit,))
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


# ==================== 充值请求 ====================

def add_recharge_request(user_id, tier_name, usdt_amount, total_credits):
    """添加充值请求"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO recharge_requests (user_id, tier_name, usdt_amount, total_credits, status)
        VALUES (?, ?, ?, ?, 'pending')
    """, (user_id, tier_name, usdt_amount, total_credits))
    request_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return request_id


def get_recharge_request(request_id):
    """获取充值请求"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recharge_requests WHERE id = ?", (request_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_id_by_request(request_id):
    """获取充值请求的用户ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM recharge_requests WHERE id = ?", (request_id,))
    row = cursor.fetchone()
    conn.close()
    return row['user_id'] if row else None


def mark_recharge_pending(request_id):
    """标记充值请求为已确认"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE recharge_requests SET status = 'confirmed' WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()


def get_pending_recharges():
    """获取所有待处理的充值请求（管理员用）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.id, r.user_id, u.first_name, u.username, r.tier_name, r.usdt_amount, r.total_credits, r.created_at
        FROM recharge_requests r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.status = 'confirmed'
        ORDER BY r.created_at DESC
    """)
    requests = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return requests


def confirm_recharge(request_id):
    """管理员确认充值，给用户加积分"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取充值请求
    cursor.execute("SELECT * FROM recharge_requests WHERE id = ?", (request_id,))
    req = cursor.fetchone()
    if not req:
        conn.close()
        return False
    
    req = dict(req)
    user_id = req['user_id']
    total_credits = req['total_credits']
    
    # 给用户加积分
    cursor.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (total_credits, user_id))
    
    # 记录充值流水
    cursor.execute("""
        INSERT INTO credit_transactions (user_id, amount, usdt_amount, tier_name, type, description)
        VALUES (?, ?, ?, ?, 'recharge', '充值确认')
    """, (user_id, total_credits, req['usdt_amount'], req['tier_name']))
    
    # 更新请求状态
    cursor.execute("UPDATE recharge_requests SET status = 'completed' WHERE id = ?", (request_id,))
    
    conn.commit()
    conn.close()
    return True


def reject_recharge(request_id):
    """管理员拒绝充值"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE recharge_requests SET status = 'rejected' WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()
    return True


def confirm_admin_recharge(user_id, tier_name, usdt_amount, total_credits):
    """管理员手动给用户加积分"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 给用户加积分
    cursor.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (total_credits, user_id))
    
    # 记录充值流水
    cursor.execute("""
        INSERT INTO credit_transactions (user_id, amount, usdt_amount, tier_name, type, description)
        VALUES (?, ?, ?, ?, 'admin_add', '管理员手动充值')
    """, (user_id, total_credits, usdt_amount, tier_name))
    
    conn.commit()
    conn.close()
    return True

