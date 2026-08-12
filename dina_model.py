"""
认知诊断作业 — DINA 模型算法逻辑
阶段：TDD 算法实现

DINA 模型 (Deterministic Inputs, Noisy "And" gate model)
是认知诊断中经典的离散模型，用于根据学生作答数据
推断学生的知识掌握状态。

核心公式:
- 理想反应: η_ij = Π_k α_ik^{q_jk}  (And gate)
- 观察似然: P(X_ij | η_ij) =
    (1-slip)^{η_ij} * guess^{(1-η_ij)}      当 X_ij = 1
    slip^{η_ij} * (1-guess)^{(1-η_ij)}       当 X_ij = 0
"""
import numpy as np


def _validate_inputs(q_matrix, x_matrix):
    """
    输入校验：确保 Q 矩阵和 X 矩阵的维度匹配，且无不合法值。

    Args:
        q_matrix: np.ndarray, shape (n_questions, n_knowledge_points), 0/1
        x_matrix: np.ndarray, shape (n_students, n_questions), 0/1

    Returns:
        tuple: (q_matrix, x_matrix) — 转为 np.ndarray 后的输入

    Raises:
        ValueError: 若 Q 矩阵列数与 X 矩阵列数不匹配，或 Q 矩阵某行全为 0
    """
    if not isinstance(q_matrix, np.ndarray):
        q_matrix = np.array(q_matrix, dtype=np.int32)
    if not isinstance(x_matrix, np.ndarray):
        x_matrix = np.array(x_matrix, dtype=np.int32)

    n_questions, n_kp = q_matrix.shape
    n_students, n_q = x_matrix.shape

    if n_questions != n_q:
        raise ValueError(
            f"Q 矩阵列数({n_questions})与 X 矩阵列数({n_q})不匹配"
        )

    # 检查 Q 矩阵是否有全 0 行
    for j in range(n_questions):
        if q_matrix[j].sum() == 0:
            raise ValueError(
                f"Q 矩阵第 {j} 行全为 0：该题目不考查任何知识点，无法估计参数"
            )

    return q_matrix, x_matrix


def _compute_eta(q_matrix, alpha):
    """
    根据 Q 矩阵和学生知识状态 α，计算理想反应矩阵 η。

    η_ij = 1 当且仅当学生对题目 j 所考查的所有知识点均已掌握。

    Args:
        q_matrix: np.ndarray, shape (n_questions, n_knowledge_points), 0/1
        alpha: np.ndarray, shape (n_students, n_knowledge_points), 0/1 知识状态

    Returns:
        np.ndarray, shape (n_students, n_questions), 0/1 理想反应矩阵
    """
    n_students = alpha.shape[0]
    n_questions = q_matrix.shape[0]
    eta = np.zeros((n_students, n_questions), dtype=np.int32)

    for j in range(n_questions):
        required = np.where(q_matrix[j] == 1)[0]
        if len(required) > 0:
            eta[:, j] = np.all(alpha[:, required] == 1, axis=1).astype(np.int32)

    return eta


def estimate_slip_guess(q_matrix, x_matrix):
    """
    使用矩估计法估计 DINA 模型的 slip（失误率）和 guess（猜测率）参数。

    算法步骤:
    1. 对每个学生，根据其在与各知识点相关题目上的平均得分，初估 α 向量
    2. 二值化 α（阈值 0.5）
    3. 计算理想反应 η
    4. 统计 η=1 时的错误率 → slip，η=0 时的正确率 → guess

    Args:
        q_matrix: np.ndarray, shape (n_questions, n_knowledge_points), 0/1
        x_matrix: np.ndarray, shape (n_students, n_questions), 0/1

    Returns:
        tuple: (slip, guess) — 两个 float，范围均在 [0, 1]
    """
    q_matrix, x_matrix = _validate_inputs(q_matrix, x_matrix)

    n_students, n_questions = x_matrix.shape
    n_kp = q_matrix.shape[1]

    # ── Step 1: 软估计 α ──
    alpha_soft = np.zeros((n_students, n_kp))
    for k in range(n_kp):
        kp_qs = np.where(q_matrix[:, k] == 1)[0]
        if len(kp_qs) > 0:
            alpha_soft[:, k] = x_matrix[:, kp_qs].mean(axis=1)

    # ── Step 2: 二值化 ──
    alpha_binary = (alpha_soft >= 0.5).astype(np.int32)

    # ── Step 3: 理想反应 ──
    eta = _compute_eta(q_matrix, alpha_binary)

    # ── Step 4: 统计 slip 和 guess ──
    slip_mask = eta == 1
    guess_mask = eta == 0

    if slip_mask.sum() > 0:
        slip = 1.0 - x_matrix[slip_mask].mean()
    else:
        slip = 0.0

    if guess_mask.sum() > 0:
        guess = x_matrix[guess_mask].mean()
    else:
        guess = 0.0

    # 正则化：clip 到合理范围，避免极端值导致数值问题
    slip = float(np.clip(slip, 0.001, 0.499))
    guess = float(np.clip(guess, 0.001, 0.499))

    return slip, guess


def compute_knowledge_prob(q_matrix, x_matrix, slip, guess):
    """
    计算每个学生在每个知识点上的后验掌握概率（贝叶斯推断）。

    使用精确枚举法遍历所有可能的 α 状态（共 2^{n_kp} 种），
    计算每种状态的后验概率，再对每个知识点进行边缘化。

    先验: 基于学生在各知识点相关题目上的平均得分动态计算，
    避免全对/全错情况下先验过于极端。

    Args:
        q_matrix: np.ndarray, shape (n_questions, n_knowledge_points), 0/1
        x_matrix: np.ndarray, shape (n_students, n_questions), 0/1
        slip: float, 失误率参数
        guess: float, 猜测率参数

    Returns:
        np.ndarray, shape (n_students, n_knowledge_points), 掌握概率 [0,1]
    """
    q_matrix, x_matrix = _validate_inputs(q_matrix, x_matrix)

    n_students, n_questions = x_matrix.shape
    n_kp = q_matrix.shape[1]
    n_states = 1 << n_kp  # 2^{n_kp}

    probs = np.zeros((n_students, n_kp), dtype=np.float64)

    # ── 计算每个学生在各知识点上的平均得分（用于动态先验） ──
    kp_scores = np.zeros((n_students, n_kp))
    for k in range(n_kp):
        kp_qs = np.where(q_matrix[:, k] == 1)[0]
        if len(kp_qs) > 0:
            kp_scores[:, k] = x_matrix[:, kp_qs].mean(axis=1)

    # ── 预计算每道题所需的 KP 集合 ──
    question_kps = [set(np.where(q_matrix[j] == 1)[0].tolist()) for j in range(n_questions)]

    for i in range(n_students):
        # 动态先验: 基于各 KP 得分，clip 到 [0.2, 0.8] 避免极端
        prior = np.clip(0.3 + 0.4 * kp_scores[i], 0.15, 0.85)

        state_log_probs = np.zeros(n_states, dtype=np.float64)

        for state in range(n_states):
            # 解析 α 向量
            alpha = np.array([(state >> k) & 1 for k in range(n_kp)], dtype=np.int32)

            # ── 对数先验 ──
            log_prob = 0.0
            for k in range(n_kp):
                if alpha[k] == 1:
                    log_prob += np.log(prior[k])
                else:
                    log_prob += np.log(1.0 - prior[k])

            # ── 对数似然 ──
            for j in range(n_questions):
                required = question_kps[j]
                if len(required) == 0:
                    eta_ij = 0
                else:
                    eta_ij = 1 if all(alpha[k] == 1 for k in required) else 0

                if eta_ij == 1:
                    p_correct = 1.0 - slip
                else:
                    p_correct = guess

                if x_matrix[i, j] == 1:
                    log_prob += np.log(max(p_correct, 1e-15))
                else:
                    log_prob += np.log(max(1.0 - p_correct, 1e-15))

            state_log_probs[state] = log_prob

        # ── Log-Sum-Exp 归一化 ──
        max_log = state_log_probs.max()
        state_probs = np.exp(state_log_probs - max_log)
        state_probs /= state_probs.sum()

        # ── 边缘化：对每个 KP 求和 P(α_k=1) ──
        for k in range(n_kp):
            mask = np.array([(s >> k) & 1 for s in range(n_states)], dtype=bool)
            probs[i, k] = state_probs[mask].sum()

    return probs
