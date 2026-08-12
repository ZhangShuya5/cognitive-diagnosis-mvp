"""
认知诊断作业 — Flask 主入口
阶段：前端可视化

提供认知诊断系统的 Web 服务，包含以下 API 端点：
    GET  /                       — 渲染前端主页
    GET  /api/health             — 健康检查
    GET  /api/students           — 学生列表
    GET  /api/questions          — 题目列表（含 Q 矩阵信息）
    GET  /api/diagnosis/<id>     — 学生诊断结果（DINA 掌握概率 + 雷达图数据）
    GET  /api/knowledge_graph    — 知识图谱结构
    POST /api/advice/<id>        — 学习建议（LLM / 模拟降级）
"""
import logging
import numpy as np
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

import database
from dina_model import estimate_slip_guess, compute_knowledge_prob
from llm_service import generate_advice

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 固定随机种子，确保诊断结果可复现
np.random.seed(42)

app = Flask(__name__)
CORS(app)

# 配置 SQLite 数据库路径
app.config["DATABASE"] = "instance/cognitive_diag.db"


# ═══════════════════════════════════════
# 页面路由
# ═══════════════════════════════════════

@app.route("/")
def index():
    """渲染前端主页"""
    return render_template("index.html")


@app.route("/api/health")
def health():
    """健康检查接口"""
    return jsonify({"status": "ok", "message": "前端可视化阶段"})


# ═══════════════════════════════════════
# API: 学生列表
# ═══════════════════════════════════════

@app.route("/api/students")
def api_students():
    """
    返回所有学生列表。

    Returns:
        JSON: {"students": [{"id": int, "name": str}, ...], "total": int}
    """
    conn = database.get_connection()
    rows = conn.execute("SELECT id, name FROM students ORDER BY id").fetchall()
    students = [{"id": r["id"], "name": r["name"]} for r in rows]
    return jsonify({"students": students, "total": len(students)})


# ═══════════════════════════════════════
# API: 题目列表（含 Q 矩阵信息）
# ═══════════════════════════════════════

@app.route("/api/questions")
def api_questions():
    """
    返回所有题目及每道题考查的知识点。

    Returns:
        JSON: {"questions": [{"id": int, "content": str,
                              "covered_knowledge_points": [int, ...]}, ...],
               "total": int}
    """
    conn = database.get_connection()

    # 获取所有题目
    q_rows = conn.execute("SELECT id, content FROM questions ORDER BY id").fetchall()

    # 获取 Q 矩阵（批量查询，避免 N+1）
    qm_rows = conn.execute(
        "SELECT question_id, knowledge_point_id FROM q_matrix WHERE is_covered = 1 ORDER BY question_id, knowledge_point_id"
    ).fetchall()

    # 构建 question_id → [kp_id, ...] 映射
    qm_map = {}
    for row in qm_rows:
        qid = row["question_id"]
        if qid not in qm_map:
            qm_map[qid] = []
        qm_map[qid].append(row["knowledge_point_id"])

    questions = []
    for q in q_rows:
        questions.append({
            "id": q["id"],
            "content": q["content"],
            "covered_knowledge_points": qm_map.get(q["id"], [])
        })

    return jsonify({"questions": questions, "total": len(questions)})


# ═══════════════════════════════════════
# API: 学生诊断结果
# ═══════════════════════════════════════

@app.route("/api/diagnosis/<int:student_id>")
def api_diagnosis(student_id):
    """
    返回指定学生在 5 个知识点上的掌握概率（DINA 后验估计）。
    """
    conn = database.get_connection()

    # --- 验证学生存在 ---
    student = conn.execute(
        "SELECT id, name FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    if student is None:
        return jsonify({"error": "student_not_found", "message": f"学生 ID={student_id} 不存在"}), 404

    # --- 加载 Q 矩阵 ---
    kp_rows = conn.execute("SELECT id, name FROM knowledge_points ORDER BY id").fetchall()
    n_kp = len(kp_rows)
    kp_names = [r["name"] for r in kp_rows]

    q_rows = conn.execute(
        "SELECT question_id, knowledge_point_id, is_covered FROM q_matrix ORDER BY question_id, knowledge_point_id"
    ).fetchall()

    # 构建 Q 矩阵二维数组
    n_questions = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    q_matrix = np.zeros((n_questions, n_kp), dtype=np.int32)
    for row in q_rows:
        q_matrix[row["question_id"] - 1, row["knowledge_point_id"] - 1] = row["is_covered"]

    # --- 加载 X 矩阵（所有学生） ---
    n_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    x_rows = conn.execute(
        "SELECT student_id, question_id, is_correct FROM x_matrix ORDER BY student_id, question_id"
    ).fetchall()
    x_matrix = np.zeros((n_students, n_questions), dtype=np.int32)
    for row in x_rows:
        x_matrix[row["student_id"] - 1, row["question_id"] - 1] = row["is_correct"]

    # --- 获取该生的作答统计 ---
    student_x = x_matrix[student_id - 1]
    correct_count = int(student_x.sum())
    incorrect_count = n_questions - correct_count

    # --- DINA 参数估计与诊断 ---
    try:
        slip, guess = estimate_slip_guess(q_matrix, x_matrix)
        probs_all = compute_knowledge_prob(q_matrix, x_matrix, slip, guess)
        student_probs = probs_all[student_id - 1]
    except ValueError:
        # 如果参数估计失败（如边缘情况），返回合理默认值
        student_probs = np.full(n_kp, 0.5)

    # --- 构建雷达图数据 ---
    radar_data = []
    for k in range(n_kp):
        radar_data.append({
            "knowledge_point_id": int(kp_rows[k]["id"]),
            "knowledge_point_name": kp_names[k],
            "mastery_probability": round(float(student_probs[k]), 4)
        })

    return jsonify({
        "student_id": student["id"],
        "student_name": student["name"],
        "radar_data": radar_data,
        "answer_summary": {
            "total": n_questions,
            "correct": correct_count,
            "incorrect": incorrect_count
        }
    })


# ═══════════════════════════════════════
# API: 知识图谱
# ═══════════════════════════════════════

@app.route("/api/knowledge_graph")
def api_knowledge_graph():
    """
    返回知识图谱完整结构（节点 + 前驱后继有向边）。

    Returns:
        JSON: {"nodes": [{"id": int, "name": str}, ...],
               "edges": [{"predecessor_kp_id": int, "predecessor_name": str,
                          "successor_kp_id": int, "successor_name": str}, ...]}
    """
    conn = database.get_connection()

    # 节点
    kp_rows = conn.execute("SELECT id, name FROM knowledge_points ORDER BY id").fetchall()
    nodes = [{"id": r["id"], "name": r["name"]} for r in kp_rows]

    # 边（含前驱/后继名称）
    edge_rows = conn.execute("""
        SELECT
            kg.predecessor_kp_id,
            kp1.name AS predecessor_name,
            kg.successor_kp_id,
            kp2.name AS successor_name
        FROM knowledge_graph kg
        JOIN knowledge_points kp1 ON kg.predecessor_kp_id = kp1.id
        JOIN knowledge_points kp2 ON kg.successor_kp_id = kp2.id
        ORDER BY kg.predecessor_kp_id, kg.successor_kp_id
    """).fetchall()

    edges = []
    for r in edge_rows:
        edges.append({
            "predecessor_kp_id": r["predecessor_kp_id"],
            "predecessor_name": r["predecessor_name"],
            "successor_kp_id": r["successor_kp_id"],
            "successor_name": r["successor_name"]
        })

    return jsonify({"nodes": nodes, "edges": edges})


# ═══════════════════════════════════════
# API: 学习建议（LLM / 模拟）
# ═══════════════════════════════════════

@app.route("/api/advice/<int:student_id>", methods=["POST"])
def api_advice(student_id):
    """
    为指定学生生成个性化学习建议。
    优先调用 Deepseek LLM API；若未配置 API Key 则返回模拟建议。

    Request Body (optional):
        {"regenerate": true}  — 是否重新生成

    Response 200:
        {"advice": "生成的建议文本"}
    """
    conn = database.get_connection()

    # --- 验证学生存在并获取诊断数据 ---
    student = conn.execute(
        "SELECT id, name FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    if student is None:
        return jsonify({"error": "student_not_found", "message": f"学生 ID={student_id} 不存在"}), 404

    # --- 获取该生的诊断数据（复用 DINA 计算）---
    kp_rows = conn.execute("SELECT id, name FROM knowledge_points ORDER BY id").fetchall()
    n_kp = len(kp_rows)
    kp_names = [r["name"] for r in kp_rows]

    n_questions = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    n_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]

    q_rows = conn.execute(
        "SELECT question_id, knowledge_point_id, is_covered FROM q_matrix ORDER BY question_id, knowledge_point_id"
    ).fetchall()
    q_matrix = np.zeros((n_questions, n_kp), dtype=np.int32)
    for row in q_rows:
        q_matrix[row["question_id"] - 1, row["knowledge_point_id"] - 1] = row["is_covered"]

    x_rows = conn.execute(
        "SELECT student_id, question_id, is_correct FROM x_matrix ORDER BY student_id, question_id"
    ).fetchall()
    x_matrix = np.zeros((n_students, n_questions), dtype=np.int32)
    for row in x_rows:
        x_matrix[row["student_id"] - 1, row["question_id"] - 1] = row["is_correct"]

    # DINA 诊断
    try:
        slip, guess = estimate_slip_guess(q_matrix, x_matrix)
        probs_all = compute_knowledge_prob(q_matrix, x_matrix, slip, guess)
        student_probs = probs_all[student_id - 1]
    except ValueError:
        student_probs = np.full(n_kp, 0.5)

    radar_data = []
    for k in range(n_kp):
        radar_data.append({
            "knowledge_point_id": int(kp_rows[k]["id"]),
            "knowledge_point_name": kp_names[k],
            "mastery_probability": round(float(student_probs[k]), 4)
        })

    # --- 调用 LLM / 模拟建议 ---
    try:
        advice_text = generate_advice(student["name"], radar_data)
    except Exception as e:
        logger.error(f"建议生成失败: {e}")
        advice_text = f"建议生成失败，请稍后重试。（错误: {e}）"

    return jsonify({"advice": advice_text})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
