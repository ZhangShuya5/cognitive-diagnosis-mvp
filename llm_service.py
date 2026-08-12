"""
认知诊断作业 — LLM 学习建议服务
阶段：前端可视化

支持两种模式:
1. 真实 LLM 模式: 配置环境变量 DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL 后调用 Deepseek API
2. 模拟模式: 未配置 API Key 时返回基于诊断数据生成的规则化建议
"""
import os
import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


# ── 配置 ────────────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get(
    "DEEPSEEK_BASE_URL",
    "https://api.deepseek.com/v1/chat/completions"
)
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


# ── 提示词模板 ──────────────────────────────────

SYSTEM_PROMPT = """你是一位经验丰富的数学教育诊断专家。根据认知诊断模型（DINA）的分析结果，
为教师提供针对该学生的具体、可操作的学习建议。建议应简短、具体、分层级。"""


def _build_user_prompt(student_name, radar_data):
    """根据诊断数据构建用户提示词"""
    mastery_lines = []
    for item in radar_data:
        pct = item["mastery_probability"] * 100
        level = "优秀" if pct >= 80 else ("良好" if pct >= 60 else ("一般" if pct >= 40 else "薄弱"))
        mastery_lines.append(
            f"  - {item['knowledge_point_name']}: 掌握概率 {pct:.1f}% ({level})"
        )

    return f"""学生「{student_name}」的认知诊断结果如下：

{chr(10).join(mastery_lines)}

请根据以上诊断结果：
1. 指出最需要加强的 2 个知识点
2. 给出 3 条具体的学习建议（每条不超过 50 字）
3. 推荐一个复习优先级排序（5 个知识点从高到低排列）

请用中文回答，格式为清晰的列表。"""


# ── 模拟建议生成（无需 API Key）──────────────────

def _generate_mock_advice(student_name, radar_data):
    """基于规则生成模拟的学习建议（无 LLM 依赖）"""
    # 按掌握概率升序排列（最弱排前面）
    sorted_data = sorted(radar_data, key=lambda x: x["mastery_probability"])
    weakest = sorted_data[:2]
    strongest = sorted_data[-1]

    weak_names = "、".join([f"「{item['knowledge_point_name']}」" for item in weakest])
    strong_name = strongest["knowledge_point_name"]

    priority = " → ".join([item["knowledge_point_name"] for item in sorted_data])

    advice = f"""【模拟建议 — 未配置 LLM API Key】

📊 诊断摘要：
- 最需加强：{weak_names}
- 优势领域：{strong_name}

📋 学习建议：

1. 针对{weak_names}进行专项突破训练，每天完成 5 道针对性练习题，
   先理解基础概念再逐步提升难度。

2. 利用已掌握的「{strong_name}」优势，设计综合性题目将薄弱知识点
   融入其中，通过迁移学习加速理解。

3. 建议按以下顺序复习：{priority}。
   前驱知识点稳固后再攻克后继内容，避免跳级学习。

🔧 提示：设置环境变量 DEEPSEEK_API_KEY 可启用 AI 个性化建议生成。"""

    return advice


# ── 真实 LLM 调用 ────────────────────────────────

def _call_deepseek_api(student_name, radar_data):
    """调用 Deepseek API 生成个性化学习建议"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(student_name, radar_data)}
    ]

    payload = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 600
    }).encode("utf-8")

    req = urllib.request.Request(
        DEEPSEEK_BASE_URL,
        data=payload,
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        logger.error(f"Deepseek API HTTP 错误: {e.code} - {e.reason}")
        raise
    except urllib.error.URLError as e:
        logger.error(f"Deepseek API 网络错误: {e.reason}")
        raise
    except (KeyError, IndexError) as e:
        logger.error(f"Deepseek API 响应格式异常: {e}")
        raise


# ── 公开接口 ──────────────────────────────────────

def generate_advice(student_name, radar_data):
    """
    生成学习建议。

    Args:
        student_name: str, 学生姓名
        radar_data: list[dict], 诊断雷达图数据，每项含 knowledge_point_name
                    和 mastery_probability

    Returns:
        str: 生成的建议文本
    """
    if DEEPSEEK_API_KEY:
        logger.info(f"使用 Deepseek API 为 {student_name} 生成建议")
        try:
            return _call_deepseek_api(student_name, radar_data)
        except Exception as e:
            logger.warning(f"LLM 调用失败，回退到模拟建议: {e}")
            return _generate_mock_advice(student_name, radar_data)
    else:
        logger.info(f"未配置 DEEPSEEK_API_KEY，使用模拟建议（{student_name}）")
        return _generate_mock_advice(student_name, radar_data)
