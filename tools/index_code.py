"""生成代码索引：列出每个 .py 文件里的函数、类，以及它们所在的行号。

用法：
    python tools/index_code.py             # 写入 docs/code-index.md
    python tools/index_code.py --stdout    # 直接打印，不写文件

有了这份索引，找"某个函数在第几行"不用到处翻，
直接打开 docs/code-index.md 搜函数名就行。
"""
import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "code-index.md"
SKIP_DIRS = {".git", "build", "dist", "__pycache__", "demo_output", "demo_data", "docs"}


def iter_py_files(root):
    """按路径顺序找出所有要索引的 .py 文件。"""
    for p in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


def first_doc_line(node):
    """取 docstring 第一行，没有就返回空字符串。"""
    doc = ast.get_docstring(node)
    if not doc:
        return ""
    line = doc.strip().splitlines()[0].strip()
    return line if len(line) <= 40 else line[:40] + "…"


def describe(path):
    """解析一个文件，返回 (模块说明, [(行号, 类型, 名称, 说明), ...])。"""
    src = path.read_text(encoding="utf-8-sig")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        print(f"[跳过] {path.name} 语法有误：{e}")
        return "", []

    module_doc = first_doc_line(tree)
    items = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            items.append((node.lineno, "函数", node.name, first_doc_line(node)))
        elif isinstance(node, ast.ClassDef):
            items.append((node.lineno, "类", node.name, first_doc_line(node)))
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    items.append((sub.lineno, "  方法", sub.name, first_doc_line(sub)))
        elif isinstance(node, ast.Assign) and node.lineno > 0:
            # 只记大写的模块级常量，噪音少
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.isupper():
                    items.append((node.lineno, "常量", t.id, ""))
    return module_doc, items


def build_markdown(root):
    lines = ["# 代码索引", "",
             "> 自动生成，不要手改。重新生成：`python tools/index_code.py`", ""]
    total_files = 0
    total_items = 0
    for p in iter_py_files(root):
        rel = p.relative_to(root).as_posix()
        module_doc, items = describe(p)
        if not items:
            continue
        total_files += 1
        total_items += len(items)
        lines.append(f"## `{rel}`")
        if module_doc:
            lines.append(f"")
            lines.append(module_doc)
        lines.append("")
        lines.append("| 行 | 类型 | 名称 | 说明 |")
        lines.append("|---:|---|---|---|")
        for lineno, kind, name, doc in items:
            lines.append(f"| {lineno} | {kind.strip()} | `{name}` | {doc} |")
        lines.append("")
    lines.insert(3, f"共 {total_files} 个文件、{total_items} 个函数/类/常量。")
    lines.insert(4, "")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="生成代码索引")
    p.add_argument("--stdout", action="store_true", help="直接打印，不写文件")
    args = p.parse_args()

    md = build_markdown(ROOT)
    if args.stdout:
        sys.stdout.reconfigure(encoding="utf-8")
        print(md)
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(md, encoding="utf-8")
    print(f"已生成：{OUT.resolve()}")


if __name__ == "__main__":
    main()
