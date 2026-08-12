"""
TDD 阶段 — DINA 模型单元测试
阶段：TDD 算法实现

测试先行原则：本文件在 dina_model.py 实现前编写，
初次运行应全部 FAILED（红灯）。
"""
import pytest
import numpy as np
from dina_model import estimate_slip_guess, compute_knowledge_prob


# ══════════════════════════════════════════════
# 辅助函数
# ══════════════════════════════════════════════

def _make_q_all_covered(n_kp=2):
    """生成每个知识点至少被一题覆盖的 Q 矩阵（3 题 × n_kp 知识点）"""
    q = np.zeros((3, n_kp), dtype=np.int32)
    q[0, 0] = 1                    # Q1: 仅 KP1
    q[1, :] = 1                    # Q2: 全部 KP
    q[2, 0] = 1                    # Q3: 仅 KP1（冗余题）
    return q


# ══════════════════════════════════════════════
# 测试 1: 参数估计
# ══════════════════════════════════════════════

class TestEstimateSlipGuess:
    """测试 estimate_slip_guess 函数"""

    def test_returns_tuple_of_two_floats(self, small_q_matrix, small_x_matrix):
        """验证返回值为两个浮点数的元组"""
        slip, guess = estimate_slip_guess(small_q_matrix, small_x_matrix)
        assert isinstance(slip, float), f"slip 应为 float，实际为 {type(slip)}"
        assert isinstance(guess, float), f"guess 应为 float，实际为 {type(guess)}"

    def test_slip_in_range_0_to_1(self, small_q_matrix, small_x_matrix):
        """验证 slip 参数在 [0, 1] 范围内"""
        slip, _ = estimate_slip_guess(small_q_matrix, small_x_matrix)
        assert 0.0 <= slip <= 1.0, f"slip={slip} 超出 [0,1] 范围"

    def test_guess_in_range_0_to_1(self, small_q_matrix, small_x_matrix):
        """验证 guess 参数在 [0, 1] 范围内"""
        _, guess = estimate_slip_guess(small_q_matrix, small_x_matrix)
        assert 0.0 <= guess <= 1.0, f"guess={guess} 超出 [0,1] 范围"

    def test_slip_small_when_all_masters_answered_correctly(self):
        """当所有学生都答对时，slip 应接近 0（无人失误）"""
        q = np.array([[1, 0], [1, 1]], dtype=np.int32)
        # 所有学生两题全对
        x = np.ones((5, 2), dtype=np.int32)
        slip, _ = estimate_slip_guess(q, x)
        assert slip < 0.3, f"全对场景下 slip 应很小，实际 slip={slip:.4f}"

    def test_guess_small_when_no_one_guessed_correctly(self):
        """当无人猜对时，guess 应接近 0"""
        q = np.array([[1, 0], [1, 1]], dtype=np.int32)
        # 所有学生只答对 Q1（仅 KP1），Q2 全部答错（需要 KP1+KP2）
        x = np.zeros((5, 2), dtype=np.int32)
        x[:, 0] = 1   # Q1 全对
        x[:, 1] = 0   # Q2 全错
        _, guess = estimate_slip_guess(q, x)
        assert guess < 0.3, f"无人猜对场景下 guess 应很小，实际 guess={guess:.4f}"

    def test_handles_single_student(self):
        """至少应能处理 1 个学生的数据（不崩溃）"""
        q = np.array([[1, 0], [1, 1]], dtype=np.int32)
        x = np.array([[1, 1]], dtype=np.int32)
        slip, guess = estimate_slip_guess(q, x)
        assert slip is not None and guess is not None


# ══════════════════════════════════════════════
# 测试 2: 掌握概率计算
# ══════════════════════════════════════════════

class TestComputeKnowledgeProb:
    """测试 compute_knowledge_prob 函数"""

    def test_output_shape_matches(self, small_q_matrix, small_x_matrix):
        """验证输出矩阵形状为 (n_students, n_knowledge_points)"""
        slip, guess = 0.2, 0.2
        probs = compute_knowledge_prob(small_q_matrix, small_x_matrix, slip, guess)
        n_students, n_kp = small_x_matrix.shape[0], small_q_matrix.shape[1]
        assert probs.shape == (n_students, n_kp), \
            f"预期形状 ({n_students}, {n_kp})，实际 {probs.shape}"

    def test_all_probabilities_in_0_to_1(self, small_q_matrix, small_x_matrix):
        """验证所有概率值在 [0, 1] 范围内"""
        slip, guess = 0.2, 0.2
        probs = compute_knowledge_prob(small_q_matrix, small_x_matrix, slip, guess)
        assert np.all(probs >= 0.0), "存在 <0 的概率"
        assert np.all(probs <= 1.0), "存在 >1 的概率"

    def test_mastery_near_one_for_all_correct_student(self):
        """全对学生的掌握概率应接近 1"""
        q = np.array([[1, 0], [1, 1]], dtype=np.int32)
        x = np.ones((3, 2), dtype=np.int32)  # 全对
        slip, guess = 0.1, 0.1
        probs = compute_knowledge_prob(q, x, slip, guess)
        # 所有学生对所有知识点的掌握概率应 > 0.7
        assert np.all(probs > 0.7), \
            f"全对学生掌握概率应接近 1，实际最小值 {probs.min():.4f}"

    def test_mastery_near_zero_for_all_incorrect_student(self):
        """全错学生的掌握概率应接近 0"""
        q = np.array([[1, 0], [1, 1]], dtype=np.int32)
        x = np.zeros((3, 2), dtype=np.int32)  # 全错
        slip, guess = 0.1, 0.1
        probs = compute_knowledge_prob(q, x, slip, guess)
        # 全错学生掌握概率应 < 0.4
        assert np.all(probs < 0.4), \
            f"全错学生掌握概率应接近 0，实际最大值 {probs.max():.4f}"

    def test_partial_mastery_ordering(self):
        """部分掌握时，答对越多→掌握概率应越高（单调性检查）"""
        q = np.array([[1, 0], [1, 1], [1, 1]], dtype=np.int32)
        # 学生 A：3 题全对（掌握 KP1+KP2）
        # 学生 B：只对 Q1（仅掌握 KP1）
        x = np.array([
            [1, 1, 1],   # 学生 A: 全对
            [1, 0, 0],   # 学生 B: 仅 Q1
        ], dtype=np.int32)
        slip, guess = 0.15, 0.15
        probs = compute_knowledge_prob(q, x, slip, guess)
        # 学生 A 的 KP2 掌握概率应 > 学生 B 的 KP2 掌握概率
        assert probs[0, 1] > probs[1, 1], \
            f"全对学生 KP2 掌握率({probs[0,1]:.4f})应 > 仅对Q1学生({probs[1,1]:.4f})"

    def test_uses_both_slip_and_guess_parameters(self):
        """验证 slip 和 guess 参数确实影响了计算结果（非固定输出）"""
        q = np.array([[1, 0], [1, 1]], dtype=np.int32)
        x = np.array([[1, 0], [1, 0]], dtype=np.int32)  # 两个学生都只对 Q1

        probs_low = compute_knowledge_prob(q, x, slip=0.05, guess=0.05)
        probs_high = compute_knowledge_prob(q, x, slip=0.40, guess=0.40)

        # 不同参数应产生不同结果
        assert not np.allclose(probs_low, probs_high), \
            "不同 slip/guess 参数应产生不同的掌握概率"


# ══════════════════════════════════════════════
# 测试 3: 边缘情况
# ══════════════════════════════════════════════

class TestEdgeCases:
    """测试边缘情况与异常处理"""

    def test_empty_q_matrix_row_raises_or_default(self):
        """Q 矩阵某行全 0 时应有明确处理（异常或默认值）"""
        q = np.array([
            [1, 0],
            [0, 0],   # 该题不考查任何知识点
        ], dtype=np.int32)
        x = np.array([[1, 0], [1, 1]], dtype=np.int32)

        # 应抛出 ValueError 或返回安全的默认值
        try:
            slip, guess = estimate_slip_guess(q, x)
            # 如果不抛异常，至少 slip/guess 应有效
            assert 0.0 <= slip <= 1.0
            assert 0.0 <= guess <= 1.0
        except (ValueError, ZeroDivisionError):
            # 抛异常也是可接受的行为
            pass

    def test_zero_variance_response_handled(self):
        """所有学生对某题的作答完全一致时（无方差），不崩溃"""
        q = np.array([[1, 0], [1, 1]], dtype=np.int32)
        # 所有学生 Q1=1, Q2=1（无方差）
        x = np.ones((10, 2), dtype=np.int32)
        try:
            slip, guess = estimate_slip_guess(q, x)
            assert 0.0 <= slip <= 1.0
            assert 0.0 <= guess <= 1.0
        except Exception as e:
            pytest.fail(f"零方差数据不应导致崩溃: {e}")

    def test_single_question_handled(self):
        """单道题的 Q 矩阵和 X 矩阵不应崩溃"""
        q = np.array([[1]], dtype=np.int32)
        x = np.array([[1], [0], [1], [0], [1]], dtype=np.int32)
        try:
            slip, guess = estimate_slip_guess(q, x)
            assert 0.0 <= slip <= 1.0
            assert 0.0 <= guess <= 1.0
            probs = compute_knowledge_prob(q, x, slip, guess)
            assert probs.shape == (5, 1)
        except Exception as e:
            pytest.fail(f"单题场景不应崩溃: {e}")

    def test_many_students_performance(self):
        """100 名学生规模下应能在合理时间内完成"""
        q = np.array([[1, 0], [1, 1], [0, 1]], dtype=np.int32)
        rng = np.random.RandomState(42)
        x = rng.randint(0, 2, size=(100, 3)).astype(np.int32)

        import time
        start = time.time()
        slip, guess = estimate_slip_guess(q, x)
        probs = compute_knowledge_prob(q, x, slip, guess)
        elapsed = time.time() - start

        assert elapsed < 2.0, f"100 学生计算超时: {elapsed:.2f}s"
        assert probs.shape == (100, 2)  # Q 矩阵为 (3, 2)，输出 KP 数=2
