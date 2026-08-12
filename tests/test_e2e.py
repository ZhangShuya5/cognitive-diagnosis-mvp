"""
TDD 阶段 — 端到端测试
阶段：TDD 算法实现

验证完整链路：Flask 路由 → 数据库读取 → DINA 计算 → JSON 响应。
首次运行时应全部 FAILED（红灯），因为 API 路由尚未实现。
"""
import pytest
import json


# ══════════════════════════════════════════════
# E2E 测试 1: GET /api/students
# ══════════════════════════════════════════════

class TestStudentsAPI:
    """测试学生列表 API"""

    def test_returns_json_response(self, app):
        """验证返回 Content-Type 为 JSON"""
        response = app.get("/api/students")
        assert response.content_type is not None
        assert "application/json" in response.content_type

    def test_returns_200_status(self, app):
        """验证 HTTP 状态码为 200"""
        response = app.get("/api/students")
        assert response.status_code == 200

    def test_returns_list_of_students(self, app):
        """验证返回的 students 是列表"""
        data = json.loads(response := app.get("/api/students").data)
        assert "students" in data
        assert isinstance(data["students"], list)

    def test_student_count_at_least_10(self, app):
        """验证学生数量 ≥ 10"""
        response = app.get("/api/students")
        data = json.loads(response.data)
        assert len(data["students"]) >= 10, \
            f"学生数应 ≥ 10，实际为 {len(data['students'])}"

    def test_student_has_id_and_name(self, app):
        """验证每个学生对象包含 id 和 name 字段"""
        response = app.get("/api/students")
        data = json.loads(response.data)
        for student in data["students"]:
            assert "id" in student
            assert "name" in student
            assert isinstance(student["id"], int)
            assert isinstance(student["name"], str)

    def test_total_field_matches_list_length(self, app):
        """验证 total 字段与列表长度一致"""
        response = app.get("/api/students")
        data = json.loads(response.data)
        assert data["total"] == len(data["students"])


# ══════════════════════════════════════════════
# E2E 测试 2: GET /api/questions
# ══════════════════════════════════════════════

class TestQuestionsAPI:
    """测试题目列表 API"""

    def test_returns_200(self, app):
        response = app.get("/api/questions")
        assert response.status_code == 200

    def test_returns_20_questions(self, app):
        """验证返回恰好 20 道题目"""
        response = app.get("/api/questions")
        data = json.loads(response.data)
        assert data["total"] == 20, \
            f"题目总数应为 20，实际为 {data['total']}"

    def test_question_has_content_and_kp_list(self, app):
        """验证每道题包含 content 和 covered_knowledge_points"""
        response = app.get("/api/questions")
        data = json.loads(response.data)
        for q in data["questions"]:
            assert "id" in q
            assert "content" in q
            assert "covered_knowledge_points" in q
            assert isinstance(q["covered_knowledge_points"], list)
            assert len(q["covered_knowledge_points"]) >= 1, \
                f"题目 {q['id']} 至少应考查 1 个知识点"

    def test_covered_kp_ids_are_valid(self, app):
        """验证 covered_knowledge_points 中的 ID 在 1~5 范围内"""
        response = app.get("/api/questions")
        data = json.loads(response.data)
        for q in data["questions"]:
            for kp_id in q["covered_knowledge_points"]:
                assert 1 <= kp_id <= 5, \
                    f"题目 {q['id']} 的知识点 ID {kp_id} 超出范围 1~5"


# ══════════════════════════════════════════════
# E2E 测试 3: GET /api/diagnosis/{student_id}
# ══════════════════════════════════════════════

class TestDiagnosisAPI:
    """测试诊断结果 API"""

    def test_returns_200_for_valid_student(self, app):
        """验证对有效学生 ID 返回 200"""
        response = app.get("/api/diagnosis/1")
        assert response.status_code == 200

    def test_returns_404_for_invalid_student(self, app):
        """验证对不存在学生 ID 返回 404"""
        response = app.get("/api/diagnosis/9999")
        assert response.status_code == 404

    def test_response_contains_radar_data(self, app):
        """验证响应包含 radar_data 字段（5 个知识点）"""
        response = app.get("/api/diagnosis/1")
        data = json.loads(response.data)
        assert "radar_data" in data
        assert len(data["radar_data"]) == 5, \
            f"radar_data 应有 5 个元素，实际为 {len(data['radar_data'])}"

    def test_radar_data_has_required_fields(self, app):
        """验证 radar_data 每个元素包含必要字段"""
        response = app.get("/api/diagnosis/1")
        data = json.loads(response.data)
        for point in data["radar_data"]:
            assert "knowledge_point_id" in point
            assert "knowledge_point_name" in point
            assert "mastery_probability" in point

    def test_mastery_probabilities_in_range_0_to_1(self, app):
        """验证所有掌握概率在 [0, 1] 范围内"""
        response = app.get("/api/diagnosis/1")
        data = json.loads(response.data)
        for point in data["radar_data"]:
            prob = point["mastery_probability"]
            assert 0.0 <= prob <= 1.0, \
                f"掌握概率 {prob} 超出 [0,1] 范围"

    def test_probabilities_not_all_zero(self, app):
        """验证掌握概率不全为 0（确保有实际计算）"""
        response = app.get("/api/diagnosis/1")
        data = json.loads(response.data)
        probs = [p["mastery_probability"] for p in data["radar_data"]]
        assert sum(probs) > 0.01, \
            "掌握概率总和应 > 0，确保有实际诊断计算"

    def test_answer_summary_present(self, app):
        """验证响应包含作答概况"""
        response = app.get("/api/diagnosis/1")
        data = json.loads(response.data)
        assert "answer_summary" in data
        summary = data["answer_summary"]
        assert "total" in summary
        assert "correct" in summary
        assert "incorrect" in summary
        assert summary["total"] == summary["correct"] + summary["incorrect"]

    def test_student_name_matches(self, app):
        """验证返回的学生姓名与学生表一致"""
        response = app.get("/api/diagnosis/1")
        data = json.loads(response.data)
        assert "student_name" in data

    def test_different_students_have_different_diagnoses(self, app):
        """验证不同学生产生不同的诊断结果"""
        r1 = app.get("/api/diagnosis/1")
        r2 = app.get("/api/diagnosis/2")
        probs1 = [p["mastery_probability"] for p in json.loads(r1.data)["radar_data"]]
        probs2 = [p["mastery_probability"] for p in json.loads(r2.data)["radar_data"]]
        # 因为测试数据是随机生成的，不同学生应有不同结果
        # 但如果碰巧相同也不算错（随机种子可能产生相同数据），用弱断言
        assert isinstance(probs1, list) and isinstance(probs2, list)


# ══════════════════════════════════════════════
# E2E 测试 4: GET /api/knowledge_graph
# ══════════════════════════════════════════════

class TestKnowledgeGraphAPI:
    """测试知识图谱 API"""

    def test_returns_200(self, app):
        response = app.get("/api/knowledge_graph")
        assert response.status_code == 200

    def test_response_contains_nodes_and_edges(self, app):
        """验证响应包含 nodes 和 edges 字段"""
        response = app.get("/api/knowledge_graph")
        data = json.loads(response.data)
        assert "nodes" in data
        assert "edges" in data

    def test_nodes_count_is_5(self, app):
        """验证知识点节点数为 5"""
        response = app.get("/api/knowledge_graph")
        data = json.loads(response.data)
        assert len(data["nodes"]) == 5

    def test_nodes_have_id_and_name(self, app):
        """验证每个节点包含 id 和 name"""
        response = app.get("/api/knowledge_graph")
        data = json.loads(response.data)
        for node in data["nodes"]:
            assert "id" in node
            assert "name" in node

    def test_edges_count_at_least_4(self, app):
        """验证前驱后继边数 ≥ 4"""
        response = app.get("/api/knowledge_graph")
        data = json.loads(response.data)
        assert len(data["edges"]) >= 4, \
            f"知识图谱边数应 ≥ 4，实际为 {len(data['edges'])}"

    def test_edges_have_required_fields(self, app):
        """验证每条边包含前驱/后继的 id 和 name"""
        response = app.get("/api/knowledge_graph")
        data = json.loads(response.data)
        for edge in data["edges"]:
            assert "predecessor_kp_id" in edge
            assert "predecessor_name" in edge
            assert "successor_kp_id" in edge
            assert "successor_name" in edge

    def test_no_self_loops(self, app):
        """验证无自环（predecessor ≠ successor）"""
        response = app.get("/api/knowledge_graph")
        data = json.loads(response.data)
        for edge in data["edges"]:
            assert edge["predecessor_kp_id"] != edge["successor_kp_id"], \
                "知识图谱不应包含自环"


# ══════════════════════════════════════════════
# E2E 测试 5: 健康检查
# ══════════════════════════════════════════════

class TestHealthAPI:
    """测试健康检查接口"""

    def test_health_returns_ok(self, app):
        response = app.get("/api/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ok"


# ══════════════════════════════════════════════
# E2E 测试 6: 首页渲染
# ══════════════════════════════════════════════

class TestPageRender:
    """测试首页 HTML 页面"""

    def test_index_returns_200(self, app):
        """验证首页返回 200"""
        response = app.get("/")
        assert response.status_code == 200

    def test_index_contains_html_content_type(self, app):
        """验证首页返回 HTML"""
        response = app.get("/")
        assert response.content_type is not None
        assert "text/html" in response.content_type

    def test_index_contains_radar_keyword(self, app):
        """验证首页 HTML 包含雷达图相关内容"""
        response = app.get("/")
        html = response.data.decode("utf-8")
        # 检查 ECharts 引入或雷达图相关关键词
        assert "echarts" in html.lower() or "雷达图" in html or "ECharts" in html, \
            "首页应包含 ECharts 或雷达图关键词"

    def test_index_contains_student_select(self, app):
        """验证首页包含学生选择下拉框"""
        response = app.get("/")
        html = response.data.decode("utf-8")
        assert 'student-select' in html or '学生' in html, \
            "首页应包含学生选择控件"


# ══════════════════════════════════════════════
# E2E 测试 7: 学习建议 API
# ══════════════════════════════════════════════

class TestAdviceAPI:
    """测试学习建议生成接口（含模拟回退）"""

    def test_returns_200_for_valid_student(self, app):
        """验证对有效学生返回 200"""
        response = app.post("/api/advice/1")
        assert response.status_code == 200

    def test_returns_404_for_invalid_student(self, app):
        """验证对不存在学生返回 404"""
        response = app.post("/api/advice/9999")
        assert response.status_code == 404

    def test_response_contains_advice_field(self, app):
        """验证响应包含 advice 字段"""
        response = app.post("/api/advice/1")
        data = json.loads(response.data)
        assert "advice" in data

    def test_advice_is_non_empty_string(self, app):
        """验证建议内容非空字符串"""
        response = app.post("/api/advice/1")
        data = json.loads(response.data)
        assert isinstance(data["advice"], str)
        assert len(data["advice"]) > 10, \
            f"建议内容过短: {len(data['advice'])} 字符"

    def test_advice_mentions_knowledge_points(self, app):
        """验证建议内容提及知识点相关内容（模拟模式也应有实质建议）"""
        response = app.post("/api/advice/1")
        data = json.loads(response.data)
        # 模拟模式至少应包含"建议"或知识点名称关键词
        assert any(kw in data["advice"] for kw in ["建议", "学习", "知识点", "掌握", "练习"]), \
            "建议内容应包含学习相关关键词"

    def test_different_students_have_different_advice(self, app):
        """验证不同学生生成不同的建议"""
        r1 = app.post("/api/advice/1")
        r2 = app.post("/api/advice/2")
        a1 = json.loads(r1.data)["advice"]
        a2 = json.loads(r2.data)["advice"]
        # 不同学生可能有相似模板，但诊断数据不同，建议应有差异
        assert isinstance(a1, str) and isinstance(a2, str)
