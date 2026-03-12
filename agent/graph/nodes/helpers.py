"""
节点辅助函数
"""
import ast
import json
import os
import re
from agent.config import logger


def validate_reuse_method_resp(data) -> bool:
    """
    简化版校验 LLM 输出是否符合预期格式：
    [
      {
        "method": "",
        "description": "",
        "inputs": [],
        "output": ""
      }
    ]
    返回 True/False
    """
    try:
        if not isinstance(data, list):
            return False

        for item in data:
            if not isinstance(item, dict):
                return False
            if not all(key in item for key in ["method", "description", "inputs", "output"]):
                return False
            if not isinstance(item["inputs"], list):
                return False

        return True
    except Exception:
        return False

def safe_json_loads(text: str):
    """
    安全解析 LLM 输出的 JSON。
    - 自动提取 ```json``` codeblock
    - 自动提取第一个 JSON 块
    - 清洗不可见字符
    - 失败时返回 None，并打印 logger.info 错误原因
    """

    try:
        raw = text.strip()

        # 提取 ```json ... ```
        code_block = re.search(r"```json(.*?)```", raw, re.S)
        if code_block:
            raw = code_block.group(1).strip()

        # 提取第一个 JSON 块（数组或对象）
        match = re.search(r"(\{.*\}|\[.*\])", raw, re.S)
        if match:
            raw = match.group(1)

        # 清洗 Unicode 不可见字符
        raw = raw.encode("utf-8", "ignore").decode("utf-8")

        return json.loads(raw)

    except Exception as e:
        logger.error(f"safe_json_loads 解析失败: {e}")
        return None


def extract_function_from_file(function_name: str, file_path: str = None) -> str:
    """
    从指定的 Python 文件中提取函数定义及其文档字符串

    Args:
        function_name: 要提取的函数名
        file_path: Python 文件路径，默认为 ../scripts/reuse_methods.py

    Returns:
        包含函数定义的文本字符串，如果未找到则返回空字符串
    """
    if file_path is None:
        # 默认路径：相对于当前文件的位置，定位到项目根下的 scripts/reuse_methods.py
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        file_path = os.path.join(base_dir, "scripts", "reuse_methods.py")

    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
            file_lines = file_content.split('\n')

        # 解析 AST
        tree = ast.parse(file_content)

        # 查找目标函数
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                # 获取函数的起始行和结束行
                start_line = node.lineno - 1  # AST 行号从 1 开始
                end_line = node.end_lineno

                # 提取函数前的注释（如果有）
                comment_lines = []
                check_line = start_line - 1
                while check_line >= 0:
                    line = file_lines[check_line].strip()
                    # 检查是否是注释或文档字符串
                    if line.startswith('#') or line.startswith('"""') or line.startswith("'''"):
                        comment_lines.insert(0, file_lines[check_line])
                        check_line -= 1
                    elif line == '':
                        # 空行也包含
                        comment_lines.insert(0, file_lines[check_line])
                        check_line -= 1
                    else:
                        break

                # 提取函数代码
                function_code = '\n'.join(file_lines[start_line:end_line])

                # 组合注释和函数代码
                if comment_lines:
                    result = '\n'.join(comment_lines) + '\n' + function_code
                else:
                    result = function_code

                logger.info(f"成功提取函数 '{function_name}' ({end_line - start_line} 行)")
                return result

        logger.warning(f"未找到函数 '{function_name}' 在文件 {file_path}")
        return ""

    except FileNotFoundError:
        abs_path = os.path.abspath(file_path)
        print(abs_path)
        logger.error(f"文件不存在: {file_path}")
        return ""
    except SyntaxError as e:
        logger.error(f"文件语法错误: {e}")
        return ""
    except Exception as e:
        logger.error(f"提取函数时出错: {e}")
        return ""


def extract_multiple_functions(function_names: list, file_path: str = None) -> str:
    """
    从指定的 Python 文件中提取多个函数定义

    Args:
        function_names: 要提取的函数名列表
        file_path: Python 文件路径，默认为 ../scripts/reuse_methods.py

    Returns:
        包含所有函数定义的文本字符串，用分隔符分开
    """
    results = []

    function_names = list(set(function_names))
    for func_name in function_names:
        func_code = extract_function_from_file(func_name, file_path)
        if func_code:
            results.append(func_code)

    return "\n\n".join(results) if results else ""

def extract_python_code(text: str) -> str:
    m = re.search(r'```python\s*(.*?)\s*```', text, re.S | re.I)
    if m:
        return m.group(1)

    m = re.search(r'```\s*(.*?)\s*```', text, re.S)
    if m:
        return m.group(1)

    return text.strip()


def build_license_clauses_text(known_works, license_raw_dir=None) -> str:
    """
    为 known_works 中涉及的每个唯一许可证，读取 scripts/license_raw/ 下对应的原文文件，
    拼接为格式化的许可证原文字符串，供注入分析提示词使用。
    相同许可证的 work 合并展示，每份许可证原文只插入一次。
    """
    if license_raw_dir is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        license_raw_dir = os.path.join(base_dir, 'scripts', 'license_raw')

    # 按许可证名称聚合 work
    license_to_works: dict[str, list[str]] = {}
    for work in (known_works or []):
        lic = getattr(work, 'license', None)
        if not lic:
            continue
        license_to_works.setdefault(lic, []).append(work.name)

    sections = []
    for lic, work_names in license_to_works.items():
        works_label = "、".join(work_names)
        license_file = os.path.join(license_raw_dir, f"{lic}.txt")

        if os.path.exists(license_file):
            with open(license_file, 'r', encoding='utf-8') as f:
                raw_text = f.read()
            sections.append(f"### {lic}\n\n适用作品：{works_label}\n\n{raw_text.strip()}")
        else:
            logger.warning(f"许可证原文文件未找到: {lic}")
            sections.append(f"### {lic}\n\n适用作品：{works_label}\n\n（原文件未找到，请查阅官方网站）")

    # print(os.path.abspath(license_file))
    return "\n\n---\n\n".join(sections) if sections else "（未检测到任何已知许可证）"
