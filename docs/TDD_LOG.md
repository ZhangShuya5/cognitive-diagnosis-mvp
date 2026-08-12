# TDD 开发日志

> **阶段**: TDD 算法实现
> **日期**: 2026-08-12
> **测试框架**: pytest 9.1.1

---

## TDD 节奏记录

遵循 **红灯 → 绿灯 → 重构** 节奏，每次只修改最少代码使测试通过。

---

### 迭代 1：红灯 — 函数签名占位

**操作**: 在 `dina_model.py` 中定义 `estimate_slip_guess` 和 `compute_knowledge_prob` 两个函数签名，函数体抛出 `NotImplementedError`。

**运行结果**: 16 FAILED（全部因 `NotImplementedError` 失败）

**分析**: 测试框架正确捕获了尚未实现的功能。测试覆盖了参数估计（6 个用例）、掌握概率计算（6 个用例）、边缘情况（4 个用例）。

---

### 迭代 2：绿灯 — 实现矩估计参数推断

**操作**: 实现 `estimate_slip_guess` 和 `compute_knowledge_prob` 的完整逻辑。

首次运行结果：15 PASSED / 1 FAILED。

**失败测试**: `test_many_students_performance`

**失败原因分析**:

```
assert probs.shape == (100, 3)
# 实际: probs.shape == (100, 2)
```

测试中 Q 矩阵定义为 `(3, 2)`（3 题 × 2 知识点），但断言写成了 `(100, 3)`。这是因为写测试时思维惯性（将题目数 3 误当作知识点数）。这是一个**测试本身的 bug**，而非实现代码的问题。

**修正方法**: 将断言改为 `probs.shape == (100, 2)`，并添加注释说明 Q 矩阵维度。

修正后运行：**16 PASSED / 0 FAILED** ✅

---

### 迭代 3：重构 — 提取辅助函数

**操作**:
1. 提取 `_validate_inputs()` — 输入校验（维度匹配、全零行检测）
2. 提取 `_compute_eta()` — 理想反应矩阵计算（And gate 逻辑）

**运行结果**: 16 PASSED（重构不破坏已有测试）

**重构收益**:
- 主函数更简洁，单一职责清晰
- `_validate_inputs` 可被两个公开函数复用
- `_compute_eta` 封装了 DINA 模型的核心"And gate"语义

---

## 算法设计要点

### `estimate_slip_guess` — 矩估计法

```
1. α_soft[i,k] = mean(X[i, j] for j where q[j,k]=1)    # 软估计
2. α_binary[i,k] = 1 if α_soft[i,k] >= 0.5 else 0       # 二值化
3. η[i,j] = AND(α_binary[i,k] for k where q[j,k]=1)     # 理想反应
4. slip = mean(1 - X[i,j] for (i,j) where η[i,j]=1)     # 失误率
5. guess = mean(X[i,j] for (i,j) where η[i,j]=0)        # 猜测率
6. clip(slip, 0.001, 0.499); clip(guess, 0.001, 0.499)  # 正则化
```

### `compute_knowledge_prob` — 精确贝叶斯推断

```
1. prior[k] = clip(0.3 + 0.4 * kp_score[k], 0.15, 0.85)  # 动态先验
2. 枚举所有 2^{n_kp} 种 α 状态
3. 对每种状态:
   - 计算对数先验 log P(α)
   - 计算对数似然 log P(X_i | α, slip, guess)
   - 求和得对数后验
4. Log-Sum-Exp 归一化得到后验概率分布
5. 对每个 KP k 边缘化: P(α_k=1 | X_i) = Σ_{α: α_k=1} P(α | X_i)
```

**数值稳定性**: 使用 log-sum-exp 技巧避免浮点下溢。

**复杂度**: O(n_students × 2^{n_kp} × n_questions)，在 n_kp=5 时（32 状态）完全可接受。

---

## 测试覆盖汇总

| 测试类 | 用例数 | 覆盖内容 | 结果 |
|---|---|---|---|
| `TestEstimateSlipGuess` | 6 | 返回值类型、范围检查、边界（全对/全错）、单学生 | ✅ |
| `TestComputeKnowledgeProb` | 6 | 形状、概率范围、全对≈1、全错≈0、单调性、参数敏感性 | ✅ |
| `TestEdgeCases` | 4 | Q 矩阵全零行、零方差数据、单题场景、100 学生性能 | ✅ |
| **合计** | **16** | — | **16/16 PASSED** |
