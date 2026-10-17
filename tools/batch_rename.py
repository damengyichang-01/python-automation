"""批量重命名工具 —— 加序号和前缀，支持预览。

用法：
    python batch_rename.py "目录" --ext .png --prefix 图片
    python batch_rename.py "目录" --ext .png --prefix 图片 --dry-run
"""
import argparse
from pathlib import Path


def build_plan(folder: Path, ext: str, prefix: str, width: int):
    """生成 [(原文件, 新文件名), ...]，不真正改名。"""
    files = sorted(
        [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() == ext.lower()],
        key=lambda f: f.name,
    )
    plan = []
    for i, f in enumerate(files, start=1):
        new_name = f"{prefix}_{i:0{width}d}{f.suffix}"
        plan.append((f, new_name))
    return plan


def main():
    p = argparse.ArgumentParser(description="批量重命名文件")
    p.add_argument("folder", help="要处理的目录")
    p.add_argument("--ext", required=True, help="文件后缀，例如 .png")
    p.add_argument("--prefix", required=True, help="新文件名前缀")
    p.add_argument("--width", type=int, default=3, help="序号位数，默认 3")
    p.add_argument("--dry-run", action="store_true", help="只预览，不改名")
    args = p.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        raise SystemExit(f"目录不存在: {folder}")

    plan = build_plan(folder, args.ext, args.prefix, args.width)
    if not plan:
        print(f"没有找到 {args.ext} 文件")
        return

    for old, new in plan:
        if args.dry_run:
            print(f"[预览] {old.name}  ->  {new}")
        else:
            old.rename(folder / new)
            print(f"[完成] {old.name}  ->  {new}")

    print(f"\n共 {len(plan)} 个文件" + ("（预览模式，未修改）" if args.dry_run else "已重命名"))


if __name__ == "__main__":
    main()
