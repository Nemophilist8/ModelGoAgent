"""
测试函数提取功能
"""
from graph.nodes import extract_function_from_file, extract_multiple_functions

# 测试单个函数提取
print("=" * 80)
print("测试 1: 提取单个函数 'combine'")
print("=" * 80)
result = extract_function_from_file("combine")
print(result)

print("\n\n")
print("=" * 80)
print("测试 2: 提取单个函数 'train'")
print("=" * 80)
result = extract_function_from_file("train")
print(result)

print("\n\n")
print("=" * 80)
print("测试 3: 提取多个函数 ['use', 'embed', 'generate']")
print("=" * 80)
result = extract_multiple_functions(["use", "embed", "generate"])
print(result)
