"""提示词常用方法"""

from pathlib import Path


def load_prompt(name: str) -> str:
    """输入提示词文件名，获取提示词内容"""
    return (Path(__file__).parent / name).read_text(encoding="utf-8")
