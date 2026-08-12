"""
认知诊断作业 — 初始假数据 & 环境验证
阶段：环境初始化

本文件用于：
1. 验证核心依赖（NumPy, SQLite）是否可正常导入
2. 后续阶段将填充模拟学生作答数据
"""
import sys
import io

# 修复 Windows GBK 终端无法输出 UTF-8 特殊字符的问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def verify_environment():
    """验证环境：检查 NumPy 和 SQLite 是否能正常导入"""
    errors = []

    # --- 验证 NumPy ---
    try:
        import numpy as np
        print(f"[OK] NumPy 导入成功 — 版本 {np.__version__}")
    except ImportError as e:
        errors.append(f"[FAIL] NumPy 导入失败: {e}")

    # --- 验证 SQLite ---
    try:
        import sqlite3
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        conn.close()
        print(f"[OK] SQLite 导入成功 — 版本 {version}")
    except Exception as e:
        errors.append(f"[FAIL] SQLite 验证失败: {e}")

    # --- 验证 Pandas ---
    try:
        import pandas as pd
        print(f"[OK] Pandas 导入成功 — 版本 {pd.__version__}")
    except ImportError as e:
        errors.append(f"[FAIL] Pandas 导入失败: {e}")

    # --- 验证 Flask & Flask-CORS ---
    try:
        import flask
        print(f"[OK] Flask 导入成功 — 版本 {flask.__version__}")
    except ImportError as e:
        errors.append(f"[FAIL] Flask 导入失败: {e}")

    try:
        import flask_cors  # noqa: F401
        print("[OK] Flask-CORS 导入成功")
    except ImportError as e:
        errors.append(f"[FAIL] Flask-CORS 导入失败: {e}")

    # --- 汇总 ---
    print(f"\nPython 版本: {sys.version}")
    if errors:
        print("\n[FAIL] 环境验证失败，存在以下错误：")
        for err in errors:
            print(f"   {err}")
        return False
    else:
        print("\n[OK] 所有核心依赖验证通过，环境就绪！")
        return True


def generate_sample_data():
    """生成模拟假数据（占位 — 后续阶段补全）"""
    print("[init_data] 假数据生成模块就绪，等待 SDD 建模阶段补全")


if __name__ == "__main__":
    verify_environment()
    generate_sample_data()
