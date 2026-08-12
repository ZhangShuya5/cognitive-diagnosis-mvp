"""
认知诊断作业 — 数据库连接模块
阶段：环境初始化
"""
import sqlite3
import os


def get_db_path():
    """获取数据库文件路径"""
    instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance")
    os.makedirs(instance_dir, exist_ok=True)
    return os.path.join(instance_dir, "cognitive_diag.db")


def get_connection():
    """获取 SQLite 数据库连接"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表结构（占位，后续阶段补全）"""
    conn = get_connection()
    cursor = conn.cursor()
    # 后续 SDD 建模阶段将在此创建表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _env_check (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO _env_check (id, message) VALUES (1, 'env ok')")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("[database] 数据库初始化完成")
