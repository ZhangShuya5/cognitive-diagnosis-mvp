-- ============================================
-- 认知诊断系统 — 数据库 Schema
-- 阶段: SDD 建模
-- 数据库: SQLite 3.x
-- ============================================

PRAGMA foreign_keys = ON;

-- 学生表
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

-- 题目表
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL
);

-- 知识点表（5 个知识点）
CREATE TABLE IF NOT EXISTS knowledge_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Q 矩阵关联表（20 题 × 5 知识点 = 100 条）
CREATE TABLE IF NOT EXISTS q_matrix (
    question_id INTEGER NOT NULL,
    knowledge_point_id INTEGER NOT NULL,
    is_covered INTEGER NOT NULL CHECK (is_covered IN (0, 1)),
    PRIMARY KEY (question_id, knowledge_point_id),
    FOREIGN KEY (question_id) REFERENCES questions(id),
    FOREIGN KEY (knowledge_point_id) REFERENCES knowledge_points(id)
);

-- X 矩阵作答表（≥10 名学生 × 20 题 = ≥200 条）
CREATE TABLE IF NOT EXISTS x_matrix (
    student_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    PRIMARY KEY (student_id, question_id),
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (question_id) REFERENCES questions(id)
);

-- 知识图谱前驱后继表（≥4 条有向边）
CREATE TABLE IF NOT EXISTS knowledge_graph (
    predecessor_kp_id INTEGER NOT NULL,
    successor_kp_id INTEGER NOT NULL,
    PRIMARY KEY (predecessor_kp_id, successor_kp_id),
    FOREIGN KEY (predecessor_kp_id) REFERENCES knowledge_points(id),
    FOREIGN KEY (successor_kp_id) REFERENCES knowledge_points(id),
    CHECK (predecessor_kp_id != successor_kp_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_x_matrix_student ON x_matrix(student_id);
CREATE INDEX IF NOT EXISTS idx_x_matrix_question ON x_matrix(question_id);
CREATE INDEX IF NOT EXISTS idx_q_matrix_question ON q_matrix(question_id);
CREATE INDEX IF NOT EXISTS idx_q_matrix_kp ON q_matrix(knowledge_point_id);
CREATE INDEX IF NOT EXISTS idx_kg_predecessor ON knowledge_graph(predecessor_kp_id);
CREATE INDEX IF NOT EXISTS idx_kg_successor ON knowledge_graph(successor_kp_id);
