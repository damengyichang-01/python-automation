"""PDF 合并 / 拆分 / 抽取页面。

用法：
    # 把一个文件夹里所有 PDF 合并成一个（按文件名自然顺序）
    python pdf_merge.py "PDF文件夹" -o 合并结果.pdf

    # 只看会合并哪些文件、一共多少页
    python pdf_merge.py "PDF文件夹" --dry-run

    # 把一个 PDF 拆成单页（输出到文件夹）
    python pdf_merge.py "文件.pdf" --split -o 拆分结果

    # 只抽取指定页，合成一个新的 PDF
    python pdf_merge.py "文件.pdf" --pages 1-3,7 -o 抽取结果.pdf
"""
import argparse
import re
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def natural_key(name):
    """让 1.pdf、2.pdf、10.pdf 按人眼习惯排序。

    直接 sorted() 会排成 1、10、2 —— 因为字符串是逐字符比较的，
    '1' < '2'，但 '10' 的第二位 '0' 比 '2' 小，所以 10 跑到 2 前面。

    这个函数把文件名切成"文字/数字"交替的片段，数字转成 int 再比，
    于是 10 会被当作数字十，自然排在 2 后面。
    """
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", name)]


def collect_pdfs(folder):
    """收集文件夹里的 PDF，按文件名自然顺序排好。"""
    files = [f for f in folder.iterdir()
             if f.is_file() and f.suffix.lower() == ".pdf"]
    return sorted(files, key=lambda f: natural_key(f.name))


def parse_pages(spec, total):
    """把 '1-3,7' 解析成 0 基的页索引列表 [0,1,2,6]。

    超出总页数时直接报错，不做静默截断 —— 客户少了一页会以为程序坏了。
    """
    result = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                a, b = part.split("-", 1)
                start, end = int(a), int(b)
            except ValueError:
                sys.exit(f"页码写法不对：{part}（正确写法如 1-3,7）")
        else:
            try:
                start = end = int(part)
            except ValueError:
                sys.exit(f"页码写法不对：{part}（正确写法如 1-3,7）")
        if start < 1 or start > end or end > total:
            sys.exit(f"页码 {part} 超出范围，这份 PDF 共 {total} 页")
        result.extend(range(start - 1, end))

    seen, ordered = set(), []
    for i in result:
        if i not in seen:
            seen.add(i)
            ordered.append(i)
    return ordered


def merge_pdfs(folder, output):
    """把一个文件夹里的 PDF 按文件名自然顺序合并，返回信息 dict。

    供网页版调用：不打印、不退出，出错抛 ValueError。
    """
    files = collect_pdfs(Path(folder))
    if not files:
        raise ValueError(f"在 {folder} 里没找到 PDF 文件")

    writer = PdfWriter()
    total = 0
    detail = []
    for f in files:
        try:
            reader = PdfReader(str(f))
        except Exception as e:
            detail.append({"name": f.name, "pages": 0, "note": f"跳过：{e}"})
            continue
        n = len(reader.pages)
        total += n
        detail.append({"name": f.name, "pages": n, "note": ""})
        for page in reader.pages:
            writer.add_page(page)

    if total == 0:
        raise ValueError("没有可用的 PDF 页面，请确认上传的是有效 PDF")

    out = Path(output)
    if out.parent and not out.parent.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
    writer.write(str(out))
    return {"files": detail, "pages": total, "count": len(files)}


def do_merge(folder, output, dry_run):
    files = collect_pdfs(folder)
    if not files:
        sys.exit(f"在 {folder} 里没找到 PDF 文件")

    print(f"找到 {len(files)} 个 PDF，合并顺序：")
    writer = PdfWriter()
    total = 0
    for f in files:
        try:
            reader = PdfReader(str(f))
        except Exception as e:
            print(f"  [跳过] {f.name} —— 打不开：{e}")
            continue
        n = len(reader.pages)
        total += n
        print(f"  {f.name}   {n} 页")
        if not dry_run:
            for page in reader.pages:
                writer.add_page(page)

    print(f"\n合计：{total} 页")

    if dry_run:
        print("[预览模式] 未写文件")
        return

    out = Path(output)
    if out.parent and not out.parent.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
    writer.write(str(out))
    print(f"已保存：{out.resolve()}")


def do_split(src, output, pages_spec, dry_run):
    reader = PdfReader(str(src))
    total = len(reader.pages)
    print(f"读取：{src.name}，共 {total} 页")

    idxs = parse_pages(pages_spec, total) if pages_spec else list(range(total))

    if pages_spec:
        # 抽取指定页，合成一个新 PDF
        if dry_run:
            print(f"[预览模式] 将抽取 {len(idxs)} 页：{', '.join(str(i+1) for i in idxs)}")
            return
        writer = PdfWriter()
        for i in idxs:
            writer.add_page(reader.pages[i])
        out = Path(output)
        if out.parent and not out.parent.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
        writer.write(str(out))
        print(f"已抽取 {len(idxs)} 页 -> {out.resolve()}")
        return

    # 拆成单页
    out_dir = Path(output) if output else Path(f"{src.stem}_拆分")
    if dry_run:
        print(f"[预览模式] 将拆成 {total} 个单页文件，输出到：{out_dir.resolve()}")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in idxs:
        w = PdfWriter()
        w.add_page(reader.pages[i])
        w.write(str(out_dir / f"{src.stem}_第{i + 1}页.pdf"))
    print(f"已拆分 {len(idxs)} 页 -> {out_dir.resolve()}")


def main():
    p = argparse.ArgumentParser(description="PDF 合并 / 拆分 / 抽取页面")
    p.add_argument("path", help="要合并的文件夹，或要拆分的 PDF 文件")
    p.add_argument("-o", "--output", default=None,
                   help="输出文件名（合并/抽取）或输出文件夹（拆分）")
    p.add_argument("--split", action="store_true", help="拆分成单页")
    p.add_argument("--pages", default="", help="只抽取这些页，如 1-3,7")
    p.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    args = p.parse_args()

    target = Path(args.path)
    if not target.exists():
        sys.exit(f"路径不存在：{target}")

    split_mode = args.split or args.pages
    if split_mode:
        if target.is_dir():
            sys.exit("拆分模式要给一个 PDF 文件，不是文件夹")
        default_out = None
        do_split(target, args.output or default_out, args.pages, args.dry_run)
    else:
        if not target.is_dir():
            sys.exit("合并模式要给一个文件夹；要拆分单个文件请加 --split")
        do_merge(target, args.output or "合并结果.pdf", args.dry_run)


if __name__ == "__main__":
    main()
