"""Word 批量处理：批量替换文字、提取全部文字、汇总所有表格。

用法：
    # 1) 批量替换：把文件夹里所有 Word 里的"甲公司"换成"乙公司"
    python word_tool.py "文件夹" --replace --old 甲公司 --new 乙公司 -o 替换结果

    # 2) 提取全部文字到一个 txt（方便搜索、统计）
    python word_tool.py "文件夹" --extract -o 全部文字.txt

    # 3) 把所有 Word 里的表格汇总成一个 Excel（HR / 行政常用）
    python word_tool.py "文件夹" --tables -o 表格汇总.xlsx
"""
import argparse
import sys
from pathlib import Path

from docx import Document


def iter_docx(folder):
    """找出文件夹里所有 .docx（跳过 Word 打开时产生的 ~$ 临时文件）。"""
    files = [f for f in sorted(folder.iterdir())
             if f.is_file() and f.suffix.lower() == ".docx" and not f.name.startswith("~$")]
    return files


def replace_in_paragraph(para, old, new):
    """在一个段落里替换文字，返回替换了多少处。

    先按 run 替换（保留格式）；如果文字被 Word 拆成了多个 run，
    再退一步整段重写（会丢这一段的内部格式，但保证替换成功）。
    """
    count = 0
    for run in para.runs:
        if old in run.text:
            run.text = run.text.replace(old, new)
            count += 1

    if count == 0 and old in para.text:
        # 文字被拆散在多个 run 里，只能整段重建
        new_text = para.text.replace(old, new)
        if para.runs:
            para.runs[0].text = new_text
            for run in para.runs[1:]:
                run.text = ""
            count = 1
    return count


def replace_in_doc(doc, old, new):
    """替换正文、表格里的文字，返回 (替换处数, 段落数)。"""
    total = 0
    hit_paras = 0

    for para in doc.paragraphs:
        n = replace_in_paragraph(para, old, new)
        if n:
            total += n
            hit_paras += 1

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    n = replace_in_paragraph(para, old, new)
                    if n:
                        total += n
                        hit_paras += 1
    return total, hit_paras


def replace_in_folder(folder, old, new, out_dir):
    """批量替换一个文件夹里的 Word，结果写到 out_dir。

    供网页版调用：不打印、不退出，出错抛 ValueError。
    返回 (输出目录, info dict)。
    """
    files = iter_docx(Path(folder))
    if not files:
        raise ValueError(f"在 {folder} 里没找到 .docx 文件")
    if not old:
        raise ValueError("要替换的文字不能为空")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    detail = []
    total_hits = 0
    changed_files = 0
    for f in files:
        try:
            doc = Document(str(f))
        except Exception as e:
            detail.append({"name": f.name, "paras": 0, "note": f"打不开：{e}"})
            continue
        hits, paras = replace_in_doc(doc, old, new)
        if hits:
            doc.save(str(out / f.name))
            total_hits += hits
            changed_files += 1
            detail.append({"name": f.name, "paras": paras, "note": ""})
        else:
            detail.append({"name": f.name, "paras": 0, "note": "无匹配，未输出"})

    return out, {
        "files": detail,
        "total_hits": total_hits,
        "count": len(files),
        "changed": changed_files,
    }


def do_replace(folder, old, new, out_dir, dry_run):
    files = iter_docx(folder)
    if not files:
        sys.exit(f"在 {folder} 里没找到 .docx 文件")

    print(f"找到 {len(files)} 个 Word 文件")
    print(f"替换规则：「{old}」 → 「{new}」\n")

    total_files_hit = 0
    total_hits = 0
    out_path = Path(out_dir) if out_dir else None
    if out_path and not dry_run:
        out_path.mkdir(parents=True, exist_ok=True)

    for f in files:
        try:
            doc = Document(str(f))
        except Exception as e:
            print(f"  [跳过] {f.name} —— 打不开：{e}")
            continue
        hits, paras = replace_in_doc(doc, old, new)
        if hits:
            total_files_hit += 1
            total_hits += hits
            print(f"  {f.name}：{paras} 段有替换")
            if not dry_run and out_path:
                doc.save(str(out_path / f.name))
        else:
            print(f"  {f.name}：无匹配")

    print(f"\n共 {total_files_hit} 个文件、{total_hits} 段被修改")
    if dry_run:
        print("[预览模式] 未写文件")
    elif out_path:
        print(f"结果已保存到：{out_path.resolve()}")
        print("（原文件没有被改动）")


def do_extract(folder, output, dry_run):
    files = iter_docx(folder)
    if not files:
        sys.exit(f"在 {folder} 里没找到 .docx 文件")

    lines = []
    for f in files:
        try:
            doc = Document(str(f))
        except Exception as e:
            print(f"  [跳过] {f.name} —— 打不开：{e}")
            continue
        lines.append("")
        lines.append("=" * 50)
        lines.append(f"文件：{f.name}")
        lines.append("=" * 50)
        for para in doc.paragraphs:
            t = para.text.strip()
            if t:
                lines.append(t)
        for ti, table in enumerate(doc.tables, 1):
            lines.append(f"\n[表格 {ti}]")
            for row in table.rows:
                cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                lines.append(" | ".join(cells))
        print(f"  {f.name}：已提取")

    text = "\n".join(lines)
    if dry_run:
        print(f"\n[预览模式] 共 {len(text)} 个字，未写文件")
        return
    out = Path(output or "全部文字.txt")
    if out.parent and not out.parent.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"\n已保存：{out.resolve()}（{len(text)} 个字）")


def do_tables(folder, output, dry_run):
    files = iter_docx(folder)
    if not files:
        sys.exit(f"在 {folder} 里没找到 .docx 文件")

    rows = []
    for f in files:
        try:
            doc = Document(str(f))
        except Exception as e:
            print(f"  [跳过] {f.name} —— 打不开：{e}")
            continue
        for ti, table in enumerate(doc.tables, 1):
            if not table.rows:
                continue
            header = [c.text.strip() for c in table.rows[0].cells]
            for row in table.rows[1:]:
                cells = [c.text.strip() for c in row.cells]
                if not any(cells):
                    continue
                rec = {"_来源文件": f.name, "_第几个表": ti}
                for i, h in enumerate(header):
                    key = h or f"列{i + 1}"
                    rec[key] = cells[i] if i < len(cells) else ""
                rows.append(rec)
            print(f"  {f.name} 表{ti}：{len(table.rows) - 1} 行")

    if not rows:
        sys.exit("没有在任何一个 Word 里找到表格")

    import pandas as pd
    df = pd.DataFrame(rows)
    print(f"\n合计：{len(df)} 行 × {len(df.columns)} 列")
    print(f"列：{', '.join(map(str, df.columns))}")

    if dry_run:
        print("\n[预览模式] 未写文件")
        return
    out = Path(output or "表格汇总.xlsx")
    if out.parent and not out.parent.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out, index=False)
    print(f"\n已保存：{out.resolve()}")


def main():
    p = argparse.ArgumentParser(description="Word 批量处理")
    p.add_argument("folder", help="放 Word 文件的文件夹")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--replace", action="store_true", help="批量替换文字")
    g.add_argument("--extract", action="store_true", help="提取全部文字")
    g.add_argument("--tables", action="store_true", help="汇总所有表格")
    p.add_argument("--old", default="", help="要替换掉的文字")
    p.add_argument("--new", default="", help="替换成的文字")
    p.add_argument("-o", "--output", default=None, help="输出文件或文件夹")
    p.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    args = p.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        sys.exit(f"文件夹不存在：{folder}")

    if args.replace:
        if not args.old:
            sys.exit("替换模式必须用 --old 指定要替换掉的文字")
        do_replace(folder, args.old, args.new, args.output or "替换结果", args.dry_run)
    elif args.extract:
        do_extract(folder, args.output or "全部文字.txt", args.dry_run)
    else:
        do_tables(folder, args.output or "表格汇总.xlsx", args.dry_run)


if __name__ == "__main__":
    main()
