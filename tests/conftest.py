"""
TDD 阶段 — pytest 共享 fixtures
阶段：TDD 算法实现

提供：
- app: Flask 测试客户端
- db: 内存 SQLite 数据库（含完整测试数据）
"""
import os
import sys
import sqlite3
import pytest
import numpy as np

# 将项目根目录加入 sys.path，确保能导入 app/database/dina_model
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app as flask_app
from database import get_connection

# 固定随机种子，确保测试可复现
np.random.seed(42)

# ────────────────────────────────────────────
# 常量定义
# ────────────────────────────────────────────
NUM_KNOWLEDGE_POINTS = 5
NUM_QUESTIONS = 20
NUM_STUDENTS = 12  # ≥10

KP_NAMES = ["加法", "减法", "乘法", "除法", "混合运算"]

# Q 矩阵设计 (20 题 × 5 知识点)
# 每行对应一道题，每列对应一个知识点，1 = 考查
# 每个知识点至少被 3 道题覆盖
Q_MATRIX_DATA = {
    # question_id: [KP1, KP2, KP3, KP4, KP5]
    1:  [1, 0, 0, 0, 0],   # 纯加法
    2:  [1, 0, 0, 0, 0],   # 纯加法
    3:  [1, 0, 0, 0, 0],   # 纯加法
    4:  [1, 1, 0, 0, 0],   # 加法 + 减法
    5:  [0, 1, 0, 0, 0],   # 纯减法
    6:  [0, 1, 0, 0, 0],   # 纯减法
    7:  [0, 1, 0, 0, 0],   # 纯减法
    8:  [0, 1, 1, 0, 0],   # 减法 + 乘法
    9:  [0, 0, 1, 0, 0],   # 纯乘法
    10: [0, 0, 1, 0, 0],   # 纯乘法
    11: [0, 0, 1, 0, 0],   # 纯乘法
    12: [0, 0, 1, 1, 0],   # 乘法 + 除法
    13: [0, 0, 0, 1, 0],   # 纯除法
    14: [0, 0, 0, 1, 0],   # 纯除法
    15: [0, 0, 0, 1, 0],   # 纯除法
    16: [0, 0, 0, 1, 1],   # 除法 + 混合运算
    17: [0, 0, 0, 0, 1],   # 纯混合运算
    18: [0, 0, 0, 0, 1],   # 纯混合运算
    19: [1, 0, 0, 0, 1],   # 加法 + 混合运算
    20: [0, 1, 1, 1, 1],   # 综合题：减法+乘法+除法+混合运算
}

# 知识图谱有向边（6 条）
KG_EDGES = [
    (1, 3),   # 加法 → 乘法
    (2, 3),   # 减法 → 乘法
    (1, 4),   # 加法 → 除法
    (2, 4),   # 减法 → 除法
    (3, 5),   # 乘法 → 混合运算
    (4, 5),   # 除法 → 混合运算
]


def _create_tables(conn):
    """创建所有表结构（与 docs/SCHEMA.sql 完全一致）"""
    conn.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS knowledge_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS q_matrix (
            question_id INTEGER NOT NULL,
            knowledge_point_id INTEGER NOT NULL,
            is_covered INTEGER NOT NULL CHECK (is_covered IN (0, 1)),
            PRIMARY KEY (question_id, knowledge_point_id),
            FOREIGN KEY (question_id) REFERENCES questions(id),
            FOREIGN KEY (knowledge_point_id) REFERENCES knowledge_points(id)
        );

        CREATE TABLE IF NOT EXISTS x_matrix (
            student_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
            PRIMARY KEY (student_id, question_id),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        );

        CREATE TABLE IF NOT EXISTS knowledge_graph (
            predecessor_kp_id INTEGER NOT NULL,
            successor_kp_id INTEGER NOT NULL,
            PRIMARY KEY (predecessor_kp_id, successor_kp_id),
            FOREIGN KEY (predecessor_kp_id) REFERENCES knowledge_points(id),
            FOREIGN KEY (successor_kp_id) REFERENCES knowledge_points(id),
            CHECK (predecessor_kp_id != successor_kp_id)
        );

        CREATE INDEX IF NOT EXISTS idx_x_matrix_student ON x_matrix(student_id);
        CREATE INDEX IF NOT EXISTS idx_x_matrix_question ON x_matrix(question_id);
        CREATE INDEX IF NOT EXISTS idx_q_matrix_question ON q_matrix(question_id);
        CREATE INDEX IF NOT EXISTS idx_q_matrix_kp ON q_matrix(knowledge_point_id);
        CREATE INDEX IF NOT EXISTS idx_kg_predecessor ON knowledge_graph(predecessor_kp_id);
        CREATE INDEX IF NOT EXISTS idx_kg_successor ON knowledge_graph(successor_kp_id);
    """)


def _insert_seed_data(conn):
    """插入测试种子数据：5 知识点、20 题、Q 矩阵、12 名学生、X 矩阵、知识图谱"""
    cursor = conn.cursor()

    # --- 知识点 ---
    for name in KP_NAMES:
        cursor.execute("INSERT INTO knowledge_points (name) VALUES (?)", (name,))

    # --- 题目 ---
    for qid in range(1, NUM_QUESTIONS + 1):
        cursor.execute(
            "INSERT INTO questions (content) VALUES (?)",
            (f"题目{qid:02d}：算术运算测试题 #{qid}",)
        )

    # --- Q 矩阵 ---
    for qid, kp_flags in Q_MATRIX_DATA.items():
        for kp_idx, covered in enumerate(kp_flags, start=1):
            cursor.execute(
                "INSERT INTO q_matrix (question_id, knowledge_point_id, is_covered) VALUES (?, ?, ?)",
                (qid, kp_idx, covered)
            )

    # --- 学生 ---
    for sid in range(1, NUM_STUDENTS + 1):
        cursor.execute(
            "INSERT INTO students (name) VALUES (?)",
            (f"学生{sid:02d}",)
        )

    # --- X 矩阵（随机生成 0/1，seed=42 保证可复现）---
    for sid in range(1, NUM_STUDENTS + 1):
        for qid in range(1, NUM_QUESTIONS + 1):
            is_correct = int(np.random.rand() > 0.4)  # 约 60% 正确率
            cursor.execute(
                "INSERT INTO x_matrix (student_id, question_id, is_correct) VALUES (?, ?, ?)",
                (sid, qid, is_correct)
            )

    # --- 知识图谱 ---
    for pred, succ in KG_EDGES:
        cursor.execute(
            "INSERT INTO knowledge_graph (predecessor_kp_id, successor_kp_id) VALUES (?, ?)",
            (pred, succ)
        )

    conn.commit()


# ────────────────────────────────────────────
# pytest fixtures
# ────────────────────────────────────────────

@pytest.fixture
def db():
    """
    创建临时 SQLite 内存数据库，建表并插入完整测试数据。
    测试结束后自动清理。
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _create_tables(conn)
    _insert_seed_data(conn)
    yield conn
    conn.close()


@pytest.fixture
def app(db):
    """
    Flask 测试客户端。
    将 app 的数据库连接替换为测试数据库。
    """
    # 保存原始连接函数
    original_get_conn = __import__("database").get_connection

    # 注入测试数据库连接
    def _test_get_connection():
        return db

    import database
    database.get_connection = _test_get_connection

    flask_app.config["TESTING"] = True
    flask_app.config["DATABASE"] = ":memory:"

    with flask_app.test_client() as client:
        yield client

    # 恢复原始连接函数
    database.get_connection = original_get_conn


@pytest.fixture
def small_q_matrix():
    """
    简化版 Q 矩阵（2 题 × 2 知识点），用于 DINA 单元测试
    Q1 考查 KP1，Q2 考查 KP1 + KP2
    """
    return np.array([
        [1, 0],   # Q1: 仅 KP1
        [1, 1],   # Q2: KP1 + KP2
    ], dtype=np.int32)


@pytest.fixture
def small_x_matrix():
    """
    简化版 X 矩阵（10 学生 × 2 题），对应 small_q_matrix
    学生 0~4 两题全对（掌握 KP1+KP2），学生 5~9 仅 Q1 对（只掌握 KP1）
    """
    x = np.zeros((10, 2), dtype=np.int32)
    # 学生 0~4: 两题全对 (KP1 + KP2 都掌握)
    x[0:5, 0] = 1
    x[0:5, 1] = 1
    # 学生 5~9: 只对 Q1 (仅 KP1 掌握)
    x[5:10, 0] = 1
    x[5:10, 1] = 0
    return x
